"""
Dashboard Statistics Schemas.

Defines the data structures for real-time dashboard metrics.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ConnectStats(BaseModel):
    """Statistics for the Connect pipeline (connectors)."""

    model_config = ConfigDict(from_attributes=True)

    active_pipelines: int = Field(default=0, ge=0, description="Number of connectors currently running or syncing")
    total_connectors: int = Field(default=0, ge=0, description="Total number of connectors")
    system_status: Literal["ok", "error"] = Field(
        default="ok", description="Overall system health based on error presence"
    )
    storage_status: Literal["online", "offline"] = Field(
        default="online", description="Health status of the data storage mount"
    )
    last_sync_time: Optional[datetime] = Field(default=None, description="Most recent connector sync timestamp")


class VectorizeStats(BaseModel):
    """Statistics for the Vectorize pipeline (document indexing)."""

    model_config = ConfigDict(from_attributes=True)

    total_vectors: int = Field(default=0, ge=0, description="Total number of vector points indexed")
    total_tokens: int = Field(default=0, ge=0, description="Total number of tokens processed")
    indexing_success_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Success rate of document indexing (0.0 - 1.0)"
    )
    failed_docs_count: int = Field(default=0, ge=0, description="Number of failed documents")


class ChatStats(BaseModel):
    """Statistics for the Chat pipeline (usage analytics)."""

    model_config = ConfigDict(from_attributes=True)

    monthly_sessions: int = Field(default=0, ge=0, description="Number of unique sessions in the last 30 days")
    avg_latency_ttft: float = Field(default=0.0, ge=0.0, description="Average time to first token in seconds")
    total_tokens_used: int = Field(default=0, ge=0, description="Total tokens (input + output) used")


class DashboardStats(BaseModel):
    """Aggregated dashboard statistics for all pipelines."""

    model_config = ConfigDict(from_attributes=True)

    connect: ConnectStats = Field(default_factory=ConnectStats, description="Connect pipeline statistics")
    vectorize: VectorizeStats = Field(default_factory=VectorizeStats, description="Vectorize pipeline statistics")
    chat: ChatStats = Field(default_factory=ChatStats, description="Chat pipeline statistics")
