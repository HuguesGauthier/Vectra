from typing import Optional
from uuid import UUID, uuid4

from pydantic import ConfigDict, EmailStr
from sqlalchemy import Column, Enum
from sqlmodel import Field, SQLModel

from app.models.enums import UserRole

# Constants
MAX_EMAIL_LENGTH = 255
MAX_ROLE_LENGTH = 50


class UserBase(SQLModel):
    """
    Base properties for User.
    Shared between Model and Schemas.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True, from_attributes=True)

    email: EmailStr = Field(index=True, unique=True, max_length=MAX_EMAIL_LENGTH, description="User email address")
    role: UserRole = Field(default=UserRole.USER, max_length=MAX_ROLE_LENGTH, description="User role (admin/user)")
    is_active: bool = Field(default=True, description="Active status")
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500, description="Profile picture URL")
    avatar_vertical_position: int = Field(default=50, ge=0, le=100, description="Avatar vertical position (0-100)")


class User(UserBase, table=True):
    """
    Database model for Users.

    ARCHITECT NOTE:
    - validate_assignment=True ensures Pydantic validation runs during updates.
    """

    __tablename__ = "users"
    model_config = {"validate_assignment": True, "arbitrary_types_allowed": True}

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str = Field(nullable=False)

    # Explicit Enum column mapping for SQLAlchemy
    role: UserRole = Field(
        default=UserRole.USER,
        sa_column=Column(
            Enum(UserRole, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False
        ),
    )
