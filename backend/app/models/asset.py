import uuid
from enum import Enum

from sqlalchemy import JSON, String, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, SoftDeleteMixin


class AssetStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    DECOMMISSIONED = "decommissioned"


class AssetType(str, Enum):
    MACHINERY = "machinery"
    VEHICLE = "vehicle"
    EQUIPMENT = "equipment"
    FACILITY = "facility"
    SOFTWARE = "software"
    OTHER = "other"


class Asset(Base, SoftDeleteMixin):
    """Represents a physical or digital asset in the system."""
    
    __tablename__ = "assets"
    
    # Core identification
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant identifier for multi-tenancy"
    )
    
    asset_identifier: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Business identifier for the asset"
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable asset name"
    )
    
    # Classification
    asset_type: Mapped[AssetType] = mapped_column(
        String(50),
        nullable=False,
        default=AssetType.OTHER
    )
    
    status: Mapped[AssetStatus] = mapped_column(
        String(50),
        nullable=False,
        default=AssetStatus.ACTIVE
    )
    
    # Location and description
    location: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Physical or logical location"
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed asset description"
    )
    
    # Metadata
    meta_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Flexible metadata storage"
    )
    
    # External references
    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        comment="External system identifier"
    )
    
    manufacturer: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Asset manufacturer"
    )
    
    model: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Asset model"
    )
    
    serial_number: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Asset serial number"
    )
    
    # Relationships
    runtime_counters: Mapped[list["AssetRuntimeCounter"]] = relationship(
        "AssetRuntimeCounter",
        back_populates="asset",
        cascade="all, delete-orphan"
    )
    
    failure_events: Mapped[list["FailureEvent"]] = relationship(
        "FailureEvent",
        back_populates="asset",
        cascade="all, delete-orphan"
    )
    
    kpi_snapshots: Mapped[list["KPISnapshot"]] = relationship(
        "KPISnapshot",
        back_populates="asset",
        cascade="all, delete-orphan"
    )
    
    # Group memberships
    group_memberships: Mapped[list["AssetGroupMember"]] = relationship(
        "AssetGroupMember",
        back_populates="asset",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "asset_identifier",
            name="uq_assets_tenant_identifier",
            comment="Asset identifiers must be unique within tenant"
        ),
        Index("ix_assets_tenant_status", "tenant_id", "status"),
        Index("ix_assets_type_status", "asset_type", "status"),
        {"comment": "Core asset registry"}
    )


class AssetGroup(Base, SoftDeleteMixin):
    """Represents logical groupings of assets."""
    
    __tablename__ = "asset_groups"
    
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Tenant identifier for multi-tenancy"
    )
    
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Group name"
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Group description"
    )
    
    meta_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Flexible group metadata"
    )
    
    # Relationships
    members: Mapped[list["AssetGroupMember"]] = relationship(
        "AssetGroupMember",
        back_populates="group",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "name",
            name="uq_asset_groups_tenant_name",
            comment="Group names must be unique within tenant"
        ),
        {"comment": "Logical groupings of assets"}
    )


class AssetGroupMember(Base):
    """Many-to-many relationship between assets and groups."""
    
    __tablename__ = "asset_group_members"
    
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Reference to asset"
    )
    
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Reference to asset group"
    )
    
    # Relationships
    asset: Mapped["Asset"] = relationship(
        "Asset",
        back_populates="group_memberships"
    )
    
    group: Mapped["AssetGroup"] = relationship(
        "AssetGroup",
        back_populates="members"
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint(
            "asset_id", "group_id",
            name="uq_asset_group_members_asset_group",
            comment="Asset can only be member of a group once"
        ),
        {"comment": "Asset group membership relationships"}
    )