"""
Setting Database Model.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Text, func
from sqlmodel import Field, SQLModel

from app.schemas.setting import (MAX_GROUP_LENGTH, MAX_KEY_LENGTH,
                                 MAX_VALUE_LENGTH, SettingBase)


class Setting(SettingBase, table=True):
    """
    Database model for Settings.
    Inherits schema/validation from SettingBase in schemas/.
    """

    __tablename__ = "settings"

    key: str = Field(primary_key=True, index=True, max_length=MAX_KEY_LENGTH)

    value: str = Field(sa_column=Column(Text, nullable=False), max_length=MAX_VALUE_LENGTH)

    group: str = Field(index=True, max_length=MAX_GROUP_LENGTH)

    updated_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )
