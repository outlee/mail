from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator


class UserRole(str, Enum):
    MAINTAINER = "maintainer"
    OPERATOR = "operator"
    MANAGER = "manager"


class TaskRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class FailureSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


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


class AssetRuntimeCreate(BaseModel):
    asset_id: str
    runtime_counter: int
    metadata: Optional[str] = None

    @validator('runtime_counter')
    def validate_runtime_counter(cls, v):
        if v < 0:
            raise ValueError('Runtime counter must be non-negative')
        return v


class AssetRuntimeResponse(BaseModel):
    id: str
    asset_id: str
    runtime_counter: int
    recorded_at: datetime
    metadata: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class FailureEventCreate(BaseModel):
    asset_id: str
    severity: FailureSeverity
    start_time: datetime
    end_time: Optional[datetime] = None
    description: str
    metadata: Optional[str] = None

    @validator('end_time')
    def validate_time_window(cls, v, values):
        if v and 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v

    @validator('description')
    def validate_description(cls, v, values):
        if values.get('severity') in [FailureSeverity.HIGH, FailureSeverity.CRITICAL]:
            if not v or len(v.strip()) < 10:
                raise ValueError('High and critical severity events require detailed description (min 10 characters)')
        return v


class FailureEventUpdate(BaseModel):
    severity: Optional[FailureSeverity] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    description: Optional[str] = None
    metadata: Optional[str] = None

    @validator('end_time')
    def validate_time_window(cls, v, values):
        if v and 'start_time' in values and v <= values['start_time']:
            raise ValueError('End time must be after start time')
        return v


class FailureEventResponse(BaseModel):
    id: str
    asset_id: str
    severity: FailureSeverity
    start_time: datetime
    end_time: Optional[datetime] = None
    description: str
    metadata: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AuditLogEntryResponse(BaseModel):
    id: str
    user_id: str
    action: AuditAction
    resource_type: str
    resource_id: str
    old_values: Optional[str] = None
    new_values: Optional[str] = None
    timestamp: datetime
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True


class DataQualityReportResponse(BaseModel):
    id: str
    report_type: str
    status: str
    summary: Optional[str] = None
    details: Optional[str] = None
    issues_found: int
    assets_checked: int
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DataQualityRequest(BaseModel):
    report_type: str = Field(default="comprehensive", description="Type of data quality check to run")
