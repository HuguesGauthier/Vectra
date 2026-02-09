"""
User Database Model.
"""

from uuid import UUID, uuid4

# Note: Import UserRole for SA column definition if needed, but SQLModel handles Enum fields well now
# provided the type in Base is correct.
from sqlalchemy import Column, Enum
from sqlmodel import Field

from app.schemas.enums import UserRole
from app.schemas.user import MAX_EMAIL_LENGTH, MAX_ROLE_LENGTH, UserBase


class User(UserBase, table=True):
    """
    Database model for Users.
    Inherits schema/validation from UserBase in schemas/.
    """

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    hashed_password: str = Field(nullable=False)

    # Explicit Enum column mapping for SQLAlchemy
    role: UserRole = Field(
        default=UserRole.USER,
        sa_column=Column(
            Enum(UserRole, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False
        ),
    )

    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    avatar_url: str | None = Field(default=None, max_length=500)
    avatar_vertical_position: int = Field(default=50, ge=0, le=100)
