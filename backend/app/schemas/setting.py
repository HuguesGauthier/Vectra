"""
Setting Schemas - Pydantic definitions for API request/response.
"""

from datetime import datetime
from typing import Optional, Set

from pydantic import ConfigDict, field_validator
from sqlmodel import Field, SQLModel

from app.models.enums import SettingGroup

# Constants
MAX_KEY_LENGTH = 100
MAX_VALUE_LENGTH = 5000
MAX_GROUP_LENGTH = 50
MAX_DESCRIPTION_LENGTH = 500

ALLOWED_SETTING_GROUPS = [t.value for t in SettingGroup]


class SettingBase(SQLModel):
    """
    Base properties for Setting.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    key: str = Field(min_length=1, max_length=MAX_KEY_LENGTH)
    value: str = Field(max_length=MAX_VALUE_LENGTH)
    group: SettingGroup = Field(description="Setting category")
    is_secret: bool = Field(default=False)
    description: Optional[str] = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)


class SettingCreate(SettingBase):
    """Schema for Creation."""

    pass


class SettingUpdate(SQLModel):
    """Schema for Partial Updates."""

    key: str = Field(min_length=1, max_length=MAX_KEY_LENGTH)
    value: Optional[str] = Field(None, max_length=MAX_VALUE_LENGTH)
    group: Optional[SettingGroup] = Field(None, description="Setting category")
    is_secret: Optional[bool] = Field(None)
    description: Optional[str] = Field(None, max_length=MAX_DESCRIPTION_LENGTH)


class SettingResponse(SettingBase):
    """Schema for Response."""

    updated_at: Optional[datetime] = None
