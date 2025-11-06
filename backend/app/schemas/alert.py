import uuid
from datetime import datetime
from typing import Any, Dict

from pydantic import Field, field_validator

from app.models.alert import AlertSeverity, AlertStatus, EvaluationFrequency
from .base import BaseSchema, TimestampedSchema


class AlertPolicyBase(BaseSchema):
    """Base alert policy schema with common fields."""
    
    name: str = Field(..., max_length=255, description="Policy name")
    description: str | None = Field(None, description="Policy description")
    tenant_id: uuid.UUID = Field(..., description="Tenant identifier for multi-tenancy")
    is_active: bool = Field(default=True, description="Whether the policy is currently active")
    evaluation_frequency: EvaluationFrequency = Field(default=EvaluationFrequency.HOURLY, description="How often to evaluate the policy")
    conditions: Dict[str, Any] = Field(..., description="Alert conditions and rules (JSON format)")
    severity: AlertSeverity = Field(default=AlertSeverity.WARNING, description="Default severity for alerts from this policy")
    notification_channels: Dict[str, Any] | None = Field(None, description="Notification channel configuration")
    escalation_rules: Dict[str, Any] | None = Field(None, description="Escalation rules and timeouts")
    cooldown_minutes: int = Field(default=60, description="Minimum minutes between identical alerts")
    max_alerts_per_hour: int = Field(default=10, description="Maximum alerts per hour from this policy")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional policy metadata")


class AlertPolicyCreate(AlertPolicyBase):
    """Schema for creating a new alert policy."""
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Policy name cannot be empty')
        return v.strip()
    
    @field_validator('conditions')
    @classmethod
    def validate_conditions(cls, v):
        if not v or not isinstance(v, dict):
            raise ValueError('Conditions must be a valid dictionary')
        return v
    
    @field_validator('cooldown_minutes')
    @classmethod
    def validate_cooldown_minutes(cls, v):
        if v < 0:
            raise ValueError('Cooldown minutes cannot be negative')
        return v
    
    @field_validator('max_alerts_per_hour')
    @classmethod
    def validate_max_alerts_per_hour(cls, v):
        if v <= 0:
            raise ValueError('Maximum alerts per hour must be positive')
        return v


class AlertPolicyUpdate(BaseSchema):
    """Schema for updating an existing alert policy."""
    
    name: str | None = Field(None, max_length=255, description="Policy name")
    description: str | None = Field(None, description="Policy description")
    is_active: bool | None = Field(None, description="Whether the policy is currently active")
    evaluation_frequency: EvaluationFrequency | None = Field(None, description="How often to evaluate the policy")
    conditions: Dict[str, Any] | None = Field(None, description="Alert conditions and rules (JSON format)")
    severity: AlertSeverity | None = Field(None, description="Default severity for alerts from this policy")
    notification_channels: Dict[str, Any] | None = Field(None, description="Notification channel configuration")
    escalation_rules: Dict[str, Any] | None = Field(None, description="Escalation rules and timeouts")
    cooldown_minutes: int | None = Field(None, description="Minimum minutes between identical alerts")
    max_alerts_per_hour: int | None = Field(None, description="Maximum alerts per hour from this policy")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional policy metadata")


class AlertPolicyRead(TimestampedSchema, AlertPolicyBase):
    """Schema for reading alert policy data."""
    
    pass


class AlertOccurrenceBase(BaseSchema):
    """Base alert occurrence schema with common fields."""
    
    policy_id: uuid.UUID = Field(..., description="Reference to the alert policy")
    asset_id: uuid.UUID | None = Field(None, description="Reference to the related asset (if applicable)")
    title: str = Field(..., max_length=255, description="Alert title")
    message: str = Field(..., description="Alert message content")
    severity: AlertSeverity = Field(..., description="Alert severity level")
    status: AlertStatus = Field(default=AlertStatus.ACTIVE, description="Current alert status")
    triggered_at: datetime = Field(default_factory=datetime.utcnow, description="When the alert was triggered")
    acknowledged_at: datetime | None = Field(None, description="When the alert was acknowledged")
    resolved_at: datetime | None = Field(None, description="When the alert was resolved")
    acknowledged_by: uuid.UUID | None = Field(None, description="User who acknowledged the alert")
    resolved_by: uuid.UUID | None = Field(None, description="User who resolved the alert")
    trigger_data: Dict[str, Any] | None = Field(None, description="Data that triggered the alert")
    resolution_notes: str | None = Field(None, description="Notes about the resolution")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional alert metadata")


class AlertOccurrenceCreate(AlertOccurrenceBase):
    """Schema for creating a new alert occurrence."""
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Alert title cannot be empty')
        return v.strip()
    
    @field_validator('message')
    @classmethod
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Alert message cannot be empty')
        return v.strip()


class AlertOccurrenceUpdate(BaseSchema):
    """Schema for updating an existing alert occurrence."""
    
    severity: AlertSeverity | None = Field(None, description="Alert severity level")
    status: AlertStatus | None = Field(None, description="Current alert status")
    acknowledged_at: datetime | None = Field(None, description="When the alert was acknowledged")
    resolved_at: datetime | None = Field(None, description="When the alert was resolved")
    acknowledged_by: uuid.UUID | None = Field(None, description="User who acknowledged the alert")
    resolved_by: uuid.UUID | None = Field(None, description="User who resolved the alert")
    trigger_data: Dict[str, Any] | None = Field(None, description="Data that triggered the alert")
    resolution_notes: str | None = Field(None, description="Notes about the resolution")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional alert metadata")


class AlertOccurrenceRead(TimestampedSchema, AlertOccurrenceBase):
    """Schema for reading alert occurrence data."""
    
    pass