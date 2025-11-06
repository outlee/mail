import uuid
from datetime import datetime
from typing import Any, Dict, List

from pydantic import Field, EmailStr, field_validator

from app.models.auth import UserStatus
from .base import BaseSchema, TimestampedSchema, SoftDeleteSchema


class RoleBase(BaseSchema):
    """Base role schema with common fields."""
    
    name: str = Field(..., max_length=100, description="Unique role name")
    display_name: str = Field(..., max_length=255, description="Human-readable role display name")
    description: str | None = Field(None, description="Role description and responsibilities")
    is_system_role: bool = Field(default=False, description="Indicates if this is a system-defined role")
    is_active: bool = Field(default=True, description="Whether the role is currently active")
    permissions: Dict[str, List[str]] | None = Field(None, description="Role permissions and access rights")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional role metadata")


class RoleCreate(RoleBase):
    """Schema for creating a new role."""
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Role name cannot be empty')
        return v.strip().lower()
    
    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Display name cannot be empty')
        return v.strip()


class RoleUpdate(BaseSchema):
    """Schema for updating an existing role."""
    
    display_name: str | None = Field(None, max_length=255, description="Human-readable role display name")
    description: str | None = Field(None, description="Role description and responsibilities")
    is_active: bool | None = Field(None, description="Whether the role is currently active")
    permissions: Dict[str, List[str]] | None = Field(None, description="Role permissions and access rights")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional role metadata")


class RoleRead(TimestampedSchema, RoleBase):
    """Schema for reading role data."""
    
    pass


class UserBase(BaseSchema):
    """Base user schema with common fields."""
    
    username: str = Field(..., max_length=100, description="Unique username for login")
    email: EmailStr = Field(..., description="Unique email address")
    first_name: str = Field(..., max_length=100, description="User's first name")
    last_name: str = Field(..., max_length=100, description="User's last name")
    status: UserStatus = Field(default=UserStatus.PENDING, description="Account status")
    tenant_id: uuid.UUID | None = Field(None, description="Tenant identifier for multi-tenancy")
    phone: str | None = Field(None, max_length=50, description="Phone number")
    department: str | None = Field(None, max_length=100, description="Department or organization unit")
    job_title: str | None = Field(None, max_length=100, description="Job title or position")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional user metadata")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    
    password: str = Field(..., min_length=8, max_length=255, description="User password")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError('Username cannot be empty')
        if len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters long')
        return v.strip().lower()
    
    @field_validator('first_name')
    @classmethod
    def validate_first_name(cls, v):
        if not v or not v.strip():
            raise ValueError('First name cannot be empty')
        return v.strip()
    
    @field_validator('last_name')
    @classmethod
    def validate_last_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Last name cannot be empty')
        return v.strip()


class UserUpdate(BaseSchema):
    """Schema for updating an existing user."""
    
    username: str | None = Field(None, max_length=100, description="Unique username for login")
    email: EmailStr | None = Field(None, description="Unique email address")
    first_name: str | None = Field(None, max_length=100, description="User's first name")
    last_name: str | None = Field(None, max_length=100, description="User's last name")
    status: UserStatus | None = Field(None, description="Account status")
    tenant_id: uuid.UUID | None = Field(None, description="Tenant identifier for multi-tenancy")
    phone: str | None = Field(None, max_length=50, description="Phone number")
    department: str | None = Field(None, max_length=100, description="Department or organization unit")
    job_title: str | None = Field(None, max_length=100, description="Job title or position")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional user metadata")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if v is not None:
            if not v.strip():
                raise ValueError('Username cannot be empty')
            if len(v.strip()) < 3:
                raise ValueError('Username must be at least 3 characters long')
            return v.strip().lower()
        return v


class UserRead(TimestampedSchema, SoftDeleteSchema, UserBase):
    """Schema for reading user data."""
    
    is_email_verified: bool = Field(default=False, description="Whether user's email has been verified")


class UserRoleBase(BaseSchema):
    """Base user role assignment schema with common fields."""
    
    user_id: uuid.UUID = Field(..., description="Reference to the user")
    role_id: uuid.UUID = Field(..., description="Reference to the role")
    assigned_by: uuid.UUID | None = Field(None, description="User who made this assignment")
    expires_at: datetime | None = Field(None, description="When this role assignment expires")
    meta_data: Dict[str, Any] | None = Field(None, description="Additional assignment metadata")


class UserRoleCreate(UserRoleBase):
    """Schema for creating a new user role assignment."""
    
    pass