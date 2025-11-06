from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Pagination(BaseModel):
    total: int = Field(ge=0)
    limit: int = Field(ge=0)
    offset: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")
