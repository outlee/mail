import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, Numeric, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class EvaluationFrequency(str, Enum):
    REALTIME = "realtime"
    MINUTELY = "minutely"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class AlertPolicy(Base):
    """Defines alerting policies and rules for monitoring."""
    
    __tablename__ = "alert_policies"
    
    # Policy identification
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Policy name"
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Policy description"
    )
    
    # Multi-tenancy
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant identifier for multi-tenancy"
    )
    
    # Policy configuration
    is_active: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        comment="Whether the policy is currently active"
    )
    
    evaluation_frequency: Mapped[EvaluationFrequency] = mapped_column(
        String(50),
        nullable=False,
        default=EvaluationFrequency.HOURLY,
        comment="How often to evaluate the policy"
    )
    
    # Alert conditions (stored as JSON for flexibility)
    conditions: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="Alert conditions and rules (JSON format)"
    )
    
    # Alert configuration
    severity: Mapped[AlertSeverity] = mapped_column(
        String(50),
        nullable=False,
        default=AlertSeverity.WARNING,
        comment="Default severity for alerts from this policy"
    )
    
    # Notification settings
    notification_channels: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Notification channel configuration"
    )
    
    # Escalation settings
    escalation_rules: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Escalation rules and timeouts"
    )
    
    # Rate limiting
    cooldown_minutes: Mapped[int] = mapped_column(
        nullable=False,
        default=60,
        comment="Minimum minutes between identical alerts"
    )
    
    max_alerts_per_hour: Mapped[int] = mapped_column(
        nullable=False,
        default=10,
        comment="Maximum alerts per hour from this policy"
    )
    
    # Metadata
    meta_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional policy metadata"
    )
    
    # Relationships
    occurrences: Mapped[list["AlertOccurrence"]] = relationship(
        "AlertOccurrence",
        back_populates="policy",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        Index("ix_alert_policies_tenant_active", "tenant_id", "is_active"),
        {"comment": "Alert policies and rules configuration"}
    )


class AlertOccurrence(Base):
    """Represents individual alert occurrences triggered by policies."""
    
    __tablename__ = "alert_occurrences"
    
    # Policy reference
    policy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Reference to the alert policy"
    )
    
    # Asset reference (if applicable)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Reference to the related asset (if applicable)"
    )
    
    # Alert information
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Alert title"
    )
    
    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Alert message content"
    )
    
    severity: Mapped[AlertSeverity] = mapped_column(
        String(50),
        nullable=False,
        comment="Alert severity level"
    )
    
    status: Mapped[AlertStatus] = mapped_column(
        String(50),
        nullable=False,
        default=AlertStatus.ACTIVE,
        comment="Current alert status"
    )
    
    # Timing
    triggered_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=datetime.utcnow,
        comment="When the alert was triggered"
    )
    
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="When the alert was acknowledged"
    )
    
    resolved_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="When the alert was resolved"
    )
    
    # Acknowledgment and resolution
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who acknowledged the alert"
    )
    
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who resolved the alert"
    )
    
    # Alert details
    trigger_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Data that triggered the alert"
    )
    
    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Notes about the resolution"
    )
    
    # Metadata
    meta_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional alert metadata"
    )
    
    # Relationships
    policy: Mapped["AlertPolicy"] = relationship(
        "AlertPolicy",
        back_populates="occurrences"
    )
    
    # Constraints
    __table_args__ = (
        Index(
            "ix_alert_occurrences_policy_status",
            "policy_id", "status"
        ),
        Index(
            "ix_alert_occurrences_severity_triggered",
            "severity", "triggered_at"
        ),
        Index(
            "ix_alert_occurrences_asset_status",
            "asset_id", "status"
        ),
        {"comment": "Individual alert occurrences"}
    )