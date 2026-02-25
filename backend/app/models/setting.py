"""
Setting Database Model.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Enum, Text, func
from sqlmodel import Field, SQLModel

from app.models.enums import SettingGroup

# Storage Constants (Source of truth for DB limits)
MAX_KEY_LENGTH = 100
MAX_VALUE_LENGTH = 5000
MAX_GROUP_LENGTH = 50
MAX_DESCRIPTION_LENGTH = 500


class Setting(SQLModel, table=True):
    """
    Database model for Settings.

    ARCHITECT NOTE:
    We use validate_assignment=True to ensure Pydantic constraints
    are enforced during model instantiation and updates.
    """

    __tablename__ = "settings"
    model_config = {"validate_assignment": True}

    key: str = Field(primary_key=True, index=True, max_length=MAX_KEY_LENGTH)

    value: str = Field(sa_column=Column(Text, nullable=False), max_length=MAX_VALUE_LENGTH)

    group: SettingGroup = Field(
        sa_column=Column(
            Enum(SettingGroup, native_enum=False, values_callable=lambda x: [e.value for e in x]),
            index=True,
            nullable=False,
        ),
        max_length=MAX_GROUP_LENGTH,
    )

    is_secret: bool = Field(default=False)

    description: Optional[str] = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)

    updated_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )
