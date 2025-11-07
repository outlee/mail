from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLAlchemyEnum, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class UserRole(str, Enum):
    MAINTAINER = "maintainer"
    OPERATOR = "operator"
    MANAGER = "manager"


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


class TaskRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Asset(Base):
    __tablename__ = "assets"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Group(Base):
    __tablename__ = "groups"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class KPISnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id = Column(String(36), primary_key=True, index=True)
    asset_id = Column(String(36), index=True, nullable=True)
    group_id = Column(String(36), index=True, nullable=True)
    kpi_type = Column(String(100), index=True)
    value = Column(Float)
    period_start = Column(DateTime(timezone=True), index=True)
    period_end = Column(DateTime(timezone=True), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TaskRun(Base):
    __tablename__ = "task_runs"

    id = Column(String(36), primary_key=True, index=True)
    task_name = Column(String(255), index=True)
    task_id = Column(String(255), index=True, nullable=True)
    status = Column(SQLAlchemyEnum(TaskRunStatus), default=TaskRunStatus.PENDING, index=True)
    scope = Column(String(100), nullable=True)
    asset_id = Column(String(36), index=True, nullable=True)
    group_id = Column(String(36), index=True, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    items_processed = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


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


class AlertPolicy(Base):
    __tablename__ = "alert_policies"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), index=True)
    description = Column(Text, nullable=True)
    metric_name = Column(String(100), index=True)
    comparator = Column(SQLAlchemyEnum(AlertComparator), index=True)
    threshold = Column(Float)
    severity = Column(SQLAlchemyEnum(AlertSeverity), default=AlertSeverity.MEDIUM, index=True)
    deduplication_window_minutes = Column(Integer, default=60)
    email_recipients = Column(Text, nullable=True)  # JSON array of emails
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AlertOccurrence(Base):
    __tablename__ = "alert_occurrences"

    id = Column(String(36), primary_key=True, index=True)
    policy_id = Column(String(36), index=True)
    asset_id = Column(String(36), index=True, nullable=True)
    group_id = Column(String(36), index=True, nullable=True)
    kpi_snapshot_id = Column(String(36), index=True)
    status = Column(SQLAlchemyEnum(AlertStatus), default=AlertStatus.ACTIVE, index=True)
    severity = Column(SQLAlchemyEnum(AlertSeverity), index=True)
    current_value = Column(Float)
    threshold_value = Column(Float)
    message = Column(Text)
    last_notification_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String(36), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolved_by = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AlertEventLog(Base):
    __tablename__ = "alert_event_logs"

    id = Column(String(36), primary_key=True, index=True)
    alert_occurrence_id = Column(String(36), index=True)
    event_type = Column(String(50))  # TRIGGERED, NOTIFIED, ACKNOWLEDGED, RESOLVED
    message = Column(Text)
    metadata = Column(Text, nullable=True)  # JSON metadata
    user_id = Column(String(36), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
