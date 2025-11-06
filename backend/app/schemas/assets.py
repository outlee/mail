from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import Pagination


class AssetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    asset_group: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    asset_group: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def ensure_at_least_one_field(cls, values: "AssetUpdate") -> "AssetUpdate":
        if not any(
            [
                values.name is not None,
                values.asset_group is not None,
                values.description is not None,
                values.metadata is not None,
            ]
        ):
            raise ValueError("At least one field must be provided for update")
        return values


class AssetRead(BaseModel):
    id: int
    name: str
    asset_group: str
    description: str | None
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


class AssetListResponse(BaseModel):
    items: list[AssetRead]
    pagination: Pagination

    model_config = ConfigDict(from_attributes=True)
