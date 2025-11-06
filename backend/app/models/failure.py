import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Numeric, String, Text, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class FailureSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FailureMode(str, Enum):
    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    SOFTWARE = "software"
    HUMAN_ERROR = "human_error"
    ENVIRONMENTAL = "environmental"
    WEAR = "wear"
    CORROSION = "corrosion"
    OTHER = "other"


class FailureStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    FALSE_ALARM = "false_alarm"


class FailureEvent(Base):
    """Records failure events for assets with severity and mode classification."""
    
    __tablename__ = "failure_events"
    
    # Asset reference
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Reference to the affected asset"
    )
    
    # Event identification
    event_identifier: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Business identifier for the failure event"
    )
    
    # Classification
    severity: Mapped[FailureSeverity] = mapped_column(
        String(50),
        nullable=False,
        comment="Severity level of the failure"
    )
    
    failure_mode: Mapped[FailureMode] = mapped_column(
        String(50),
        nullable=False,
        comment="Type or mode of failure"
    )
    
    status: Mapped[FailureStatus] = mapped_column(
        String(50),
        nullable=False,
        default=FailureStatus.OPEN,
        comment="Current status of the failure event"
    )
    
    # Timing information
    occurred_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        comment="When the failure occurred"
    )
    
    detected_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        comment="When the failure was detected"
    )
    
    resolved_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="When the failure was resolved"
    )
    
    # Downtime calculation (computed field)
    downtime_minutes: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Calculated downtime in minutes"
    )
    
    # Description and details
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Brief title of the failure"
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of the failure"
    )
    
    root_cause: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Identified root cause of the failure"
    )
    
    # Impact assessment
    production_impact: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Impact on production"
    )
    
    cost_impact: Mapped[float | None] = mapped_column(
        Numeric(15, 2),
        nullable=True,
        comment="Estimated financial impact"
    )
    
    # Metadata
    meta_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional failure metadata"
    )
    
    # Relationships
    asset: Mapped["Asset"] = relationship(
        "Asset",
        back_populates="failure_events"
    )
    
    updates: Mapped[list["FailureEventUpdate"]] = relationship(
        "FailureEventUpdate",
        back_populates="failure_event",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        Index(
            "ix_failure_events_asset_severity",
            "asset_id", "severity"
        ),
        Index(
            "ix_failure_events_status_occurred",
            "status", "occurred_at"
        ),
        Index(
            "ix_failure_events_occurred_at",
            "occurred_at"
        ),
        {"comment": "Asset failure events and incidents"}
    )


class FailureEventUpdate(Base):
    """Tracks updates and status changes for failure events."""
    
    __tablename__ = "failure_event_updates"
    
    # Failure event reference
    failure_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("failure_events.id"),
        nullable=False,
        index=True,
        comment="Reference to the failure event"
    )
    
    # Update information
    previous_status: Mapped[FailureStatus | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Previous status before this update"
    )
    
    new_status: Mapped[FailureStatus] = mapped_column(
        String(50),
        nullable=False,
        comment="New status after this update"
    )
    
    update_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of update (status_change, comment, investigation, etc.)"
    )
    
    # Content
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Update notes or comments"
    )
    
    # Metadata
    meta_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional update metadata"
    )
    
    # Relationships
    failure_event: Mapped["FailureEvent"] = relationship(
        "FailureEvent",
        back_populates="updates"
    )
    
    # Constraints
    __table_args__ = (
        Index(
            "ix_failure_updates_event_type",
            "failure_event_id", "update_type"
        ),
        {"comment": "Failure event status updates and comments"}
    )