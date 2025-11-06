from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MetadataMixin:
    attributes: Mapped[dict[str, Any] | None]

    @property
    def metadata(self) -> dict[str, Any] | None:
        return self.attributes

    @metadata.setter
    def metadata(self, value: dict[str, Any] | None) -> None:
        self.attributes = value


class Asset(MetadataMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("name", name="uq_assets_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_group: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None, nullable=True)

    runtime_counters: Mapped[list["RuntimeCounter"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
    )
    failure_events: Mapped[list["FailureEvent"]] = relationship(
        back_populates="asset",
        cascade="all, delete-orphan",
    )


class RuntimeCounter(MetadataMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "runtime_counters"
    __table_args__ = (UniqueConstraint("asset_id", "recorded_at", name="uq_runtime_counter_record"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    total_hours: Mapped[float] = mapped_column(Float, nullable=False)
    delta_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None, nullable=True)

    asset: Mapped[Asset] = relationship(back_populates="runtime_counters")


class FailureEvent(MetadataMixin, TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "failure_events"
    __table_args__ = (UniqueConstraint("asset_id", "occurred_at", name="uq_failure_event_record"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    downtime_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None, nullable=True)

    asset: Mapped[Asset] = relationship(back_populates="failure_events")


__all__ = ["Asset", "RuntimeCounter", "FailureEvent"]
