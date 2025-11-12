import uuid
from enum import Enum

from sqlalchemy import JSON, String, Text, Boolean, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


class Role(Base):
    """System roles for authorization and access control."""
    
    __tablename__ = "roles"
    
    # Role identification
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Unique role name"
    )
    
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable role display name"
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Role description and responsibilities"
    )
    
    # Role properties
    is_system_role: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Indicates if this is a system-defined role"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether the role is currently active"
    )
    
    # Permissions (stored as JSON for flexibility)
    permissions: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Role permissions and access rights"
    )
    
    # Metadata
    meta_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional role metadata"
    )
    
    # Relationships
    users: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        Index("ix_roles_active", "is_active"),
        {"comment": "System roles for authorization"}
    )


class User(Base, SoftDeleteMixin):
    """User accounts for authentication and authorization."""
    
    __tablename__ = "users"
    
    # User identification
    username: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique username for login"
    )
    
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="Unique email address"
    )
    
    # Profile information
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="User's first name"
    )
    
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="User's last name"
    )
    
    # Authentication
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Hashed password"
    )
    
    # Status and properties
    status: Mapped[UserStatus] = mapped_column(
        String(50),
        nullable=False,
        default=UserStatus.PENDING,
        comment="Account status"
    )
    
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether the user's email has been verified"
    )
    
    # Multi-tenancy support
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Tenant identifier for multi-tenancy"
    )
    
    # Contact information
    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Phone number"
    )
    
    department: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Department or organization unit"
    )
    
    job_title: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Job title or position"
    )
    
    # Metadata
    meta_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional user metadata"
    )
    
    # Relationships
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        Index("ix_users_status", "status"),
        Index("ix_users_tenant", "tenant_id"),
        {"comment": "User accounts and authentication"}
    )


class UserRole(Base):
    """Many-to-many relationship between users and roles."""
    
    __tablename__ = "user_roles"
    
    # References
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Reference to the user"
    )
    
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Reference to the role"
    )
    
    # Assignment properties
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="User who made this assignment"
    )
    
    expires_at: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="When this role assignment expires"
    )
    
    # Metadata
    meta_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Additional assignment metadata"
    )
    
    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_roles"
    )
    
    role: Mapped["Role"] = relationship(
        "Role",
        back_populates="users"
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "user_id", "role_id",
            name="uq_user_roles_user_role",
            comment="User can only have the same role assigned once"
        ),
        {"comment": "User role assignments"}
    )