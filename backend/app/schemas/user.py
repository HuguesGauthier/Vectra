"""
User Schemas - Pydantic definitions for API request/response.
"""

from typing import List, Optional
from uuid import UUID

from pydantic import EmailStr, Field
from sqlmodel import SQLModel

from app.models.enums import UserRole
from app.models.user import MAX_EMAIL_LENGTH, MAX_ROLE_LENGTH, UserBase


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
    job_titles: Optional[List[str]] = Field(default_factory=list)
    avatar_url: Optional[str] = Field(None, max_length=500)
    avatar_vertical_position: Optional[int] = Field(None, ge=0, le=100)


class UserRead(UserBase):
    """Schema for Response."""

    id: UUID
