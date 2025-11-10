import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Numeric, String, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class KPIType(str, Enum):
    MTBF = "mtbf"  # Mean Time Between Failures
    MTTR = "mttr"  # Mean Time To Repair
    AVAILABILITY = "availability"
    RELIABILITY = "reliability"
    PERFORMANCE = "performance"
    QUALITY = "quality"
    OEE = "oee"  # Overall Equipment Effectiveness
    CUSTOM = "custom"


class KPISnapshot(Base):
    """Stores KPI snapshots for performance tracking and analytics."""
    
    __tablename__ = "kpi_snapshots"
    
    # Asset reference
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Reference to the asset"
    )
    
    # Snapshot identification
    kpi_type: Mapped[KPIType] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of KPI being measured"
    )
    
    kpi_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Human-readable KPI name"
    )
    
    # Time period for the snapshot
    period_start: Mapped[datetime] = mapped_column(
        nullable=False,
        comment="Start time of the measurement period"
    )
    
    period_end: Mapped[datetime] = mapped_column(
        nullable=False,
        comment="End time of the measurement period"
    )
    
    # KPI values
    value: Mapped[float] = mapped_column(
        Numeric(20, 6),
        nullable=False,
        comment="KPI measurement value"
    )
    
    target_value: Mapped[float | None] = mapped_column(
        Numeric(20, 6),
        nullable=True,
        comment="Target or expected value"
    )
    
    baseline_value: Mapped[float | None] = mapped_column(
        Numeric(20, 6),
        nullable=True,
        comment="Baseline or historical value"
    )
    
    # Units and formatting
    unit_of_measure: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Unit of measurement (e.g., hours, percentage, count)"
    )
    
    # Quality indicators
    data_quality_score: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Quality of data used for calculation (0-100)"
    )
    
    confidence_level: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
        comment="Statistical confidence level (0-100)"
    )
    
    # Metadata
    meta_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional KPI metadata and calculation details"
    )
    
    # Relationships
    asset: Mapped["Asset"] = relationship(
        "Asset",
        back_populates="kpi_snapshots"
    )
    
    # Constraints
    __table_args__ = (
        Index(
            "ix_kpi_snapshots_asset_type_period",
            "asset_id", "kpi_type", "period_start", "period_end"
        ),
        Index(
            "ix_kpi_snapshots_period_end",
            "period_end"
        ),
        Index(
            "ix_kpi_snapshots_type_period",
            "kpi_type", "period_start"
        ),
        {"comment": "KPI measurement snapshots for analytics"}
    )