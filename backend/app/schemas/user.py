"""
User Schemas - Pydantic definitions for API request/response.
"""

from typing import Optional
from uuid import UUID

from pydantic import ConfigDict, EmailStr, Field
from sqlmodel import SQLModel

from app.schemas.enums import UserRole

# Constants
MAX_EMAIL_LENGTH = 255
MAX_ROLE_LENGTH = 50


class UserBase(SQLModel):
    """
    Base properties for User.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    email: EmailStr = Field(index=True, unique=True, max_length=MAX_EMAIL_LENGTH, description="User email address")
    role: UserRole = Field(default=UserRole.USER, max_length=MAX_ROLE_LENGTH, description="User role (admin/user)")
    is_active: bool = Field(default=True, description="Active status")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500, description="Profile picture URL")
    avatar_vertical_position: int = Field(default=50, ge=0, le=100, description="Avatar vertical position (0-100)")


class UserCreate(UserBase):
    """Schema for Creation."""

    password: str = Field(min_length=8, description="Password (min 8 chars)")


class UserUpdate(SQLModel):
    """Schema for Partial Updates."""

    email: Optional[EmailStr] = Field(None, max_length=MAX_EMAIL_LENGTH)
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    avatar_vertical_position: Optional[int] = Field(None, ge=0, le=100)


class UserRead(UserBase):
    """Schema for Response."""

    id: UUID
