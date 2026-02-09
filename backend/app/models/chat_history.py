"""
Chat History Database Model.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import (CheckConstraint, Column, DateTime, ForeignKey, String,
                        Text, func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ChatHistory(SQLModel, table=True):
    """
    Database model for persistent Chat History (Audit Log).
    Replaces the legacy `data_chat_history` table.
    """

    __tablename__ = "chat_history"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    session_id: str = Field(index=True, nullable=False, max_length=100)

    user_id: Optional[str] = Field(
        default=None, index=True, nullable=True, max_length=100, description="ID of the user who initiated the chat"
    )

    role: str = Field(sa_column=Column(String(20), nullable=False))

    content: str = Field(sa_column=Column(Text, nullable=False))

    assistant_id: UUID = Field(
        sa_column=Column(ForeignKey("assistants.id", ondelete="CASCADE"), nullable=True, index=True),
        description="Assistant context for this message",
    )

    # Metadata like tokens, feedback, sources used, etc.
    metadata_: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column("metadata", JSONB, nullable=True))

    created_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True)
    )

    # Constraints
    __table_args__ = (CheckConstraint("role IN ('user', 'assistant', 'system')", name="valid_role_check"),)
