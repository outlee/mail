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
