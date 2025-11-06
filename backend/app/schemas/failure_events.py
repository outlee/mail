from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import Pagination


class FailureEventBase(BaseModel):
    occurred_at: datetime
    resolved_at: datetime | None = None
    description: str | None = Field(default=None, max_length=1000)
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_timestamps(cls, values: "FailureEventBase") -> "FailureEventBase":
        resolved = values.resolved_at
        occurred = values.occurred_at
        if resolved is not None and resolved < occurred:
            raise ValueError("resolved_at must be greater than or equal to occurred_at")
        return values


class FailureEventCreate(FailureEventBase):
    asset_id: int = Field(gt=0)


class FailureEventUpdate(BaseModel):
    occurred_at: datetime | None = None
    resolved_at: datetime | None = None
    description: str | None = Field(default=None, max_length=1000)
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def ensure_fields(cls, values: "FailureEventUpdate") -> "FailureEventUpdate":
        if not any(
            [
                values.occurred_at is not None,
                values.resolved_at is not None,
                values.description is not None,
                values.metadata is not None,
            ]
        ):
            raise ValueError("At least one field must be provided for update")
        if (
            values.occurred_at is not None
            and values.resolved_at is not None
            and values.resolved_at < values.occurred_at
        ):
            raise ValueError("resolved_at must be greater than or equal to occurred_at")
        return values


class FailureEventRead(BaseModel):
    id: int
    asset_id: int
    occurred_at: datetime
    resolved_at: datetime | None
    description: str | None
    downtime_minutes: int | None
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


class FailureEventListResponse(BaseModel):
    items: list[FailureEventRead]
    pagination: Pagination

    model_config = ConfigDict(from_attributes=True)
