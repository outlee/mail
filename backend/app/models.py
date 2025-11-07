from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    asset_group_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("asset_groups.id"), index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    asset_group: Mapped[Optional["AssetGroup"]] = relationship(
        "AssetGroup", back_populates="assets"
    )
    runtime_records: Mapped[list["RuntimeRecord"]] = relationship(
        "RuntimeRecord", back_populates="asset", cascade="all, delete-orphan"
    )
    failures: Mapped[list["Failure"]] = relationship(
        "Failure", back_populates="asset", cascade="all, delete-orphan"
    )
    kpi_snapshots: Mapped[list["KPISnapshot"]] = relationship(
        "KPISnapshot", back_populates="asset", cascade="all, delete-orphan"
    )


class AssetGroup(Base):
    __tablename__ = "asset_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    assets: Mapped[list["Asset"]] = relationship(
        "Asset", back_populates="asset_group", cascade="all, delete-orphan"
    )
    kpi_snapshots: Mapped[list["KPISnapshot"]] = relationship(
        "KPISnapshot", back_populates="asset_group", cascade="all, delete-orphan"
    )


class RuntimeRecord(Base):
    __tablename__ = "runtime_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    runtime_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=3), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="runtime_records")


class Failure(Base):
    __tablename__ = "failures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(Integer, ForeignKey("assets.id"), nullable=False)
    failure_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    recovery_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    downtime_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=10, scale=3), nullable=True
    )
    failure_code: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="failures")


class KPISnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("assets.id"), nullable=True, index=True
    )
    asset_group_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("asset_groups.id"), nullable=True, index=True
    )
    window_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'rolling' or 'calendar'
    window_start: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    window_end: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    granularity: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'day', 'week', 'month', '7d', '30d', '90d'

    # KPI Metrics (all nullable to handle edge cases)
    mtbf: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=15, scale=3), nullable=True
    )  # Mean Time Between Failures (hours)
    failure_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=15, scale=6), nullable=True
    )  # λ = 1/MTBF (failures per hour)
    mttr: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=15, scale=3), nullable=True
    )  # Mean Time To Repair (hours)
    availability: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=5, scale=4), nullable=True
    )  # Availability ratio (0-1)

    # Source data counts
    total_runtime_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=15, scale=3), nullable=True
    )
    total_downtime_hours: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=15, scale=3), nullable=True
    )
    failure_count: Mapped[int] = mapped_column(Integer, default=0)

    # Metadata
    source_version_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "window_type",
            "window_start",
            "granularity",
            name="uq_kpi_snapshot_asset_window",
        ),
        UniqueConstraint(
            "asset_group_id",
            "window_type",
            "window_start",
            "granularity",
            name="uq_kpi_snapshot_group_window",
        ),
    )

    # Relationships
    asset: Mapped[Optional["Asset"]] = relationship("Asset", back_populates="kpi_snapshots")
    asset_group: Mapped[Optional["AssetGroup"]] = relationship(
        "AssetGroup", back_populates="kpi_snapshots"
    )
