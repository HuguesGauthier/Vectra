"""
Advanced Analytics Schemas for KPI Dashboard.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnalyticsBaseModel(BaseModel):
    """Base model for analytics with attributes support."""

    model_config = ConfigDict(from_attributes=True)


# Performance KPIs
class TTFTPercentiles(AnalyticsBaseModel):
    """Time-to-First-Token percentiles."""

    p50: float = Field(description="Median TTFT in seconds")
    p95: float = Field(description="95th percentile TTFT")
    p99: float = Field(description="99th percentile TTFT")
    period_hours: int = Field(description="Time period analyzed")


class StepBreakdown(AnalyticsBaseModel):
    """Average duration breakdown by pipeline step."""

    step_name: str
    avg_duration: float
    step_count: int
    avg_tokens: Optional[Dict[str, float]] = None  # keys: input, output


class CacheMetrics(AnalyticsBaseModel):
    """Semantic cache performance."""

    hit_rate: float = Field(description="Cache hit rate percentage")
    total_requests: int
    cache_hits: int
    cache_misses: int
    period_hours: int


# User Satisfaction KPIs
class SessionDistribution(AnalyticsBaseModel):
    """Distribution of questions per session."""

    session_type: str  # "Single Question", "Normal (2-5)", "Power User (5+)"
    session_count: int
    percentage: float


class TrendingTopic(AnalyticsBaseModel):
    """Popular question/topic."""

    topic: str
    canonical_text: str
    frequency: int
    variation_count: int
    last_asked: datetime


class TopicDiversity(AnalyticsBaseModel):
    """Topic diversity score (Herfindahl Index)."""

    diversity_score: float = Field(ge=0.0, le=1.0, description="0=no diversity, 1=perfect diversity")
    total_topics: int
    dominant_topic_share: float


# Cost & ROI KPIs
class AssistantCost(AnalyticsBaseModel):
    """Token cost per assistant."""

    assistant_id: UUID
    assistant_name: str
    total_tokens: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


class DocumentUtilization(AnalyticsBaseModel):
    """Knowledge base document usage."""

    file_name: str
    connector_name: str
    retrieval_count: int
    last_retrieved: Optional[datetime] = None
    status: str  # "hot", "warm", "cold"


# User Stats
class UserStat(AnalyticsBaseModel):
    """User usage statistics."""

    user_id: UUID
    email: str
    full_name: str
    total_tokens: int
    interaction_count: int
    last_active: Optional[datetime] = None


# Knowledge Base Health KPIs
class DocumentFreshness(AnalyticsBaseModel):
    """Document age distribution."""

    freshness_category: str  # "Fresh (<30d)", "Aging (30-90d)", "Stale (>90d)"
    doc_count: int
    percentage: float


class RerankingImpact(AnalyticsBaseModel):
    """Reranking effectiveness metrics."""

    avg_score_improvement: float
    reranking_enabled_count: int
    avg_position_change: Optional[float] = None


class ConnectorSyncRate(AnalyticsBaseModel):
    """Connector synchronization success metrics."""

    connector_id: UUID
    connector_name: str
    success_rate: float = Field(ge=0.0, le=100.0, description="Success rate percentage")
    total_syncs: int
    successful_syncs: int
    failed_syncs: int
    avg_sync_duration: Optional[float] = None


# Aggregate Response
class AdvancedAnalyticsResponse(AnalyticsBaseModel):
    """Complete advanced analytics dashboard data."""

    # Performance
    ttft_percentiles: Optional[TTFTPercentiles] = None
    step_breakdown: List[StepBreakdown] = []
    cache_metrics: Optional[CacheMetrics] = None

    # User Satisfaction
    session_distribution: List[SessionDistribution] = []
    trending_topics: List[TrendingTopic] = []
    topic_diversity: Optional[TopicDiversity] = None

    # Cost & ROI
    assistant_costs: List[AssistantCost] = []
    document_utilization: List[DocumentUtilization] = []

    # User Stats
    user_stats: List[UserStat] = []

    # KB Health
    document_freshness: List[DocumentFreshness] = []
    reranking_impact: Optional[RerankingImpact] = None
    connector_sync_rates: List[ConnectorSyncRate] = []

    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
