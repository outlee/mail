from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLAlchemyEnum, Float, String
from sqlalchemy.sql import func

from app.database import Base


class UserRole(str, Enum):
    MAINTAINER = "maintainer"
    OPERATOR = "operator"
    MANAGER = "manager"


class TaskRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    hashed_password = Column(String(255))
    full_name = Column(String(255))
    role = Column(SQLAlchemyEnum(UserRole), default=UserRole.OPERATOR, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), index=True)
    token_hash = Column(String(255), index=True)
    expires_at = Column(DateTime(timezone=True), index=True)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Group(Base):
    __tablename__ = "groups"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KPISnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id = Column(String(36), primary_key=True, index=True)
    asset_id = Column(String(36), index=True, nullable=True)
    group_id = Column(String(36), index=True, nullable=True)
    kpi_type = Column(String(50), index=True)
    value = Column(Float)
    period_start = Column(DateTime(timezone=True), index=True)
    period_end = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TaskRun(Base):
    __tablename__ = "task_runs"

    id = Column(String(36), primary_key=True, index=True)
    task_name = Column(String(255), index=True)
    task_id = Column(String(255), nullable=True)
    status = Column(SQLAlchemyEnum(TaskRunStatus), default=TaskRunStatus.PENDING, index=True)
    scope = Column(String(50), nullable=True)
    asset_id = Column(String(36), nullable=True)
    group_id = Column(String(36), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String(1000), nullable=True)
    items_processed = Column(String(50), default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class FailureEvent(Base):
    __tablename__ = "failure_events"

    id = Column(String(36), primary_key=True, index=True)
    asset_id = Column(String(36), index=True)
    failure_mode = Column(String(255), index=True)
    failure_code = Column(String(50), nullable=True)
    severity = Column(String(50), index=True)
    duration_minutes = Column(Float, nullable=True)
    start_time = Column(DateTime(timezone=True), index=True)
    end_time = Column(DateTime(timezone=True), nullable=True)
    description = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
