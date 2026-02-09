"""
Connector Sync Log Model.
Tracks connector synchronization attempts for analytics.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Text, func
from sqlmodel import Field, SQLModel


class ConnectorSyncLog(SQLModel, table=True):
    """
    Database model for tracking connector sync operations.
    Used for analytics: sync success rate, reliability metrics.
    """

    __tablename__ = "connector_sync_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    connector_id: UUID = Field(
        sa_column=Column(ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False, index=True)
    )

    status: str = Field(max_length=20, description="Sync status: 'success', 'failure', 'partial'")

    documents_synced: int = Field(default=0, ge=0, description="Number of documents successfully synced")

    error_message: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True), description="Error details if sync failed"
    )

    sync_duration: Optional[float] = Field(default=None, ge=0.0, description="Sync duration in seconds")

    sync_time: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now(), index=True))

    __table_args__ = (
        Index("ix_connector_sync_logs_connector_time", "connector_id", "sync_time"),
        Index("ix_connector_sync_logs_status_time", "status", "sync_time"),
    )
