import uuid
from enum import Enum

from sqlalchemy import JSON, Numeric, String, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class CounterType(str, Enum):
    OPERATING_HOURS = "operating_hours"
    PRODUCTION_CYCLES = "production_cycles"
    DISTANCE_TRAVELED = "distance_traveled"
    UNITS_PRODUCED = "units_produced"
    ENERGY_CONSUMED = "energy_consumed"
    CUSTOM = "custom"


class AssetRuntimeCounter(Base):
    """Tracks operational metrics and runtime counters for assets."""
    
    __tablename__ = "asset_runtime_counters"
    
    # Asset reference
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Reference to the asset"
    )
    
    # Counter identification
    counter_type: Mapped[CounterType] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of runtime counter"
    )
    
    counter_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable counter name"
    )
    
    # Current values (non-null as per requirements)
    current_value: Mapped[float] = mapped_column(
        Numeric(20, 6),
        nullable=False,
        comment="Current counter value"
    )
    
    unit_of_measure: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Unit of measurement (e.g., hours, cycles, km)"
    )
    
    # Thresholds and targets
    warning_threshold: Mapped[float | None] = mapped_column(
        Numeric(20, 6),
        nullable=True,
        comment="Warning threshold for the counter"
    )
    
    critical_threshold: Mapped[float | None] = mapped_column(
        Numeric(20, 6),
        nullable=True,
        comment="Critical threshold for the counter"
    )
    
    target_value: Mapped[float | None] = mapped_column(
        Numeric(20, 6),
        nullable=True,
        comment="Target value for performance tracking"
    )
    
    # Metadata
    meta_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional counter metadata"
    )
    
    # Relationships
    asset: Mapped["Asset"] = relationship(
        "Asset",
        back_populates="runtime_counters"
    )
    
    # Constraints
    __table_args__ = (
        Index(
            "ix_runtime_counters_asset_type",
            "asset_id", "counter_type"
        ),
        Index(
            "ix_runtime_counters_value",
            "current_value"
        ),
        {"comment": "Asset runtime and operational counters"}
    )