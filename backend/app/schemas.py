from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserRole(str, Enum):
    MAINTAINER = "maintainer"
    OPERATOR = "operator"
    MANAGER = "manager"


class TaskRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


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


class AssetResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FailureEventResponse(BaseModel):
    id: str
    asset_id: str
    failure_mode: str
    failure_code: Optional[str] = None
    severity: str
    duration_minutes: Optional[float] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AssetDetailResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    latest_kpi: Optional[KPISnapshotResponse] = None
    recent_failures: list[FailureEventResponse] = []

    class Config:
        from_attributes = True


class KPIStatsResponse(BaseModel):
    average_kpi: float
    min_kpi: float
    max_kpi: float
    total_assets: int
    total_failures: int
    failures_by_mode: dict[str, int] = {}

    class Config:
        from_attributes = True
