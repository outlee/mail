from datetime import datetime, timedelta

from celery import current_app as celery_app
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models import UserRole
from app.schemas import (
    AlertAcknowledgeRequest,
    AlertListResponse,
    AlertOccurrenceResponse,
    AlertPolicyCreate,
    AlertPolicyResponse,
    AlertPolicyUpdate,
    AlertResolveRequest,
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
    AlertEvaluationService,
    AlertOccurrenceService,
    AlertPolicyService,
    KPIService,
    RefreshTokenService,
    TaskRunService,
    UserService,
)

auth_router = APIRouter(prefix="/auth", tags=["auth"])
kpi_router = APIRouter(prefix="/kpis", tags=["kpis"])
alerts_router = APIRouter(prefix="/alerts", tags=["alerts"])
settings = get_settings()

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(kpi_router)
router.include_router(alerts_router)


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


# Alert Policy Routes
@alerts_router.post("/policies", response_model=AlertPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_policy(
    policy_data: AlertPolicyCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER, UserRole.OPERATOR])),
):
    # Check if policy name already exists
    existing_policy = AlertPolicyService.get_policy_by_name(db, policy_data.name)
    if existing_policy:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Policy with this name already exists",
        )
    
    policy = AlertPolicyService.create_policy(
        db=db,
        name=policy_data.name,
        description=policy_data.description,
        metric_name=policy_data.metric_name,
        comparator=policy_data.comparator,
        threshold=policy_data.threshold,
        severity=policy_data.severity,
        deduplication_window_minutes=policy_data.deduplication_window_minutes,
        email_recipients=policy_data.email_recipients,
        webhook_url=policy_data.webhook_url,
        webhook_secret=policy_data.webhook_secret,
        is_active=policy_data.is_active,
    )
    
    return AlertPolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        metric_name=policy.metric_name,
        comparator=policy.comparator,
        threshold=policy.threshold,
        severity=policy.severity,
        deduplication_window_minutes=policy.deduplication_window_minutes,
        email_recipients=policy.email_recipients,
        webhook_url=policy.webhook_url,
        webhook_secret=policy.webhook_secret,
        is_active=policy.is_active,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@alerts_router.get("/policies", response_model=list[AlertPolicyResponse])
async def list_alert_policies(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = True,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    policies = AlertPolicyService.list_policies(db, skip, limit, active_only)
    return [
        AlertPolicyResponse(
            id=policy.id,
            name=policy.name,
            description=policy.description,
            metric_name=policy.metric_name,
            comparator=policy.comparator,
            threshold=policy.threshold,
            severity=policy.severity,
            deduplication_window_minutes=policy.deduplication_window_minutes,
            email_recipients=policy.email_recipients,
            webhook_url=policy.webhook_url,
            webhook_secret=policy.webhook_secret,
            is_active=policy.is_active,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )
        for policy in policies
    ]


@alerts_router.get("/policies/{policy_id}", response_model=AlertPolicyResponse)
async def get_alert_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    policy = AlertPolicyService.get_policy_by_id(db, policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )
    
    return AlertPolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        metric_name=policy.metric_name,
        comparator=policy.comparator,
        threshold=policy.threshold,
        severity=policy.severity,
        deduplication_window_minutes=policy.deduplication_window_minutes,
        email_recipients=policy.email_recipients,
        webhook_url=policy.webhook_url,
        webhook_secret=policy.webhook_secret,
        is_active=policy.is_active,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@alerts_router.put("/policies/{policy_id}", response_model=AlertPolicyResponse)
async def update_alert_policy(
    policy_id: str,
    policy_update: AlertPolicyUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER, UserRole.OPERATOR])),
):
    # Check if name is being updated and if it conflicts with existing policy
    if policy_update.name:
        existing_policy = AlertPolicyService.get_policy_by_name(db, policy_update.name)
        if existing_policy and existing_policy.id != policy_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Policy with this name already exists",
            )
    
    policy = AlertPolicyService.update_policy(
        db, policy_id, **policy_update.model_dump(exclude_unset=True)
    )
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )
    
    return AlertPolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        metric_name=policy.metric_name,
        comparator=policy.comparator,
        threshold=policy.threshold,
        severity=policy.severity,
        deduplication_window_minutes=policy.deduplication_window_minutes,
        email_recipients=policy.email_recipients,
        webhook_url=policy.webhook_url,
        webhook_secret=policy.webhook_secret,
        is_active=policy.is_active,
        created_at=policy.created_at,
        updated_at=policy.updated_at,
    )


