import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from pydantic import Field, field_validator

from app.models.import_job import ImportStatus, ImportType
from .base import BaseSchema, TimestampedSchema


class CSVImportJobBase(BaseSchema):
    """Base CSV import job schema with common fields."""
    
    job_name: str = Field(..., max_length=255, description="Human-readable job name")
    import_type: ImportType = Field(..., description="Type of data being imported")
    tenant_id: uuid.UUID = Field(..., description="Tenant identifier for multi-tenancy")
    status: ImportStatus = Field(default=ImportStatus.PENDING, description="Current job status")
    progress_percentage: Decimal = Field(default=Decimal('0.0'), ge=0, le=100, description="Progress percentage (0-100)")
    original_filename: str = Field(..., max_length=500, description="Original uploaded filename")
    file_path: str = Field(..., max_length=1000, description="Path to the stored file")
    file_size_bytes: int = Field(..., description="File size in bytes")
    total_rows: int | None = Field(None, description="Total number of rows in the file")
    processed_rows: int = Field(default=0, description="Number of rows processed")
    successful_rows: int = Field(default=0, description="Number of rows successfully imported")
    failed_rows: int = Field(default=0, description="Number of rows that failed to import")
    started_at: datetime | None = Field(None, description="When the job started processing")
    completed_at: datetime | None = Field(None, description="When the job completed (successfully or failed)")
    estimated_completion_at: datetime | None = Field(None, description="Estimated completion time")
    uploaded_by: uuid.UUID = Field(..., description="User who uploaded the file")
    error_message: str | None = Field(None, description="Error message if job failed")
    error_details: Dict[str, Any] | None = Field(None, description="Detailed error information")
    import_config: Dict[str, Any] | None = Field(None, description="Import configuration and mapping")
    validation_errors: Dict[str, Any] | None = Field(None, description="Validation errors found during import")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional job metadata")


class CSVImportJobCreate(CSVImportJobBase):
    """Schema for creating a new CSV import job."""
    
    @field_validator('job_name')
    @classmethod
    def validate_job_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Job name cannot be empty')
        return v.strip()
    
    @field_validator('file_size_bytes')
    @classmethod
    def validate_file_size(cls, v):
        if v <= 0:
            raise ValueError('File size must be positive')
        return v
    
    @field_validator('processed_rows')
    @classmethod
    def validate_processed_rows(cls, v):
        if v < 0:
            raise ValueError('Processed rows cannot be negative')
        return v
    
    @field_validator('successful_rows')
    @classmethod
    def validate_successful_rows(cls, v):
        if v < 0:
            raise ValueError('Successful rows cannot be negative')
        return v
    
    @field_validator('failed_rows')
    @classmethod
    def validate_failed_rows(cls, v):
        if v < 0:
            raise ValueError('Failed rows cannot be negative')
        return v


class CSVImportJobUpdate(BaseSchema):
    """Schema for updating an existing CSV import job."""
    
    job_name: str | None = Field(None, max_length=255, description="Human-readable job name")
    status: ImportStatus | None = Field(None, description="Current job status")
    progress_percentage: Decimal | None = Field(None, ge=0, le=100, description="Progress percentage (0-100)")
    total_rows: int | None = Field(None, description="Total number of rows in the file")
    processed_rows: int | None = Field(None, description="Number of rows processed")
    successful_rows: int | None = Field(None, description="Number of rows successfully imported")
    failed_rows: int | None = Field(None, description="Number of rows that failed to import")
    started_at: datetime | None = Field(None, description="When the job started processing")
    completed_at: datetime | None = Field(None, description="When the job completed (successfully or failed)")
    estimated_completion_at: datetime | None = Field(None, description="Estimated completion time")
    error_message: str | None = Field(None, description="Error message if job failed")
    error_details: Dict[str, Any] | None = Field(None, description="Detailed error information")
    import_config: Dict[str, Any] | None = Field(None, description="Import configuration and mapping")
    validation_errors: Dict[str, Any] | None = Field(None, description="Validation errors found during import")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional job metadata")
    
    @field_validator('processed_rows')
    @classmethod
    def validate_processed_rows(cls, v):
        if v is not None and v < 0:
            raise ValueError('Processed rows cannot be negative')
        return v
    
    @field_validator('successful_rows')
    @classmethod
    def validate_successful_rows(cls, v):
        if v is not None and v < 0:
            raise ValueError('Successful rows cannot be negative')
        return v
    
    @field_validator('failed_rows')
    @classmethod
    def validate_failed_rows(cls, v):
        if v is not None and v < 0:
            raise ValueError('Failed rows cannot be negative')
        return v


class CSVImportJobRead(TimestampedSchema, CSVImportJobBase):
    """Schema for reading CSV import job data."""
    
    pass