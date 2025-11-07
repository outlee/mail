from datetime import datetime, timedelta
from typing import Optional

from celery import current_app as celery_app
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import UserRole, TaskRunStatus
from app.schemas import (
    AssetDetailResponse,
    AssetResponse,
    FailureEventResponse,
    KPIRecomputeRequest,
    KPISnapshotResponse,
    KPIStatsResponse,
    MeResponse,
    RefreshTokenRequest,
    TaskRunResponse,
    TaskRunStatus as TaskRunStatusSchema,
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
    AssetService,
    DashboardService,
    FailureEventService,
    KPIService,
    RefreshTokenService,
    TaskRunService,
    UserService,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
kpi_router = APIRouter(prefix="/kpis", tags=["kpis"])
assets_router = APIRouter(prefix="/assets", tags=["assets"])
failures_router = APIRouter(prefix="/failures", tags=["failures"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])
settings = get_settings()

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(kpi_router)
router.include_router(assets_router)
router.include_router(failures_router)
router.include_router(dashboard_router)


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


@assets_router.get("", response_model=list[AssetResponse])
async def list_assets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return AssetService.list_assets(db, skip=skip, limit=limit)


@assets_router.get("/{asset_id}", response_model=AssetDetailResponse)
async def get_asset_detail(
    asset_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    asset = AssetService.get_asset_by_id(db, asset_id)
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    latest_kpi = (
        db.query(KPISnapshot)
        .filter(KPISnapshot.asset_id == asset_id)
        .order_by(KPISnapshot.created_at.desc())
        .first()
    )

    recent_failures = FailureEventService.list_failure_events(
        db, asset_id=asset_id, limit=10
    )

    return AssetDetailResponse(
        id=asset.id,
        name=asset.name,
        description=asset.description,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        latest_kpi=latest_kpi,
        recent_failures=recent_failures,
    )


@failures_router.get("", response_model=list[FailureEventResponse])
async def list_failures(
    asset_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return FailureEventService.list_failure_events(
        db, asset_id=asset_id, skip=skip, limit=limit
    )


@failures_router.get("/{failure_id}", response_model=FailureEventResponse)
async def get_failure(
    failure_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    failure = FailureEventService.get_failure_event(db, failure_id)
    if not failure:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failure not found",
        )
    return failure


@dashboard_router.get("/stats", response_model=KPIStatsResponse)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    stats = DashboardService.get_kpi_stats(db)
    return KPIStatsResponse(**stats)


@dashboard_router.get("/top-assets")
async def get_top_assets(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DashboardService.get_top_assets(db, limit=limit)


@dashboard_router.get("/bottom-assets")
async def get_bottom_assets(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return DashboardService.get_bottom_assets(db, limit=limit)
