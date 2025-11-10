from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLAlchemyEnum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

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


class FailureSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


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
    name = Column(String(255), unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Group(Base):
    __tablename__ = "groups"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AssetRuntime(Base):
    __tablename__ = "asset_runtimes"

    id = Column(String(36), primary_key=True, index=True)
    asset_id = Column(String(36), ForeignKey("assets.id"), index=True)
    runtime_counter = Column(Integer, nullable=False)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    metadata = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    asset = relationship("Asset")


class FailureEvent(Base):
    __tablename__ = "failure_events"

    id = Column(String(36), primary_key=True, index=True)
    asset_id = Column(String(36), ForeignKey("assets.id"), index=True)
    severity = Column(SQLAlchemyEnum(FailureSeverity), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=True, index=True)
    description = Column(Text, nullable=False)
    metadata = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    asset = relationship("Asset")


class KPISnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id = Column(String(36), primary_key=True, index=True)
    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=True, index=True)
    group_id = Column(String(36), ForeignKey("groups.id"), nullable=True, index=True)
    kpi_type = Column(String(50), nullable=False, index=True)
    value = Column(Float, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    asset = relationship("Asset")
    group = relationship("Group")


class TaskRun(Base):
    __tablename__ = "task_runs"

    id = Column(String(36), primary_key=True, index=True)
    task_name = Column(String(255), nullable=False, index=True)
    task_id = Column(String(255), nullable=True, index=True)
    status = Column(SQLAlchemyEnum(TaskRunStatus), default=TaskRunStatus.PENDING, index=True)
    scope = Column(String(50), nullable=True, index=True)
    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=True, index=True)
    group_id = Column(String(36), ForeignKey("groups.id"), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    items_processed = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    asset = relationship("Asset")
    group = relationship("Group")


class AuditLogEntry(Base):
    __tablename__ = "audit_log_entries"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    action = Column(SQLAlchemyEnum(AuditAction), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(36), nullable=False, index=True)
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    ip_address = Column(String(45), nullable=True)

    user = relationship("User")


class DataQualityReport(Base):
    __tablename__ = "data_quality_reports"

    id = Column(String(36), primary_key=True, index=True)
    report_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    summary = Column(Text, nullable=True)
    details = Column(Text, nullable=True)
    issues_found = Column(Integer, default=0)
    assets_checked = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
