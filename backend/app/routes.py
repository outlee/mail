import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from celery import current_app as celery_app
from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import CSVImportType, UserRole
from app.schemas import (
    CSVImportJobResponse,
    KPIRecomputeRequest,
    MeResponse,
    RefreshTokenRequest,
    TaskRunResponse,
    TaskRunStatus,
    TokenResponse,
    UserRegister,
    UserResponse,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
)
from app.services import (
    CSVImportJobService,
    KPIService,
    RefreshTokenService,
    TaskRunService,
    UserService,
)

settings = get_settings()

auth_router = APIRouter(prefix="/auth", tags=["auth"])
kpi_router = APIRouter(prefix="/kpis", tags=["kpis"])
imports_router = APIRouter(prefix="/imports", tags=["imports"])

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(kpi_router)
router.include_router(imports_router)

ACCEPTED_CSV_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
}


def _build_import_job_response(job) -> CSVImportJobResponse:
    payload: dict[str, Any] = {
        "id": job.id,
        "import_type": job.import_type,
        "idempotency_key": job.idempotency_key,
        "status": job.status,
        "actor_id": job.actor_id,
        "source_filename": job.source_filename,
        "total_rows": job.total_rows or 0,
        "processed_rows": job.processed_rows or 0,
        "skipped_rows": job.skipped_rows or 0,
        "error_rows": job.error_rows or 0,
        "error_sample": job.error_sample or [],
        "message": job.message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
    }
    return CSVImportJobResponse.model_validate(payload)


async def _handle_csv_import(
    import_type: CSVImportType,
    upload: UploadFile,
    idempotency_key: str,
    current_user,
    db: Session,
) -> CSVImportJobResponse:
    if not idempotency_key or not idempotency_key.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Idempotency-Key header is required",
        )

    idempotency_key = idempotency_key.strip()

    existing_job = CSVImportJobService.get_by_idempotency(
        db=db, import_type=import_type, idempotency_key=idempotency_key
    )
    if existing_job and CSVImportJobService.is_within_ttl(
        existing_job, settings.csv_import_idempotency_ttl_minutes
    ):
        await upload.close()
        return _build_import_job_response(existing_job)

    if upload.content_type not in ACCEPTED_CSV_CONTENT_TYPES:
        await upload.close()
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported content type. Expected text/csv.",
        )

    contents = await upload.read()
    source_filename = upload.filename
    await upload.close()

    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV file is empty",
        )

    if len(contents) > settings.csv_import_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="CSV file exceeds maximum allowed size",
        )

    storage_dir = Path(settings.csv_import_storage_path).expanduser().resolve()
    storage_dir.mkdir(parents=True, exist_ok=True)

    job_id = str(uuid.uuid4())
    destination = storage_dir / f"{job_id}.csv"

    try:
        with destination.open("wb") as buffer:
            buffer.write(contents)
    except OSError as exc:
        if destination.exists():
            destination.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist uploaded CSV file",
        ) from exc

    try:
        job = CSVImportJobService.create_job(
            db=db,
            import_type=import_type,
            idempotency_key=idempotency_key,
            storage_path=str(destination),
            actor_id=getattr(current_user, "id", None),
            source_filename=source_filename,
            job_id=job_id,
        )
    except Exception as exc:
        if destination.exists():
            destination.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create import job",
        ) from exc

    try:
        celery_app.send_task(
            "worker.tasks.process_csv_import_task",
            args=(job.id,),
            retry=True,
            retry_policy={
                "max_retries": 3,
                "interval_start": 1,
                "interval_step": 2,
                "interval_max": 10,
            },
        )
    except Exception as exc:
        CSVImportJobService.mark_failed(
            db=db,
            job_id=job.id,
            total_rows=0,
            processed_rows=0,
            skipped_rows=0,
            error_rows=0,
            error_sample=[],
            message=f"Failed to enqueue job: {exc}",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue import job",
        ) from exc

    return _build_import_job_response(job)


@auth_router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER])),
):
    existing_user = UserService.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = UserService.create_user(
        db=db,
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name,
        role=UserRole.OPERATOR,
    )

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )


@auth_router.post("/login", response_model=TokenResponse)
async def login(
    email: str,
    password: str,
    db: Session = Depends(get_db),
):
    user = UserService.authenticate_user(db, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role.value},
        expires_delta=access_token_expires,
    )

    refresh_token = create_refresh_token(
        data={"sub": user.id, "role": user.role.value}
    )

    refresh_token_hash = hash_password(refresh_token)
    expires_at = datetime.utcnow() + timedelta(
        days=settings.refresh_token_expire_days
    )
    RefreshTokenService.create_refresh_token(
        db=db,
        user_id=user.id,
        token_hash=refresh_token_hash,
        expires_at=expires_at,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@auth_router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id: str = payload.get("sub")
    user = UserService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.id, "role": user.role.value},
        expires_delta=access_token_expires,
    )

    new_refresh_token = create_refresh_token(
        data={"sub": user.id, "role": user.role.value}
    )

    new_refresh_token_hash = hash_password(new_refresh_token)
    expires_at = datetime.utcnow() + timedelta(
        days=settings.refresh_token_expire_days
    )
    RefreshTokenService.create_refresh_token(
        db=db,
        user_id=user.id,
        token_hash=new_refresh_token_hash,
        expires_at=expires_at,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
    )


