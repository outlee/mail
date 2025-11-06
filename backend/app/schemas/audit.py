import uuid
from datetime import datetime
from typing import Any, Dict

from pydantic import Field, field_validator

from app.models.audit import AuditAction
from .base import BaseSchema, TimestampedSchema


class AuditLogEntryBase(BaseSchema):
    """Base audit log entry schema with common fields."""
    
    action: AuditAction = Field(..., description="Type of action performed")
    entity_type: str = Field(..., max_length=100, description="Type of entity that was acted upon")
    entity_id: uuid.UUID | None = Field(None, description="ID of the entity that was acted upon")
    user_id: uuid.UUID | None = Field(None, description="User who performed the action")
    username: str | None = Field(None, max_length=100, description="Username of the user who performed the action")
    tenant_id: uuid.UUID | None = Field(None, description="Tenant identifier for multi-tenancy")
    description: str = Field(..., max_length=500, description="Description of the action performed")
    details: str | None = Field(None, description="Detailed description of the action")
    ip_address: str | None = Field(None, max_length=45, description="IP address from which the action was performed")
    user_agent: str | None = Field(None, max_length=1000, description="User agent string of the client")
    session_id: str | None = Field(None, max_length=255, description="Session identifier")
    old_values: Dict[str, Any] | None = Field(None, description="Previous values before the change")
    new_values: Dict[str, Any] | None = Field(None, description="New values after the change")
    request_id: str | None = Field(None, max_length=100, description="Request identifier for tracing")
    endpoint: str | None = Field(None, max_length=500, description="API endpoint or page URL")
    success: bool = Field(default=True, description="Whether the action was successful")
    error_message: str | None = Field(None, description="Error message if the action failed")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional audit metadata")


class AuditLogEntryCreate(AuditLogEntryBase):
    """Schema for creating a new audit log entry."""
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError('Description cannot be empty')
        return v.strip()
    
    @field_validator('entity_type')
    @classmethod
    def validate_entity_type(cls, v):
        if not v or not v.strip():
            raise ValueError('Entity type cannot be empty')
        return v.strip().lower()


class AuditLogEntryRead(TimestampedSchema, AuditLogEntryBase):
    """Schema for reading audit log entry data."""
    
    pass