import uuid
from datetime import datetime
from typing import Any, Dict

from pydantic import Field, field_validator

from app.models.asset import AssetStatus, AssetType
from .base import BaseSchema, TimestampedSchema, SoftDeleteSchema


class AssetBase(BaseSchema):
    """Base asset schema with common fields."""
    
    tenant_id: uuid.UUID = Field(..., description="Tenant identifier for multi-tenancy")
    asset_identifier: str = Field(..., max_length=100, description="Business identifier for asset")
    name: str = Field(..., max_length=255, description="Human-readable asset name")
    asset_type: AssetType = Field(default=AssetType.OTHER, description="Type of asset")
    status: AssetStatus = Field(default=AssetStatus.ACTIVE, description="Asset status")
    location: str | None = Field(None, max_length=500, description="Physical or logical location")
    description: str | None = Field(None, description="Detailed asset description")
    external_id: str | None = Field(None, max_length=255, description="External system identifier")
    manufacturer: str | None = Field(None, max_length=255, description="Asset manufacturer")
    model: str | None = Field(None, max_length=255, description="Asset model")
    serial_number: str | None = Field(None, max_length=255, description="Asset serial number")
    meta_data: Dict[str, Any] | None = Field(None, description="Flexible metadata storage")


class AssetCreate(AssetBase):
    """Schema for creating a new asset."""
    
    @field_validator('asset_identifier')
    @classmethod
    def validate_asset_identifier(cls, v):
        if not v or not v.strip():
            raise ValueError('Asset identifier cannot be empty')
        return v.strip()
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Asset name cannot be empty')
        return v.strip()


class AssetUpdate(BaseSchema):
    """Schema for updating an existing asset."""
    
    asset_identifier: str | None = Field(None, max_length=100, description="Business identifier for asset")
    name: str | None = Field(None, max_length=255, description="Human-readable asset name")
    asset_type: AssetType | None = Field(None, description="Type of asset")
    status: AssetStatus | None = Field(None, description="Asset status")
    location: str | None = Field(None, max_length=500, description="Physical or logical location")
    description: str | None = Field(None, description="Detailed asset description")
    external_id: str | None = Field(None, max_length=255, description="External system identifier")
    manufacturer: str | None = Field(None, max_length=255, description="Asset manufacturer")
    model: str | None = Field(None, max_length=255, description="Asset model")
    serial_number: str | None = Field(None, max_length=255, description="Asset serial number")
    meta_data: Dict[str, Any] | None = Field(None, description="Flexible metadata storage")


class AssetRead(TimestampedSchema, SoftDeleteSchema, AssetBase):
    """Schema for reading asset data."""
    
    pass


class AssetGroupBase(BaseSchema):
    """Base asset group schema with common fields."""
    
    tenant_id: uuid.UUID = Field(..., description="Tenant identifier for multi-tenancy")
    name: str = Field(..., max_length=255, description="Group name")
    description: str | None = Field(None, description="Group description")
    meta_data: Dict[str, Any] | None = Field(None, description="Flexible group metadata")


class AssetGroupCreate(AssetGroupBase):
    """Schema for creating a new asset group."""
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Group name cannot be empty')
        return v.strip()


class AssetGroupUpdate(BaseSchema):
    """Schema for updating an existing asset group."""
    
    name: str | None = Field(None, max_length=255, description="Group name")
    description: str | None = Field(None, description="Group description")
    meta_data: Dict[str, Any] | None = Field(None, description="Flexible group metadata")


class AssetGroupRead(TimestampedSchema, SoftDeleteSchema, AssetGroupBase):
    """Schema for reading asset group data."""
    
    pass