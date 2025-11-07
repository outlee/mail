from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class UserRole(str, Enum):
    MAINTAINER = "maintainer"
    OPERATOR = "operator"
    MANAGER = "manager"


class TaskRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertComparator(str, Enum):
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    EQUAL = "eq"
    NOT_EQUAL = "ne"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool

    class Config:
        from_attributes = True


class KPIRecomputeRequest(BaseModel):
    scope: str
    asset_id: Optional[str] = None
    group_id: Optional[str] = None


class TaskRunResponse(BaseModel):
    id: str
    task_name: str
    task_id: Optional[str] = None
    status: TaskRunStatus
    scope: Optional[str] = None
    asset_id: Optional[str] = None
    group_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    items_processed: int
    created_at: datetime

    class Config:
        from_attributes = True


class KPISnapshotResponse(BaseModel):
    id: str
    asset_id: Optional[str] = None
    group_id: Optional[str] = None
    kpi_type: str
    value: float
    period_start: datetime
    period_end: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class AlertPolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    metric_name: str
    comparator: AlertComparator
    threshold: float
    severity: AlertSeverity = AlertSeverity.MEDIUM
    deduplication_window_minutes: int = 60
    email_recipients: Optional[list[str]] = []
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    is_active: bool = True

    @field_validator('email_recipients', mode='before')
    @classmethod
    def validate_email_recipients(cls, v):
        if v is None:
            return []
        return v


class AlertPolicyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    metric_name: Optional[str] = None
    comparator: Optional[AlertComparator] = None
    threshold: Optional[float] = None
    severity: Optional[AlertSeverity] = None
    deduplication_window_minutes: Optional[int] = None
    email_recipients: Optional[list[str]] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    is_active: Optional[bool] = None


class AlertPolicyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    metric_name: str
    comparator: AlertComparator
    threshold: float
    severity: AlertSeverity
    deduplication_window_minutes: int
    email_recipients: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertOccurrenceResponse(BaseModel):
    id: str
    policy_id: str
    asset_id: Optional[str] = None
    group_id: Optional[str] = None
    kpi_snapshot_id: str
    status: AlertStatus
    severity: AlertSeverity
    current_value: float
    threshold_value: float
    message: str
    last_notification_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertEventLogResponse(BaseModel):
    id: str
    alert_occurrence_id: str
    event_type: str
    message: str
    metadata: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AlertAcknowledgeRequest(BaseModel):
    user_id: str
    message: Optional[str] = None


class AlertResolveRequest(BaseModel):
    user_id: str
    message: Optional[str] = None


class AlertListResponse(BaseModel):
    alerts: list[AlertOccurrenceResponse]
    total: int
    page: int
    size: int
