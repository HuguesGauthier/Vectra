"""
Topic statistics model for trending questions tracking.

ARCHITECT NOTE: Vector-Database Synchronization
This model stores metadata about frequently asked questions alongside Qdrant vectors.
The TopicStat.id MUST match the Qdrant Point ID for consistency.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from pydantic import ConfigDict
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .assistant import Assistant

# Validation constants
MAX_CANONICAL_TEXT_LENGTH = 500
MAX_RAW_VARIATIONS_COUNT = 100
MIN_FREQUENCY = 1


class TopicStatBase(SQLModel):
    """
    Base properties for TopicStat models.

    ARCHITECT NOTE: Semantic Clustering Pattern
    - canonical_text: Normalized/representative question
    - frequency: Usage count for trending analysis
    - raw_variations: Original user queries
    - assistant_id: Scope to specific assistant
    """

    canonical_text: str = Field(
        sa_column=Column(Text, nullable=False),
        max_length=MAX_CANONICAL_TEXT_LENGTH,
        description="Normalized representative question",
    )

    frequency: int = Field(
        default=1,
        ge=MIN_FREQUENCY,
        sa_column=Column(Integer, server_default="1", nullable=False),
        description="Number of times this topic was asked",
    )

    raw_variations: List[str] = Field(
        default_factory=list, sa_column=Column(JSONB, default=[]), description="Original user question variations"
    )

    assistant_id: UUID = Field(
        sa_column=Column(ForeignKey("assistants.id", ondelete="CASCADE"), nullable=False, index=True),
        description="Assistant this topic belongs to",
    )


class TopicStat(TopicStatBase, table=True):
    """
    Database model for Trending Topics Statistics.

    ARCHITECT NOTE: Qdrant Synchronization
    The `id` field MUST be synchronized with the corresponding Qdrant Point ID.
    When creating/deleting TopicStat records, ensure corresponding Qdrant
    operations are performed atomically.

    Query Patterns:
    - Trending by assistant: WHERE assistant_id = ? ORDER BY frequency DESC
    - Recent topics: ORDER BY created_at DESC LIMIT 10
    """

    __tablename__ = "topic_stats"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    created_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )

    updated_at: Optional[datetime] = Field(default=None, sa_column=Column(DateTime(timezone=True), onupdate=func.now()))

    assistant: Optional["Assistant"] = Relationship(sa_relationship_kwargs={"lazy": "selectin"})

    __table_args__ = (
        Index("ix_topic_stats_assistant_frequency", "assistant_id", "frequency"),
        Index("ix_topic_stats_assistant_created", "assistant_id", "created_at"),
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TopicStatCreate(SQLModel):
    """Schema for creating a new topic stat."""

    canonical_text: str = Field(min_length=1, max_length=MAX_CANONICAL_TEXT_LENGTH)
    frequency: int = Field(default=1, ge=MIN_FREQUENCY)
    raw_variations: List[str] = Field(default_factory=list)
    assistant_id: UUID


class TopicStatUpdate(SQLModel):
    """Schema for updating a topic stat."""

    frequency: Optional[int] = Field(None, ge=MIN_FREQUENCY)
    raw_variations: Optional[List[str]] = None


class TopicStatResponse(TopicStatBase):
    """Schema for topic stat response."""

    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
