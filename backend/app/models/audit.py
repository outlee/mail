import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class AuditAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    VIEW = "view"
    APPROVE = "approve"
    REJECT = "reject"


class AuditLogEntry(Base):
    """Audit trail for tracking system actions and changes."""
    
    __tablename__ = "audit_log_entries"
    
    # Action information
    action: Mapped[AuditAction] = mapped_column(
        String(50),
        nullable=False,
        comment="Type of action performed"
    )
    
    entity_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Type of entity that was acted upon"
    )
    
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="ID of the entity that was acted upon"
    )
    
    # User information
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="User who performed the action"
    )
    
    username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Username of the user who performed the action"
    )
    
    # Multi-tenancy
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Tenant identifier for multi-tenancy"
    )
    
    # Action details
    description: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Description of the action performed"
    )
    
    details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description of the action"
    )
    
    # IP and session information
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="IP address from which the action was performed"
    )
    
    user_agent: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="User agent string of the client"
    )
    
    session_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Session identifier"
    )
    
    # Change tracking
    old_values: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Previous values before the change"
    )
    
    new_values: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="New values after the change"
    )
    
    # Request information
    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Request identifier for tracing"
    )
    
    endpoint: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="API endpoint or page URL"
    )
    
    # Result information
    success: Mapped[bool] = mapped_column(
        nullable=False,
        default=True,
        comment="Whether the action was successful"
    )
    
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error message if the action failed"
    )
    
    # Metadata
    meta_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional audit metadata"
    )
    
    # Constraints
    __table_args__ = (
        Index(
            "ix_audit_log_user_action",
            "user_id", "action"
        ),
        Index(
            "ix_audit_log_entity_action",
            "entity_type", "entity_id", "action"
        ),
        Index(
            "ix_audit_log_tenant_action",
            "tenant_id", "action"
        ),
        Index(
            "ix_audit_log_created_at",
            "created_at"
        ),
        {"comment": "System audit trail"}
    )