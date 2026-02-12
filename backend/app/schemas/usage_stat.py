"""
UsageStat Schemas - Pydantic definitions for API request/response.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlmodel import Field, SQLModel
from app.models.usage_stat import MAX_MODEL_NAME_LENGTH, MAX_SESSION_ID_LENGTH, UsageStatBase


class UsageStatCreate(UsageStatBase):
    """Schema for creating usage stat."""

    session_id: str = Field(min_length=1, max_length=MAX_SESSION_ID_LENGTH)


class UsageStatUpdate(SQLModel):
    """Schema for updating usage stat."""

    total_duration: Optional[float] = Field(None, ge=0.0)
    ttft: Optional[float] = Field(None, ge=0.0)
    step_duration_breakdown: Optional[Dict[str, Any]] = None
    step_token_breakdown: Optional[Dict[str, Any]] = None
    input_tokens: Optional[int] = Field(None, ge=0)
    output_tokens: Optional[int] = Field(None, ge=0)
    model: Optional[str] = Field(None, max_length=MAX_MODEL_NAME_LENGTH)


class UsageStatResponse(UsageStatBase):
    """Schema for usage stat response."""

    id: UUID
    timestamp: datetime