@auth_router.post("/logout")
async def logout(
    current_user = Depends(get_current_user),
):
    return {"message": "Logged out successfully"}


@auth_router.get("/me", response_model=MeResponse)
async def get_current_user_info(
    current_user = Depends(get_current_user),
):
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@kpi_router.post("/recompute", response_model=TaskRunResponse)
async def trigger_kpi_recompute(
    request: KPIRecomputeRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER, UserRole.OPERATOR])),
):
    task_run = TaskRunService.create_task_run(
        db=db,
        task_name="recompute_kpis",
        scope=request.scope,
        asset_id=request.asset_id,
        group_id=request.group_id,
    )

    if request.scope == "all_assets":
        task = celery_app.send_task(
            "worker.tasks.recompute_rolling_kpis_task",
            args=(task_run.id, "all", None),
            retry=True,
            retry_policy={
                "max_retries": 3,
                "interval_start": 1,
                "interval_step": 2,
                "interval_max": 10,
            },
        )
    elif request.scope == "single_asset":
        task = celery_app.send_task(
            "worker.tasks.recompute_rolling_kpis_task",
            args=(task_run.id, "asset", request.asset_id),
            retry=True,
            retry_policy={
                "max_retries": 3,
                "interval_start": 1,
                "interval_step": 2,
                "interval_max": 10,
            },
        )
    elif request.scope == "all_groups":
        task = celery_app.send_task(
            "worker.tasks.recompute_calendar_kpis_task",
            args=(task_run.id, "all", None),
            retry=True,
            retry_policy={
                "max_retries": 3,
                "interval_start": 1,
                "interval_step": 2,
                "interval_max": 10,
            },
        )
    elif request.scope == "single_group":
        task = celery_app.send_task(
            "worker.tasks.recompute_calendar_kpis_task",
            args=(task_run.id, "group", request.group_id),
            retry=True,
            retry_policy={
                "max_retries": 3,
                "interval_start": 1,
                "interval_step": 2,
                "interval_max": 10,
            },
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid scope: {request.scope}",
        )

    TaskRunService.update_task_run(
        db=db,
        task_run_id=task_run.id,
        status=TaskRunStatus.PENDING,
        task_id=str(task.id),
    )

    return TaskRunResponse(
        id=task_run.id,
        task_name=task_run.task_name,
        task_id=str(task.id),
        status=task_run.status,
        scope=task_run.scope,
        asset_id=task_run.asset_id,
        group_id=task_run.group_id,
        started_at=task_run.started_at,
        completed_at=task_run.completed_at,
        error_message=task_run.error_message,
        items_processed=task_run.items_processed,
        created_at=task_run.created_at,
    )


@kpi_router.get("/task-runs/{task_run_id}", response_model=TaskRunResponse)
async def get_task_run_status(
    task_run_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    task_run = TaskRunService.get_task_run(db, task_run_id)
    if not task_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task run not found",
        )

    return TaskRunResponse(
        id=task_run.id,
        task_name=task_run.task_name,
        task_id=task_run.task_id,
        status=task_run.status,
        scope=task_run.scope,
        asset_id=task_run.asset_id,
        group_id=task_run.group_id,
        started_at=task_run.started_at,
        completed_at=task_run.completed_at,
        error_message=task_run.error_message,
        items_processed=task_run.items_processed,
        created_at=task_run.created_at,
    )


@imports_router.post(
    "/assets",
    response_model=CSVImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_assets_csv(
    file: UploadFile = File(...),
    idempotency_key: str = Header(
        ..., alias="X-Idempotency-Key", convert_underscores=False
    ),
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER, UserRole.OPERATOR])),
):
    return await _handle_csv_import(
        CSVImportType.ASSETS, file, idempotency_key, current_user, db
    )


@imports_router.post(
    "/runtime",
    response_model=CSVImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_runtime_counters_csv(
    file: UploadFile = File(...),
    idempotency_key: str = Header(
        ..., alias="X-Idempotency-Key", convert_underscores=False
    ),
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER, UserRole.OPERATOR])),
):
    return await _handle_csv_import(
        CSVImportType.RUNTIME, file, idempotency_key, current_user, db
    )


@imports_router.post(
    "/failures",
    response_model=CSVImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def import_failure_events_csv(
    file: UploadFile = File(...),
    idempotency_key: str = Header(
        ..., alias="X-Idempotency-Key", convert_underscores=False
    ),
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER, UserRole.OPERATOR])),
):
    return await _handle_csv_import(
        CSVImportType.FAILURES, file, idempotency_key, current_user, db
    )


@imports_router.get(
    "/{job_id}",
    response_model=CSVImportJobResponse,
)
async def get_import_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER, UserRole.OPERATOR])),
):
    job = CSVImportJobService.get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import job not found",
        )

    return _build_import_job_response(job)
