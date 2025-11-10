from datetime import datetime, timedelta
import json

from celery import current_app as celery_app
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import UserRole
from app.schemas import (
    AssetRuntimeCreate,
    AssetRuntimeResponse,
    AuditLogEntryResponse,
    DataQualityReportResponse,
    DataQualityRequest,
    FailureEventCreate,
    FailureEventResponse,
    FailureEventUpdate,
    KPIRecomputeRequest,
    KPISnapshotResponse,
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
    AssetRuntimeService,
    AuditLogService,
    DataQualityService,
    FailureEventService,
    KPIService,
    RefreshTokenService,
    TaskRunService,
    UserService,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
kpi_router = APIRouter(prefix="/kpis", tags=["kpis"])
asset_runtime_router = APIRouter(prefix="/asset-runtimes", tags=["asset-runtimes"])
failure_events_router = APIRouter(prefix="/failure-events", tags=["failure-events"])
audit_router = APIRouter(prefix="/audit", tags=["audit"])
data_quality_router = APIRouter(prefix="/data-quality", tags=["data-quality"])
settings = get_settings()

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(kpi_router)
router.include_router(asset_runtime_router)
router.include_router(failure_events_router)
router.include_router(audit_router)
router.include_router(data_quality_router)


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


# Asset Runtime Routes
@asset_runtime_router.post("/", response_model=AssetRuntimeResponse, status_code=status.HTTP_201_CREATED)
async def create_asset_runtime(
    runtime_data: AssetRuntimeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER, UserRole.OPERATOR])),
):
    try:
        runtime = AssetRuntimeService.create_asset_runtime(
            db=db,
            asset_id=runtime_data.asset_id,
            runtime_counter=runtime_data.runtime_counter,
            metadata=runtime_data.metadata,
        )
        
        # Log audit entry
        AuditLogService.create_audit_entry(
            db=db,
            user_id=current_user.id,
            action=AuditAction.CREATE,
            resource_type="asset_runtime",
            resource_id=runtime.id,
            new_values=json.dumps(runtime_data.dict()),
            ip_address=request.client.host,
        )
        
        return AssetRuntimeResponse(
            id=runtime.id,
            asset_id=runtime.asset_id,
            runtime_counter=runtime.runtime_counter,
            recorded_at=runtime.recorded_at,
            metadata=runtime.metadata,
            created_at=runtime.created_at,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@asset_runtime_router.get("/{runtime_id}", response_model=AssetRuntimeResponse)
async def get_asset_runtime(
    runtime_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    runtime = AssetRuntimeService.get_asset_runtime_by_id(db, runtime_id)
    if not runtime:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset runtime not found",
        )
    
    return AssetRuntimeResponse(
        id=runtime.id,
        asset_id=runtime.asset_id,
        runtime_counter=runtime.runtime_counter,
        recorded_at=runtime.recorded_at,
        metadata=runtime.metadata,
        created_at=runtime.created_at,
    )


@asset_runtime_router.get("/asset/{asset_id}", response_model=list[AssetRuntimeResponse])
async def list_asset_runtimes(
    asset_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    runtimes = AssetRuntimeService.list_asset_runtimes(db, asset_id, skip, limit)
    return [
        AssetRuntimeResponse(
            id=runtime.id,
            asset_id=runtime.asset_id,
            runtime_counter=runtime.runtime_counter,
            recorded_at=runtime.recorded_at,
            metadata=runtime.metadata,
            created_at=runtime.created_at,
        )
        for runtime in runtimes
    ]


# Failure Events Routes
@failure_events_router.post("/", response_model=FailureEventResponse, status_code=status.HTTP_201_CREATED)
async def create_failure_event(
    event_data: FailureEventCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER, UserRole.OPERATOR])),
):
    try:
        event = FailureEventService.create_failure_event(
            db=db,
            asset_id=event_data.asset_id,
            severity=event_data.severity,
            start_time=event_data.start_time,
            description=event_data.description,
            end_time=event_data.end_time,
            metadata=event_data.metadata,
        )
        
        # Log audit entry
        AuditLogService.create_audit_entry(
            db=db,
            user_id=current_user.id,
            action=AuditAction.CREATE,
            resource_type="failure_event",
            resource_id=event.id,
            new_values=json.dumps(event_data.dict()),
            ip_address=request.client.host,
        )
        
        return FailureEventResponse(
            id=event.id,
            asset_id=event.asset_id,
            severity=event.severity,
            start_time=event.start_time,
            end_time=event.end_time,
            description=event.description,
            metadata=event.metadata,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@failure_events_router.get("/{event_id}", response_model=FailureEventResponse)
async def get_failure_event(
    event_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    event = FailureEventService.get_failure_event_by_id(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failure event not found",
        )
    
    return FailureEventResponse(
        id=event.id,
        asset_id=event.asset_id,
        severity=event.severity,
        start_time=event.start_time,
        end_time=event.end_time,
        description=event.description,
        metadata=event.metadata,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@failure_events_router.put("/{event_id}", response_model=FailureEventResponse)
async def update_failure_event(
    event_id: str,
    event_data: FailureEventUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER, UserRole.OPERATOR])),
):
    # Get current event for audit
    current_event = FailureEventService.get_failure_event_by_id(db, event_id)
    if not current_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failure event not found",
        )
    
    old_values = {
        "severity": current_event.severity.value,
        "start_time": current_event.start_time.isoformat(),
        "end_time": current_event.end_time.isoformat() if current_event.end_time else None,
        "description": current_event.description,
        "metadata": current_event.metadata,
    }
    
    try:
        updated_event = FailureEventService.update_failure_event(
            db=db,
            event_id=event_id,
            **event_data.dict(exclude_unset=True),
        )
        
        # Log audit entry
        AuditLogService.create_audit_entry(
            db=db,
            user_id=current_user.id,
            action=AuditAction.UPDATE,
            resource_type="failure_event",
            resource_id=event_id,
            old_values=json.dumps(old_values),
            new_values=json.dumps(event_data.dict(exclude_unset=True)),
            ip_address=request.client.host,
        )
        
        return FailureEventResponse(
            id=updated_event.id,
            asset_id=updated_event.asset_id,
            severity=updated_event.severity,
            start_time=updated_event.start_time,
            end_time=updated_event.end_time,
            description=updated_event.description,
            metadata=updated_event.metadata,
            created_at=updated_event.created_at,
            updated_at=updated_event.updated_at,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@failure_events_router.delete("/{event_id}")
async def delete_failure_event(
    event_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER])),
):
    # Get current event for audit
    current_event = FailureEventService.get_failure_event_by_id(db, event_id)
    if not current_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failure event not found",
        )
    
    old_values = {
        "severity": current_event.severity.value,
        "start_time": current_event.start_time.isoformat(),
        "end_time": current_event.end_time.isoformat() if current_event.end_time else None,
        "description": current_event.description,
        "metadata": current_event.metadata,
    }
    
    success = FailureEventService.delete_failure_event(db, event_id)
    
    if success:
        # Log audit entry
        AuditLogService.create_audit_entry(
            db=db,
            user_id=current_user.id,
            action=AuditAction.DELETE,
            resource_type="failure_event",
            resource_id=event_id,
            old_values=json.dumps(old_values),
            ip_address=request.client.host,
        )
        
        return {"message": "Failure event deleted successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete failure event",
        )


