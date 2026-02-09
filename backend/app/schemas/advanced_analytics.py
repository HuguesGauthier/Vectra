"""
Advanced Analytics Schemas for KPI Dashboard.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# Performance KPIs
class TTFTPercentiles(BaseModel):
    """Time-to-First-Token percentiles."""

    p50: float = Field(description="Median TTFT in seconds")
    p95: float = Field(description="95th percentile TTFT")
    p99: float = Field(description="99th percentile TTFT")
    period_hours: int = Field(description="Time period analyzed")


class StepBreakdown(BaseModel):
    """Average duration breakdown by pipeline step."""

    step_name: str
    avg_duration: float
    step_count: int
    avg_tokens: Optional[Dict[str, float]] = None  # keys: input, output


class CacheMetrics(BaseModel):
    """Semantic cache performance."""

    hit_rate: float = Field(description="Cache hit rate percentage")
    total_requests: int
    cache_hits: int
    cache_misses: int
    period_hours: int


# User Satisfaction KPIs
class SessionDistribution(BaseModel):
    """Distribution of questions per session."""

    session_type: str  # "Single Question", "Normal (2-5)", "Power User (5+)"
    session_count: int
    percentage: float


class TrendingTopic(BaseModel):
    """Popular question/topic."""

    canonical_text: str
    frequency: int
    variation_count: int
    last_asked: datetime


class TopicDiversity(BaseModel):
    """Topic diversity score (Herfindahl Index)."""

    diversity_score: float = Field(ge=0.0, le=1.0, description="0=no diversity, 1=perfect diversity")
    total_topics: int
    dominant_topic_share: float


# Cost & ROI KPIs
class AssistantCost(BaseModel):
    """Token cost per assistant."""

    assistant_id: str
    assistant_name: str
    total_tokens: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


class DocumentUtilization(BaseModel):
    """Knowledge base document usage."""

    file_name: str
    connector_name: str
    retrieval_count: int
    last_retrieved: Optional[datetime]
    status: str  # "hot", "warm", "cold"


# User Stats
class UserStat(BaseModel):
    """User usage statistics."""

    user_id: str
    email: str
    full_name: str
    total_tokens: int
    interaction_count: int
    last_active: Optional[datetime]


# Knowledge Base Health KPIs
class DocumentFreshness(BaseModel):
    """Document age distribution."""

    freshness_category: str  # "Fresh (<30d)", "Aging (30-90d)", "Stale (>90d)"
    doc_count: int
    percentage: float


class RerankingImpact(BaseModel):
    """Reranking effectiveness metrics."""

    avg_score_improvement: float
    reranking_enabled_count: int
    avg_position_change: Optional[float]


class ConnectorSyncRate(BaseModel):
    """Connector synchronization success metrics."""

    connector_id: str
    connector_name: str
    success_rate: float = Field(ge=0.0, le=100.0, description="Success rate percentage")
    total_syncs: int
    successful_syncs: int
    failed_syncs: int
    avg_sync_duration: Optional[float]


# Aggregate Response
class AdvancedAnalyticsResponse(BaseModel):
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

    generated_at: datetime = Field(default_factory=datetime.utcnow)
