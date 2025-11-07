from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class AssetBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    asset_group_id: Optional[int] = None
    is_active: bool = True


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    asset_group_id: Optional[int] = None
    is_active: Optional[bool] = None


class Asset(AssetBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssetGroupBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None


class AssetGroupCreate(AssetGroupBase):
    pass


class AssetGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class AssetGroup(AssetGroupBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RuntimeRecordBase(BaseModel):
    asset_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    runtime_hours: Optional[Decimal] = Field(None, ge=0)
    is_active: bool = True


class RuntimeRecordCreate(RuntimeRecordBase):
    pass


class RuntimeRecord(RuntimeRecordBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class FailureBase(BaseModel):
    asset_id: int
    failure_time: datetime
    recovery_time: Optional[datetime] = None
    downtime_hours: Optional[Decimal] = Field(None, ge=0)
    failure_code: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_resolved: bool = False


class FailureCreate(FailureBase):
    pass


class FailureUpdate(BaseModel):
    recovery_time: Optional[datetime] = None
    downtime_hours: Optional[Decimal] = Field(None, ge=0)
    failure_code: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    is_resolved: Optional[bool] = None


class Failure(FailureBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KPISnapshotBase(BaseModel):
    window_type: str = Field(..., pattern=r"^(rolling|calendar)$")
    window_start: datetime
    window_end: datetime
    granularity: str = Field(..., pattern=r"^(day|week|month|7d|30d|90d)$")


class KPISnapshot(KPISnapshotBase):
    id: int
    asset_id: Optional[int] = None
    asset_group_id: Optional[int] = None
    mtbf: Optional[Decimal] = None
    failure_rate: Optional[Decimal] = None
    mttr: Optional[Decimal] = None
    availability: Optional[Decimal] = None
    total_runtime_hours: Optional[Decimal] = None
    total_downtime_hours: Optional[Decimal] = None
    failure_count: int
    source_version_hash: str
    computed_at: datetime

    model_config = {"from_attributes": True}


class KPIRequest(BaseModel):
    asset_id: Optional[int] = None
    asset_group_id: Optional[int] = None
    window_type: str = Field("rolling", pattern=r"^(rolling|calendar)$")
    granularity: str = Field("30d", pattern=r"^(day|week|month|7d|30d|90d)$")
    evaluation_time: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "asset_id": 1,
                "window_type": "rolling",
                "granularity": "30d",
                "evaluation_time": "2024-01-15T10:30:00Z",
            }
        }
    }


class KPIResponse(BaseModel):
    snapshots: list[KPISnapshot]
    total: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "snapshots": [
                    {
                        "id": 1,
                        "asset_id": 1,
                        "asset_group_id": None,
                        "window_type": "rolling",
                        "window_start": "2023-12-16T10:30:00Z",
                        "window_end": "2024-01-15T10:30:00Z",
                        "granularity": "30d",
                        "mtbf": 240.5,
                        "failure_rate": 0.004156,
                        "mttr": 8.2,
                        "availability": 0.9667,
                        "total_runtime_hours": 2405.0,
                        "total_downtime_hours": 82.0,
                        "failure_count": 10,
                        "source_version_hash": "abc123...",
                        "computed_at": "2024-01-15T10:35:00Z",
                    }
                ],
                "total": 1,
            }
        }
    }


class KPIFilters(BaseModel):
    asset_id: Optional[int] = None
    asset_group_id: Optional[int] = None
    window_type: Optional[str] = Field(None, pattern=r"^(rolling|calendar)$")
    granularity: Optional[str] = Field(None, pattern=r"^(day|week|month|7d|30d|90d)$")
    limit: int = Field(100, ge=1, le=1000)

    model_config = {
        "json_schema_extra": {
            "example": {"asset_id": 1, "window_type": "rolling", "granularity": "30d", "limit": 50}
        }
    }