@alerts_router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.MAINTAINER])),
):
    success = AlertPolicyService.delete_policy(db, policy_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found",
        )


# Alert Events Routes
@alerts_router.get("/events", response_model=AlertListResponse)
async def list_alert_events(
    skip: int = 0,
    limit: int = 100,
    status: str = None,
    severity: str = None,
    asset_id: str = None,
    group_id: str = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    from app.models import AlertStatus, AlertSeverity
    
    # Convert string parameters to enums if provided
    status_enum = AlertStatus(status) if status else None
    severity_enum = AlertSeverity(severity) if severity else None
    
    occurrences, total = AlertOccurrenceService.list_occurrences(
        db, skip, limit, status_enum, severity_enum, asset_id, group_id
    )
    
    return AlertListResponse(
        alerts=[
            AlertOccurrenceResponse(
                id=occurrence.id,
                policy_id=occurrence.policy_id,
                asset_id=occurrence.asset_id,
                group_id=occurrence.group_id,
                kpi_snapshot_id=occurrence.kpi_snapshot_id,
                status=occurrence.status,
                severity=occurrence.severity,
                current_value=occurrence.current_value,
                threshold_value=occurrence.threshold_value,
                message=occurrence.message,
                last_notification_at=occurrence.last_notification_at,
                acknowledged_at=occurrence.acknowledged_at,
                acknowledged_by=occurrence.acknowledged_by,
                resolved_at=occurrence.resolved_at,
                resolved_by=occurrence.resolved_by,
                created_at=occurrence.created_at,
                updated_at=occurrence.updated_at,
            )
            for occurrence in occurrences
        ],
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        size=limit,
    )


@alerts_router.post("/events/{alert_id}/acknowledge", response_model=AlertOccurrenceResponse)
async def acknowledge_alert(
    alert_id: str,
    ack_request: AlertAcknowledgeRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    occurrence = AlertOccurrenceService.acknowledge_alert(
        db, alert_id, ack_request.user_id, ack_request.message
    )
    if not occurrence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or cannot be acknowledged",
        )
    
    return AlertOccurrenceResponse(
        id=occurrence.id,
        policy_id=occurrence.policy_id,
        asset_id=occurrence.asset_id,
        group_id=occurrence.group_id,
        kpi_snapshot_id=occurrence.kpi_snapshot_id,
        status=occurrence.status,
        severity=occurrence.severity,
        current_value=occurrence.current_value,
        threshold_value=occurrence.threshold_value,
        message=occurrence.message,
        last_notification_at=occurrence.last_notification_at,
        acknowledged_at=occurrence.acknowledged_at,
        acknowledged_by=occurrence.acknowledged_by,
        resolved_at=occurrence.resolved_at,
        resolved_by=occurrence.resolved_by,
        created_at=occurrence.created_at,
        updated_at=occurrence.updated_at,
    )


@alerts_router.post("/events/{alert_id}/resolve", response_model=AlertOccurrenceResponse)
async def resolve_alert(
    alert_id: str,
    resolve_request: AlertResolveRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    occurrence = AlertOccurrenceService.resolve_alert(
        db, alert_id, resolve_request.user_id, resolve_request.message
    )
    if not occurrence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found or cannot be resolved",
        )
    
    return AlertOccurrenceResponse(
        id=occurrence.id,
        policy_id=occurrence.policy_id,
        asset_id=occurrence.asset_id,
        group_id=occurrence.group_id,
        kpi_snapshot_id=occurrence.kpi_snapshot_id,
        status=occurrence.status,
        severity=occurrence.severity,
        current_value=occurrence.current_value,
        threshold_value=occurrence.threshold_value,
        message=occurrence.message,
        last_notification_at=occurrence.last_notification_at,
        acknowledged_at=occurrence.acknowledged_at,
        acknowledged_by=occurrence.acknowledged_by,
        resolved_at=occurrence.resolved_at,
        resolved_by=occurrence.resolved_by,
        created_at=occurrence.created_at,
        updated_at=occurrence.updated_at,
    )
