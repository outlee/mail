import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from pydantic import Field, field_validator

from app.models.kpi import KPIType
from .base import BaseSchema, TimestampedSchema


class KPISnapshotBase(BaseSchema):
    """Base KPI snapshot schema with common fields."""
    
    asset_id: uuid.UUID = Field(..., description="Reference to the asset")
    kpi_type: KPIType = Field(..., description="Type of KPI being measured")
    kpi_name: str = Field(..., max_length=100, description="Human-readable KPI name")
    period_start: datetime = Field(..., description="Start time of the measurement period")
    period_end: datetime = Field(..., description="End time of the measurement period")
    value: Decimal = Field(..., description="KPI measurement value")
    target_value: Decimal | None = Field(None, description="Target or expected value")
    baseline_value: Decimal | None = Field(None, description="Baseline or historical value")
    unit_of_measure: str = Field(..., max_length=50, description="Unit of measurement")
    data_quality_score: Decimal | None = Field(None, ge=0, le=100, description="Quality of data used for calculation (0-100)")
    confidence_level: Decimal | None = Field(None, ge=0, le=100, description="Statistical confidence level (0-100)")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional KPI metadata and calculation details")


class KPISnapshotCreate(KPISnapshotBase):
    """Schema for creating a new KPI snapshot."""
    
    @field_validator('kpi_name')
    @classmethod
    def validate_kpi_name(cls, v):
        if not v or not v.strip():
            raise ValueError('KPI name cannot be empty')
        return v.strip()
    
    @field_validator('unit_of_measure')
    @classmethod
    def validate_unit_of_measure(cls, v):
        if not v or not v.strip():
            raise ValueError('Unit of measure cannot be empty')
        return v.strip()
    
    @field_validator('period_end')
    @classmethod
    def validate_period_order(cls, v, info):
        if 'period_start' in info.data and v <= info.data['period_start']:
            raise ValueError('Period end must be after period start')
        return v


class KPISnapshotUpdate(BaseSchema):
    """Schema for updating an existing KPI snapshot."""
    
    kpi_type: KPIType | None = Field(None, description="Type of KPI being measured")
    kpi_name: str | None = Field(None, max_length=100, description="Human-readable KPI name")
    period_start: datetime | None = Field(None, description="Start time of the measurement period")
    period_end: datetime | None = Field(None, description="End time of the measurement period")
    value: Decimal | None = Field(None, description="KPI measurement value")
    target_value: Decimal | None = Field(None, description="Target or expected value")
    baseline_value: Decimal | None = Field(None, description="Baseline or historical value")
    unit_of_measure: str | None = Field(None, max_length=50, description="Unit of measurement")
    data_quality_score: Decimal | None = Field(None, ge=0, le=100, description="Quality of data used for calculation (0-100)")
    confidence_level: Decimal | None = Field(None, ge=0, le=100, description="Statistical confidence level (0-100)")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional KPI metadata and calculation details")


class KPISnapshotRead(TimestampedSchema, KPISnapshotBase):
    """Schema for reading KPI snapshot data."""
    
    pass