from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLAlchemyEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
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


class CSVImportType(str, Enum):
    ASSETS = "assets"
    RUNTIME = "runtime"
    FAILURES = "failures"


class CSVImportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
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
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


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
    external_id = Column(String(64), unique=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Group(Base):
    __tablename__ = "groups"

    id = Column(String(36), primary_key=True, index=True)
    external_id = Column(String(64), unique=True, index=True, nullable=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class KPISnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id = Column(String(36), primary_key=True, index=True)
    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=True, index=True)
    group_id = Column(String(36), ForeignKey("groups.id"), nullable=True, index=True)
    kpi_type = Column(String(64), nullable=False)
    value = Column(Float, nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class TaskRun(Base):
    __tablename__ = "task_runs"

    id = Column(String(36), primary_key=True, index=True)
    task_name = Column(String(255), nullable=False)
    task_id = Column(String(255), nullable=True)
    status = Column(
        SQLAlchemyEnum(TaskRunStatus),
        default=TaskRunStatus.PENDING,
        nullable=False,
        index=True,
    )
    scope = Column(String(255), nullable=True)
    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=True)
    group_id = Column(String(36), ForeignKey("groups.id"), nullable=True)
    items_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class RuntimeCounter(Base):
    __tablename__ = "runtime_counters"

    id = Column(String(36), primary_key=True, index=True)
    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=False, index=True)
    counter_name = Column(String(128), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    value = Column(Float, nullable=False)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "asset_id", "counter_name", "recorded_at", name="uq_runtime_counter"
        ),
    )


class FailureEvent(Base):
    __tablename__ = "failure_events"

    id = Column(String(36), primary_key=True, index=True)
    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=False, index=True)
    failure_code = Column(String(128), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    description = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "asset_id", "failure_code", "occurred_at", name="uq_failure_event"
        ),
    )


class CSVImportJob(Base):
    __tablename__ = "csv_import_jobs"

    id = Column(String(36), primary_key=True, index=True)
    import_type = Column(SQLAlchemyEnum(CSVImportType), nullable=False, index=True)
    idempotency_key = Column(String(128), nullable=False, index=True)
    status = Column(
        SQLAlchemyEnum(CSVImportStatus),
        default=CSVImportStatus.PENDING,
        nullable=False,
        index=True,
    )
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    source_filename = Column(String(255), nullable=True)
    storage_path = Column(String(1024), nullable=False)
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    skipped_rows = Column(Integer, default=0)
    error_rows = Column(Integer, default=0)
    error_sample = Column(JSON, nullable=True)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "import_type", "idempotency_key", name="uq_csv_import_idempotency"
        ),
    )


