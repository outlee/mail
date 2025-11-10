import uuid
from decimal import Decimal
from typing import Any, Dict

from pydantic import Field, field_validator

from app.models.monitoring import CounterType
from .base import BaseSchema, TimestampedSchema


class AssetRuntimeCounterBase(BaseSchema):
    """Base runtime counter schema with common fields."""
    
    asset_id: uuid.UUID = Field(..., description="Reference to asset")
    counter_type: CounterType = Field(..., description="Type of runtime counter")
    counter_name: str = Field(..., max_length=100, description="Human-readable counter name")
    current_value: Decimal = Field(..., description="Current counter value")
    unit_of_measure: str = Field(..., max_length=50, description="Unit of measurement")
    warning_threshold: Decimal | None = Field(None, description="Warning threshold for the counter")
    critical_threshold: Decimal | None = Field(None, description="Critical threshold for the counter")
    target_value: Decimal | None = Field(None, description="Target value for performance tracking")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional counter metadata")


class AssetRuntimeCounterCreate(AssetRuntimeCounterBase):
    """Schema for creating a new runtime counter."""
    
    @field_validator('counter_name')
    @classmethod
    def validate_counter_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Counter name cannot be empty')
        return v.strip()
    
    @field_validator('unit_of_measure')
    @classmethod
    def validate_unit_of_measure(cls, v):
        if not v or not v.strip():
            raise ValueError('Unit of measure cannot be empty')
        return v.strip()
    
    @field_validator('current_value')
    @classmethod
    def validate_current_value(cls, v):
        if v < 0:
            raise ValueError('Current value cannot be negative')
        return v


class AssetRuntimeCounterUpdate(BaseSchema):
    """Schema for updating an existing runtime counter."""
    
    counter_type: CounterType | None = Field(None, description="Type of runtime counter")
    counter_name: str | None = Field(None, max_length=100, description="Human-readable counter name")
    current_value: Decimal | None = Field(None, description="Current counter value")
    unit_of_measure: str | None = Field(None, max_length=50, description="Unit of measurement")
    warning_threshold: Decimal | None = Field(None, description="Warning threshold for the counter")
    critical_threshold: Decimal | None = Field(None, description="Critical threshold for the counter")
    target_value: Decimal | None = Field(None, description="Target value for performance tracking")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional counter metadata")
    
    @field_validator('current_value')
    @classmethod
    def validate_current_value(cls, v):
        if v is not None and v < 0:
            raise ValueError('Current value cannot be negative')
        return v


class AssetRuntimeCounterRead(TimestampedSchema, AssetRuntimeCounterBase):
    """Schema for reading runtime counter data."""
    
    pass