@failure_events_router.get("/", response_model=list[FailureEventResponse])
async def list_failure_events(
    asset_id: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    events = FailureEventService.list_failure_events(db, asset_id, skip, limit)
    return [
        FailureEventResponse(
            id=event.id,
            asset_id=event.asset_id,
            severity=event.severity,
            start_time=event.start_time,
            end_time=event.end_time,
            description=event.description,
            metadata=event.metadata,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )
        for event in events
    ]


# Audit Routes
@audit_router.get("/", response_model=list[AuditLogEntryResponse])
async def list_audit_entries(
    resource_type: str = None,
    resource_id: str = None,
    user_id: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER, UserRole.MANAGER])),
):
    entries = AuditLogService.list_audit_entries(
        db, resource_type, resource_id, user_id, skip, limit
    )
    return [
        AuditLogEntryResponse(
            id=entry.id,
            user_id=entry.user_id,
            action=entry.action,
            resource_type=entry.resource_type,
            resource_id=entry.resource_id,
            old_values=entry.old_values,
            new_values=entry.new_values,
            timestamp=entry.timestamp,
            ip_address=entry.ip_address,
        )
        for entry in entries
    ]


# Data Quality Routes
@data_quality_router.post("/check", response_model=DataQualityReportResponse)
async def run_data_quality_check(
    request: DataQualityRequest = None,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER, UserRole.MANAGER])),
):
    if request is None:
        request = DataQualityRequest()
    
    report = DataQualityService.run_data_quality_check(db, request.report_type)
    
    return DataQualityReportResponse(
        id=report.id,
        report_type=report.report_type,
        status=report.status,
        summary=report.summary,
        details=report.details,
        issues_found=report.issues_found,
        assets_checked=report.assets_checked,
        created_at=report.created_at,
        completed_at=report.completed_at,
    )


@data_quality_router.get("/reports", response_model=list[DataQualityReportResponse])
async def list_data_quality_reports(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    reports = DataQualityService.list_data_quality_reports(db, skip, limit)
    return [
        DataQualityReportResponse(
            id=report.id,
            report_type=report.report_type,
            status=report.status,
            summary=report.summary,
            details=report.details,
            issues_found=report.issues_found,
            assets_checked=report.assets_checked,
            created_at=report.created_at,
            completed_at=report.completed_at,
        )
        for report in reports
    ]


@data_quality_router.get("/reports/{report_id}", response_model=DataQualityReportResponse)
async def get_data_quality_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    report = DataQualityService.get_data_quality_report_by_id(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data quality report not found",
        )
    
    return DataQualityReportResponse(
        id=report.id,
        report_type=report.report_type,
        status=report.status,
        summary=report.summary,
        details=report.details,
        issues_found=report.issues_found,
        assets_checked=report.assets_checked,
        created_at=report.created_at,
        completed_at=report.completed_at,
    )
