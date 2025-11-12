import uuid
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
    )


class TimestampedSchema(BaseSchema):
    """Base schema with timestamp fields."""
    
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SoftDeleteSchema(BaseSchema):
    """Base schema with soft delete fields."""
    
    deleted_at: datetime | None = None
    is_deleted: bool = False


class MetadataSchema(BaseSchema):
    """Base schema with metadata field."""
    
    meta_data: Dict[str, Any] | None = None