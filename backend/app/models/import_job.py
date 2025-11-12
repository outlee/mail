import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Numeric, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class ImportStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportType(str, Enum):
    ASSETS = "assets"
    FAILURE_EVENTS = "failure_events"
    KPI_DATA = "kpi_data"
    MAINTENANCE_RECORDS = "maintenance_records"
    OTHER = "other"


class CSVImportJob(Base):
    """Tracks CSV import jobs for bulk data ingestion."""
    
    __tablename__ = "csv_import_jobs"
    
    # Job identification
    job_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable job name"
    )
    
    import_type: Mapped[ImportType] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of data being imported"
    )
    
    # Multi-tenancy
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant identifier for multi-tenancy"
    )
    
    # Job status and progress
    status: Mapped[ImportStatus] = mapped_column(
        String(50),
        nullable=False,
        default=ImportStatus.PENDING,
        comment="Current job status"
    )
    
    progress_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0.0,
        comment="Progress percentage (0-100)"
    )
    
    # File information
    original_filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Original uploaded filename"
    )
    
    file_path: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="Path to the stored file"
    )
    
    file_size_bytes: Mapped[int] = mapped_column(
        nullable=False,
        comment="File size in bytes"
    )
    
    # Processing statistics
    total_rows: Mapped[int | None] = mapped_column(
        nullable=True,
        comment="Total number of rows in the file"
    )
    
    processed_rows: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Number of rows processed"
    )
    
    successful_rows: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Number of rows successfully imported"
    )
    
    failed_rows: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Number of rows that failed to import"
    )
    
    # Timing
    started_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="When the job started processing"
    )
    
    completed_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="When the job completed (successfully or failed)"
    )
    
    estimated_completion_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Estimated completion time"
    )
    
    # User information
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="User who uploaded the file"
    )
    
    # Error handling
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if job failed"
    )
    
    error_details: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Detailed error information"
    )
    
    # Configuration
    import_config: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Import configuration and mapping"
    )
    
    # Validation results
    validation_errors: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=list,
        comment="Validation errors found during import"
    )
    
    # Metadata
    meta_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional job metadata"
    )
    
    # Constraints
    __table_args__ = (
        Index(
            "ix_csv_import_jobs_tenant_status",
            "tenant_id", "status"
        ),
        Index(
            "ix_csv_import_jobs_type_status",
            "import_type", "status"
        ),
        Index(
            "ix_csv_import_jobs_uploaded_by",
            "uploaded_by"
        ),
        {"comment": "CSV import job tracking"}
    )