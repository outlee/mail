import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from pydantic import Field, field_validator

from app.models.failure import FailureSeverity, FailureMode, FailureStatus
from .base import BaseSchema, TimestampedSchema


class FailureEventBase(BaseSchema):
    """Base failure event schema with common fields."""
    
    asset_id: uuid.UUID = Field(..., description="Reference to the affected asset")
    event_identifier: str = Field(..., max_length=100, description="Business identifier for the failure event")
    severity: FailureSeverity = Field(..., description="Severity level of the failure")
    failure_mode: FailureMode = Field(..., description="Type or mode of failure")
    status: FailureStatus = Field(default=FailureStatus.OPEN, description="Current status of the failure event")
    occurred_at: datetime = Field(..., description="When the failure occurred")
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="When the failure was detected")
    resolved_at: datetime | None = Field(None, description="When the failure was resolved")
    downtime_minutes: int = Field(default=0, description="Calculated downtime in minutes")
    title: str = Field(..., max_length=255, description="Brief title of the failure")
    description: str | None = Field(None, description="Detailed description of the failure")
    root_cause: str | None = Field(None, description="Identified root cause of the failure")
    production_impact: str | None = Field(None, description="Impact on production")
    cost_impact: Decimal | None = Field(None, description="Estimated financial impact")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional failure metadata")


class FailureEventCreate(FailureEventBase):
    """Schema for creating a new failure event."""
    
    @field_validator('event_identifier')
    @classmethod
    def validate_event_identifier(cls, v):
        if not v or not v.strip():
            raise ValueError('Event identifier cannot be empty')
        return v.strip()
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
    
    @field_validator('downtime_minutes')
    @classmethod
    def validate_downtime_minutes(cls, v):
        if v < 0:
            raise ValueError('Downtime minutes cannot be negative')
        return v


class FailureEventUpdate(BaseSchema):
    """Schema for updating an existing failure event."""
    
    severity: FailureSeverity | None = Field(None, description="Severity level of the failure")
    failure_mode: FailureMode | None = Field(None, description="Type or mode of failure")
    status: FailureStatus | None = Field(None, description="Current status of the failure event")
    occurred_at: datetime | None = Field(None, description="When the failure occurred")
    detected_at: datetime | None = Field(None, description="When the failure was detected")
    resolved_at: datetime | None = Field(None, description="When the failure was resolved")
    downtime_minutes: int | None = Field(None, description="Calculated downtime in minutes")
    title: str | None = Field(None, max_length=255, description="Brief title of the failure")
    description: str | None = Field(None, description="Detailed description of the failure")
    root_cause: str | None = Field(None, description="Identified root cause of the failure")
    production_impact: str | None = Field(None, description="Impact on production")
    cost_impact: Decimal | None = Field(None, description="Estimated financial impact")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional failure metadata")
    
    @field_validator('downtime_minutes')
    @classmethod
    def validate_downtime_minutes(cls, v):
        if v is not None and v < 0:
            raise ValueError('Downtime minutes cannot be negative')
        return v


class FailureEventRead(TimestampedSchema, FailureEventBase):
    """Schema for reading failure event data."""
    
    pass


class FailureEventUpdateBase(BaseSchema):
    """Base failure event update schema with common fields."""
    
    failure_event_id: uuid.UUID = Field(..., description="Reference to the failure event")
    previous_status: FailureStatus | None = Field(None, description="Previous status before this update")
    new_status: FailureStatus = Field(..., description="New status after this update")
    update_type: str = Field(..., max_length=50, description="Type of update")
    notes: str | None = Field(None, description="Update notes or comments")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional update metadata")


class FailureEventUpdateCreate(FailureEventUpdateBase):
    """Schema for creating a new failure event update."""
    
    @field_validator('update_type')
    @classmethod
    def validate_update_type(cls, v):
        if not v or not v.strip():
            raise ValueError('Update type cannot be empty')
        return v.strip()


class FailureEventUpdateRead(TimestampedSchema, FailureEventUpdateBase):
    """Schema for reading failure event update data."""
    
    pass