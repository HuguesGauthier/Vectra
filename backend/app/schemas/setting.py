"""
Setting Schemas - Pydantic definitions for API request/response.
"""

from datetime import datetime
from typing import Optional, Set

from pydantic import ConfigDict, field_validator
from sqlmodel import Field, SQLModel

# Constants
MAX_KEY_LENGTH = 100
MAX_VALUE_LENGTH = 5000
MAX_GROUP_LENGTH = 50
MAX_DESCRIPTION_LENGTH = 500

ALLOWED_SETTING_GROUPS = {"general", "ai", "system", "auth", "storage", "notification"}


class SettingBase(SQLModel):
    """
    Base properties for Setting.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    key: str = Field(min_length=1, max_length=MAX_KEY_LENGTH)
    value: str = Field(max_length=MAX_VALUE_LENGTH)
    group: str = Field(max_length=MAX_GROUP_LENGTH)
    is_secret: bool = Field(default=False)
    description: Optional[str] = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)

    @field_validator("group")
    @classmethod
    def validate_group(cls, v: str) -> str:
        if v not in ALLOWED_SETTING_GROUPS:
            raise ValueError(f"Invalid group '{v}'. Allowed: {sorted(ALLOWED_SETTING_GROUPS)}")
        return v


class SettingCreate(SettingBase):
    """Schema for Creation."""

    pass


class SettingUpdate(SQLModel):
    """Schema for Partial Updates."""

    key: str = Field(min_length=1, max_length=MAX_KEY_LENGTH)
    value: Optional[str] = Field(None, max_length=MAX_VALUE_LENGTH)
    group: Optional[str] = Field(None, max_length=MAX_GROUP_LENGTH)
    is_secret: Optional[bool] = Field(None)
    description: Optional[str] = Field(None, max_length=MAX_DESCRIPTION_LENGTH)

    @field_validator("group")
    @classmethod
    def validate_group(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ALLOWED_SETTING_GROUPS:
            raise ValueError(f"Invalid group '{v}'. Allowed: {sorted(ALLOWED_SETTING_GROUPS)}")
        return v


class SettingResponse(SettingBase):
    """Schema for Response."""

    updated_at: Optional[datetime] = None
