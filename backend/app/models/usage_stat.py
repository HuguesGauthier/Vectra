"""
Usage statistics model for assistant analytics.

ARCHITECT NOTE: Analytics & Observability Pattern
Tracks assistant usage for performance, cost, and quality metrics.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlalchemy import (Column, DateTime, Float, ForeignKey, Index, Integer,
                        func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

from app.models.assistant import Assistant

# Validation constants
MAX_SESSION_ID_LENGTH = 100
MAX_MODEL_NAME_LENGTH = 100


class UsageStatBase(SQLModel):
    """Base properties for UsageStat."""

    assistant_id: UUID = Field(
        sa_column=Column(ForeignKey("assistants.id", ondelete="CASCADE"), nullable=False, index=True),
        description="Assistant being used",
    )

    session_id: str = Field(
        index=True, nullable=False, max_length=MAX_SESSION_ID_LENGTH, description="User session identifier"
    )

    user_id: Optional[UUID] = Field(default=None, index=True, description="User ID (optional for anonymous)")

    # Performance
    total_duration: float = Field(default=0.0, ge=0.0, description="Total duration in seconds")

    ttft: Optional[float] = Field(default=None, ge=0.0, description="Time to first token")

    step_duration_breakdown: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB), description="Step timings"
    )

    step_token_breakdown: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSONB), description="Token usage breakdown by pipeline step"
    )

    # Cost
    input_tokens: int = Field(default=0, ge=0, description="Input tokens")

    output_tokens: int = Field(default=0, ge=0, description="Output tokens")

    model: str = Field(nullable=False, max_length=MAX_MODEL_NAME_LENGTH, description="LLM model used")


class UsageStat(UsageStatBase, table=True):
    """
    Database model for tracking Assistant usage.

    Query Patterns:
    - Usage trends: GROUP BY DATE(timestamp), assistant_id
    - Cost tracking: SUM(input_tokens + output_tokens)
    - Satisfaction: AVG(feedback_score)
    """

    __tablename__ = "usage_stats"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    timestamp: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True))

    assistant: Optional[Assistant] = Relationship()

    __table_args__ = (
        Index("ix_usage_stats_assistant_timestamp", "assistant_id", "timestamp"),
        Index("ix_usage_stats_session", "session_id", "timestamp"),
        Index("ix_usage_stats_user_timestamp", "user_id", "timestamp"),
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class UsageStatCreate(SQLModel):
    """Schema for creating usage stat."""

    assistant_id: UUID
    session_id: str = Field(min_length=1, max_length=MAX_SESSION_ID_LENGTH)
    user_id: Optional[UUID] = None
    total_duration: float = Field(default=0.0, ge=0.0)
    ttft: Optional[float] = Field(None, ge=0.0)
    step_duration_breakdown: Optional[Dict[str, Any]] = None
    step_token_breakdown: Optional[Dict[str, Any]] = None
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    model: str = Field(max_length=MAX_MODEL_NAME_LENGTH)


class UsageStatUpdate(SQLModel):
    """Schema for updating usage stat."""

    total_duration: Optional[float] = None
    ttft: Optional[float] = None
    step_duration_breakdown: Optional[Dict[str, Any]] = None
    step_token_breakdown: Optional[Dict[str, Any]] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    model: Optional[str] = None


class UsageStatResponse(UsageStatBase):
    """Schema for usage stat response."""

    id: UUID
    timestamp: datetime
