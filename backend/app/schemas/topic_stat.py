"""
TopicStat Schemas - Pydantic definitions for API request/response.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import ConfigDict
from sqlmodel import Field, SQLModel
from app.models.topic_stat import MAX_CANONICAL_TEXT_LENGTH, MIN_FREQUENCY, TopicStatBase


class TopicStatCreate(TopicStatBase):
    """Schema for creation."""

    pass


class TopicStatUpdate(SQLModel):
    """Schema for partial updates."""

    frequency: Optional[int] = Field(None, ge=MIN_FREQUENCY)
    raw_variations: Optional[List[str]] = None


class TopicStatResponse(TopicStatBase):
    """Schema for response."""

    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
