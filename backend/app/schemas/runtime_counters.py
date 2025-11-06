from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import Pagination


class RuntimeCounterBase(BaseModel):
    recorded_at: datetime
    total_hours: float = Field(ge=0)
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("total_hours")
    @classmethod
    def validate_total_hours(cls, value: float) -> float:
        if value < 0:
            raise ValueError("total_hours must be non-negative")
        return value


class RuntimeCounterCreate(RuntimeCounterBase):
    asset_id: int = Field(gt=0)


class RuntimeCounterUpdate(BaseModel):
    recorded_at: datetime | None = None
    total_hours: float | None = Field(default=None, ge=0)
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def ensure_update_fields(cls, values: "RuntimeCounterUpdate") -> "RuntimeCounterUpdate":
        if not any(
            [
                values.recorded_at is not None,
                values.total_hours is not None,
                values.metadata is not None,
            ]
        ):
            raise ValueError("At least one field must be provided for update")
        return values


class RuntimeCounterRead(BaseModel):
    id: int
    asset_id: int
    recorded_at: datetime
    total_hours: float
    delta_hours: float
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata", "attributes"),
        serialization_alias="metadata",
    )
    is_archived: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RuntimeCounterListResponse(BaseModel):
    items: list[RuntimeCounterRead]
    pagination: Pagination
    delta_hours_total: float

    model_config = ConfigDict(from_attributes=True)
