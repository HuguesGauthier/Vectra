"""Analytics Service.

Consolidated service for all analytics (Business Intelligence & Advanced KPIs).
This service provides methods to aggregate and transform data from various repositories
into unified analytics reports.
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import (
    Annotated,
    Any,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
)
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_session_factory
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.advanced_analytics import (
    AdvancedAnalyticsResponse,
    AssistantCost,
    CacheMetrics,
    ConnectorSyncRate,
    DocumentFreshness,
    DocumentUtilization,
    RerankingImpact,
    SessionDistribution,
    StepBreakdown,
    TopicDiversity,
    TrendingTopic,
    TTFTPercentiles,
    UserStat,
)
from app.schemas.analytics import AnalyticsResponse
from app.services.settings_service import SettingsService, get_settings_service

logger = logging.getLogger(__name__)

# --- Type Aliases & Constants ---
T = TypeVar("T")
TimeProvider = Callable[[], datetime]

# Default values for settings-based metrics
DEFAULT_COST_PER_1K_TOKENS: float = 0.0001
DEFAULT_MIN_SAVED_PER_DOC: float = 5.0
DEFAULT_TRENDING_LIMIT: int = 10
DEFAULT_USER_STATS_DAYS: int = 30

# Fallback costs (USD)
FALLBACK_INPUT_TOKEN_COST: float = 0.00001
FALLBACK_OUTPUT_TOKEN_COST: float = 0.00003

# Resiliency constants
ANALYTICS_TASK_TIMEOUT: int = 30  # seconds


@dataclass(frozen=True)
class AnalyticsTask:
    """Configuration for an advanced analytics task.

    Attributes:
        key: The key identifying the task in the results dictionary.
        coro_func: The coroutine function to execute.
        args: Positional arguments to pass to the coroutine.
        default: Default value to return if the task fails or times out.
    """

    key: str
    coro_func: Callable[..., Coroutine[Any, Any, Any]]
    args: Tuple[Any, ...] = ()
    default: Any = None


class AnalyticsService:
    """Unified Analytics Service.

    Responsibilities:
        1. Metric Aggregation (Parallelized).
        2. Data Transformation (DB Rows -> Pydantic Models).
        3. Configuration Management.

    Attributes:
        session_factory: Factory for creating AsyncSession instances.
        settings_service: Service for retrieving application settings.
        time_provider: Function that returns current time (for testability).
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings_service: SettingsService,
        time_provider: TimeProvider = lambda: datetime.now(timezone.utc),
    ) -> None:
        """Initialize AnalyticsService.

        Args:
            session_factory: Factory to create new AsyncSession instances for parallel tasks.
            settings_service: The settings service instance.
            time_provider: Function providing the current datetime.
        """
        self.session_factory = session_factory
        self.settings_service = settings_service
        self.time_provider = time_provider

    # --- Public API ---

    async def get_business_metrics(self) -> AnalyticsResponse:
        """Aggregates simple business metrics with error handling.

        Calculates total documents, vectors, tokens, estimated cost, and hours saved.

        Returns:
            AnalyticsResponse: The aggregated business metrics.
        """
        try:
            # Start fetching settings and docs concurrently
            settings_task = self._fetch_business_settings()

            async with self.session_factory() as session:
                document_repo = DocumentRepository(session)
                stats = await document_repo.get_aggregate_stats()

            cost_per_1k, min_saved = await settings_task

            return self._calculate_business_metrics(stats, cost_per_1k, min_saved)

        except Exception as e:
            logger.error("DEGRADED_STATE | Failed to calculate business metrics: %s", str(e), exc_info=True)
            # Return empty but log as degraded state for observability
            return AnalyticsResponse()

    async def get_all_advanced_analytics(
        self,
        ttft_hours: int = 24,
        step_days: int = 7,
        cache_hours: int = 24,
        cost_hours: int = 24,
        trending_limit: int = DEFAULT_TRENDING_LIMIT,
        assistant_id: Optional[UUID] = None,
    ) -> AdvancedAnalyticsResponse:
        """Generate a complete advanced analytics report.

        Runs multiple specialized metric queries concurrently with a timeout.

        Args:
            ttft_hours: Look-back window for TTFT percentiles.
            step_days: Look-back window for step breakdown.
            cache_hours: Look-back window for cache metrics.
            cost_hours: Look-back window for assistant costs.
            trending_limit: Max number of topics to return.
            assistant_id: Optional UUID to filter metrics to a specific assistant.

        Returns:
            AdvancedAnalyticsResponse: The complete report.
        """
        tasks = self._prepare_analytics_tasks(
            ttft_hours, step_days, cache_hours, cost_hours, trending_limit, assistant_id
        )
        results = await self._run_tasks_concurrently(tasks)
        return AdvancedAnalyticsResponse(**results)

    # --- Individual Metric Methods ---

    async def get_ttft_percentiles(self, hours: int) -> Optional[TTFTPercentiles]:
        """Fetch Time To First Token (TTFT) percentiles.

        Args:
            hours: Look-back window in hours.

        Returns:
            Optional[TTFTPercentiles]: Percentile data or None if unavailable.
        """
        cutoff = self._get_cutoff_time(hours=hours)
        data = await self._execute_repo_task(lambda repo: repo.get_ttft_percentiles(cutoff))

        if not data:
            return None

        return TTFTPercentiles(
            p50=data.get("p50", 0.0),
            p95=data.get("p95", 0.0),
            p99=data.get("p99", 0.0),
            period_hours=hours,
        )

    async def get_step_breakdown(self, days: int) -> List[StepBreakdown]:
        """Fetch pipeline step performance metrics.

        Args:
            days: Look-back window in days.

        Returns:
            List[StepBreakdown]: Per-step performance results.
        """
        cutoff = self._get_cutoff_time(days=days)
        rows = await self._execute_repo_task(lambda repo: repo.get_step_breakdown(cutoff))
        return [self._map_step_row(row) for row in rows]

    async def get_cache_metrics(self, hours: int) -> Optional[CacheMetrics]:
        """Fetch semantic cache effectiveness.

        Args:
            hours: Look-back window in hours.

        Returns:
            Optional[CacheMetrics]: Cache stats or None if no requests recorded.
        """
        cutoff = self._get_cutoff_time(hours=hours)
        row = await self._execute_repo_task(lambda repo: repo.get_cache_stats(cutoff))

        if not row or not getattr(row, "total_requests", 0):
            return None

        return self._calculate_cache_metrics(row, hours)

    async def get_trending_topics(self, assistant_id: Optional[UUID], limit: int) -> List[TrendingTopic]:
        """Fetch high-frequency question topics.

        Args:
            assistant_id: UUID filter.
            limit: Max results.

        Returns:
            List[TrendingTopic]: List of trending topics.
        """
        topics = await self._execute_repo_task(lambda repo: repo.get_trending_topics(limit, assistant_id))
        return [self._map_trending_topic(t) for t in topics]

    async def get_topic_diversity(self, assistant_id: Optional[UUID]) -> Optional[TopicDiversity]:
        """Calculate topic diversity score.

        Args:
            assistant_id: UUID filter.

        Returns:
            Optional[TopicDiversity]: Diversity metrics or None if no topics found.
        """
        rows = await self._execute_repo_task(lambda repo: repo.get_topic_frequencies(assistant_id))
        if not rows:
            return None
        return self._calculate_diversity_metrics(rows)

    async def get_assistant_costs(self, hours: int) -> List[AssistantCost]:
        """Fetch estimated token costs per assistant.

        Args:
            hours: Look-back window in hours.

        Returns:
            List[AssistantCost]: Cost breakdown per assistant.
        """
        cutoff = self._get_cutoff_time(hours=hours)
        rows = await self._execute_repo_task(lambda repo: repo.get_assistant_usage_sums(cutoff))
        return [self._map_cost_row(row) for row in rows]

    async def get_document_freshness(self) -> List[DocumentFreshness]:
        """Calculate document set age distribution.

        Returns:
            List[DocumentFreshness]: Freshness buckets (Fresh, Aging, Stale).
        """
        now = self.time_provider()
        thresh_30 = now - timedelta(days=30)
        thresh_90 = now - timedelta(days=90)

        rows = await self._execute_repo_task(lambda repo: repo.get_document_freshness_stats(thresh_30, thresh_90))
        return self._calculate_freshness_percentages(rows)

    async def get_session_distribution(self, days: int) -> List[SessionDistribution]:
        """Fetch distribution of user session intensity.

        Args:
            days: Look-back window in days.

        Returns:
            List[SessionDistribution]: Distribution across buckets.
        """
        cutoff = self._get_cutoff_time(days=days)
        rows = await self._execute_repo_task(lambda repo: repo.get_session_counts(cutoff))
        return self._calculate_session_distribution(rows)

    async def get_document_utilization(self, days: int) -> List[DocumentUtilization]:
        """Fetch knowledge base utilization metrics.

        Args:
            days: Look-back window in days.

        Returns:
            List[DocumentUtilization]: Usage stats for active documents.
        """
        cutoff = self._get_cutoff_time(days=days)
        rows = await self._execute_repo_task(lambda repo: repo.get_document_retrieval_stats(cutoff))
        return [self._map_utilization_row(row) for row in rows]

    async def get_reranking_impact(self, hours: int) -> Optional[RerankingImpact]:
        """Calculate effectiveness of the reranking pipeline stage.

        Args:
            hours: Look-back window in hours.

        Returns:
            Optional[RerankingImpact]: Impact score or None if no reranking activity.
        """
        cutoff = self._get_cutoff_time(hours=hours)
        row = await self._execute_repo_task(lambda repo: repo.get_reranking_stats(cutoff))

        if row and getattr(row, "reranking_count", 0) > 0:
            return RerankingImpact(
                avg_score_improvement=round(float(getattr(row, "avg_improvement", 0.0) or 0.0), 3),
                reranking_enabled_count=int(getattr(row, "reranking_count", 0)),
                avg_position_change=None,
            )
        return None

    async def get_connector_sync_rates(self, days: int) -> List[ConnectorSyncRate]:
        """Fetch success/failure rates for connector sync jobs.

        Args:
            days: Look-back window in days.

        Returns:
            List[ConnectorSyncRate]: Reliability metrics per connector.
        """
        cutoff = self._get_cutoff_time(days=days)
        rows = await self._execute_repo_task(lambda repo: repo.get_connector_sync_stats(cutoff))
        return [self._map_sync_rate_row(row) for row in rows]

    async def get_user_stats(self, days: int) -> List[UserStat]:
        """Fetch usage statistics per user.

        Args:
            days: Look-back window in days.

        Returns:
            List[UserStat]: Engagement metrics per user.
        """
        cutoff = self._get_cutoff_time(days=days)
        rows = await self._execute_repo_task(lambda repo: repo.get_user_usage_stats(cutoff))
        return [self._map_user_stat_row(row) for row in rows]

    # --- Private Execution Helpers ---

    def _prepare_analytics_tasks(
        self,
        ttft_hours: int,
        step_days: int,
        cache_hours: int,
        cost_hours: int,
        trending_limit: int,
        assistant_id: Optional[UUID],
    ) -> List[AnalyticsTask]:
        """Construct the list of tasks for bulk execution."""
        return [
            AnalyticsTask("ttft_percentiles", self.get_ttft_percentiles, (ttft_hours,)),
            AnalyticsTask("step_breakdown", self.get_step_breakdown, (step_days,), []),
            AnalyticsTask("cache_metrics", self.get_cache_metrics, (cache_hours,)),
            AnalyticsTask("trending_topics", self.get_trending_topics, (assistant_id, trending_limit), []),
            AnalyticsTask("topic_diversity", self.get_topic_diversity, (assistant_id,)),
            AnalyticsTask("assistant_costs", self.get_assistant_costs, (cost_hours,), []),
            AnalyticsTask("document_freshness", self.get_document_freshness, (), []),
            AnalyticsTask("session_distribution", self.get_session_distribution, (step_days,), []),
            AnalyticsTask("document_utilization", self.get_document_utilization, (DEFAULT_USER_STATS_DAYS,), []),
            AnalyticsTask("reranking_impact", self.get_reranking_impact, (cache_hours,)),
            AnalyticsTask("connector_sync_rates", self.get_connector_sync_rates, (step_days,), []),
            AnalyticsTask("user_stats", self.get_user_stats, (DEFAULT_USER_STATS_DAYS,), []),
        ]

    async def _execute_repo_task(self, task_func: Callable[[AnalyticsRepository], Coroutine[Any, Any, T]]) -> T:
        """Execute a repo-bound operation in a standalone session."""
        async with self.session_factory() as session:
            repo = AnalyticsRepository(session)
            return await task_func(repo)

    async def _run_tasks_concurrently(self, tasks: List[AnalyticsTask]) -> Dict[str, Any]:
        """Run tasks concurrently with global timeout and error bridging."""
        coroutines = [task.coro_func(*task.args) for task in tasks]

        try:
            results = await asyncio.wait_for(
                asyncio.gather(*coroutines, return_exceptions=True),
                timeout=ANALYTICS_TASK_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.error("Advanced analytics report generation timed out")
            return {task.key: task.default for task in tasks}

        return {tasks[i].key: self._safe_unpack(results[i], tasks[i].default) for i in range(len(tasks))}

    def _get_cutoff_time(self, days: int = 0, hours: int = 0) -> datetime:
        """Calculate cutoff datetime using the injected time provider."""
        return self.time_provider() - timedelta(days=days, hours=hours)

    @staticmethod
    def _safe_unpack(result: Any, default: T) -> T:
        """Handle exceptions from parallelized coroutines."""
        if isinstance(result, Exception):
            logger.error("Concurrent analytics task failed: %s", str(result), exc_info=result)
            return default
        return result

    async def _fetch_business_settings(self) -> Tuple[float, float]:
        """Fetch configuration values concurrently with fallback logic."""
        keys = ["analytics_cost_per_1k_tokens", "analytics_minutes_saved_per_doc"]
        defaults = [str(DEFAULT_COST_PER_1K_TOKENS), str(DEFAULT_MIN_SAVED_PER_DOC)]

        tasks = [self.settings_service.get_value(k, default=d) for k, d in zip(keys, defaults)]
        results = await asyncio.gather(*tasks)

        try:
            return float(results[0]), float(results[1])
        except (ValueError, TypeError, IndexError):
            logger.warning("Invalid business settings detected, using internal defaults")
            return DEFAULT_COST_PER_1K_TOKENS, DEFAULT_MIN_SAVED_PER_DOC

    # --- Data Calculators & Mappers ---

    @staticmethod
    def _calculate_business_metrics(stats: Dict[str, Any], cost_per_1k: float, min_saved: float) -> AnalyticsResponse:
        """Execute business-level KPI math."""
        total_tokens = int(stats.get("total_tokens", 0))
        total_docs = int(stats.get("total_docs", 0))

        return AnalyticsResponse(
            total_docs=total_docs,
            total_vectors=int(stats.get("total_vectors", 0)),
            total_tokens=total_tokens,
            estimated_cost=round((total_tokens / 1000.0) * cost_per_1k, 4),
            time_saved_hours=round((total_docs * min_saved) / 60.0, 1),
        )

    @staticmethod
    def _map_step_row(row: Any) -> StepBreakdown:
        """Map generic db row to StepBreakdown model."""
        item = StepBreakdown(
            step_name=getattr(row, "step_name", "unknown"),
            avg_duration=float(getattr(row, "avg_duration", 0.0)),
            step_count=int(getattr(row, "step_count", 0)),
        )

        avg_input = getattr(row, "avg_input_tokens", None)
        avg_output = getattr(row, "avg_output_tokens", None)

        if avg_input is not None or avg_output is not None:
            item.avg_tokens = {
                "input": float(avg_input or 0.0),
                "output": float(avg_output or 0.0),
            }
        return item

    @staticmethod
    def _calculate_diversity_metrics(rows: List[Any]) -> Optional[TopicDiversity]:
        """Calculate Herfindahl-based diversity score from frequencies."""
        freqs = [r[0] for r in rows if r and len(r) > 0]
        total_topics = sum(freqs)

        if total_topics == 0:
            return None

        herfindahl_index = sum((f / total_topics) ** 2 for f in freqs)
        dominant_topic_share = (max(freqs) / total_topics) * 100

        diversity_score = round(1.0 - herfindahl_index, 3)
        return TopicDiversity(
            diversity_score=diversity_score,
            total_topics=len(freqs),
            dominant_topic_share=round(dominant_topic_share, 2),
        )

    @staticmethod
    def _calculate_cache_metrics(row: Any, hours: int) -> CacheMetrics:
        """Extract cache KPIs from raw aggregates."""
        total_requests = int(getattr(row, "total_requests", 0))
        cache_hits = int(getattr(row, "cache_hits", 0))
        hit_rate = round((cache_hits / total_requests) * 100, 2) if total_requests > 0 else 0.0

        return CacheMetrics(
            hit_rate=hit_rate,
            total_requests=total_requests,
            cache_hits=cache_hits,
            cache_misses=total_requests - cache_hits,
            period_hours=hours,
        )

    @staticmethod
    def _map_trending_topic(t: Any) -> TrendingTopic:
        """Convert repository topic record to Pydantic model."""
        text = getattr(t, "canonical_text", "unknown")
        return TrendingTopic(
            topic=text,
            canonical_text=text,
            frequency=int(getattr(t, "frequency", 0)),
            variation_count=len(getattr(t, "raw_variations", [])),
            last_asked=getattr(t, "updated_at", None) or getattr(t, "created_at", None),
        )

    @staticmethod
    def _map_cost_row(row: Any) -> AssistantCost:
        """Perform pricing estimation/mapping for assistant usage."""
        input_tokens = int(getattr(row, "input_tokens", 0) or 0)
        output_tokens = int(getattr(row, "output_tokens", 0) or 0)

        # Implementation Note: Future work could fetch these costs dynamically from MODEL_PRICES mapping
        estimated_cost = (input_tokens * FALLBACK_INPUT_TOKEN_COST) + (output_tokens * FALLBACK_OUTPUT_TOKEN_COST)

        return AssistantCost(
            assistant_id=str(getattr(row, "id", "unknown")),
            assistant_name=getattr(row, "name", "Unknown"),
            total_tokens=int(getattr(row, "total_tokens", 0) or 0),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=round(estimated_cost, 4),
        )

    @staticmethod
    def _calculate_freshness_percentages(rows: List[Any]) -> List[DocumentFreshness]:
        """Convert freshness counts to percentage breakdown."""
        total_docs = sum(int(getattr(row, "doc_count", 0)) for row in rows)
        if total_docs == 0:
            return []

        return [
            DocumentFreshness(
                freshness_category=str(getattr(row, "freshness_category", "unknown")),
                doc_count=int(getattr(row, "doc_count", 0)),
                percentage=round((int(getattr(row, "doc_count", 0)) / total_docs) * 100, 2),
            )
            for row in rows
        ]

    @staticmethod
    def _calculate_session_distribution(rows: List[Any]) -> List[SessionDistribution]:
        """Convert raw sessions to intensity buckets."""
        buckets = {"Single Question": 0, "Normal (2-5)": 0, "Power User (5+)": 0}
        total_sessions = len(rows)

        if total_sessions == 0:
            return []

        for row in rows:
            q_count = int(getattr(row, "q_count", 0))
            if q_count == 1:
                buckets["Single Question"] += 1
            elif 2 <= q_count <= 5:
                buckets["Normal (2-5)"] += 1
            else:
                buckets["Power User (5+)"] += 1

        return [
            SessionDistribution(
                session_type=k,
                session_count=v,
                percentage=round((v / total_sessions) * 100, 2),
            )
            for k, v in buckets.items()
        ]

    @staticmethod
    def _map_utilization_row(row: Any) -> DocumentUtilization:
        """Categorize document usage (hot/warm/cold)."""
        count = int(getattr(row, "retrieval_count", 0))
        status = "hot" if count > 10 else ("warm" if count > 0 else "cold")

        return DocumentUtilization(
            file_name=str(getattr(row, "doc_id", "unknown")),
            connector_name="Internal",
            retrieval_count=count,
            last_retrieved=getattr(row, "last_retrieved", None),
            status=status,
        )

    @staticmethod
    def _map_sync_rate_row(row: Any) -> ConnectorSyncRate:
        """Map sync logs to reliability metrics."""
        total = int(getattr(row, "total_syncs", 0) or 0)
        success = int(getattr(row, "successful_syncs", 0) or 0)

        return ConnectorSyncRate(
            connector_id=str(getattr(row, "id", "unknown")),
            connector_name=getattr(row, "name", "Unknown"),
            success_rate=round((success / total) * 100, 2) if total > 0 else 0.0,
            total_syncs=total,
            successful_syncs=success,
            failed_syncs=int(getattr(row, "failed_syncs", 0) or 0),
            avg_sync_duration=round(float(row.avg_duration), 2) if getattr(row, "avg_duration", None) else None,
        )

    @staticmethod
    def _map_user_stat_row(row: Any) -> UserStat:
        """Merge user metadata and usage stats."""
        email = str(getattr(row, "email", "unknown"))
        fname = getattr(row, "first_name", None)
        lname = getattr(row, "last_name", None)
        full_name = f"{fname or ''} {lname or ''}".strip() or email

        return UserStat(
            user_id=str(getattr(row, "user_id", "unknown")),
            email=email,
            full_name=full_name,
            total_tokens=int(getattr(row, "total_tokens", 0) or 0),
            interaction_count=int(getattr(row, "interaction_count", 0) or 0),
            last_active=getattr(row, "last_active", None),
        )


# --- Dependency Provider ---


def get_analytics_service(
    session_factory: Annotated[async_sessionmaker[AsyncSession], Depends(get_session_factory)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> AnalyticsService:
    """Dependency injection provider for FastAPI."""
    return AnalyticsService(session_factory=session_factory, settings_service=settings_service)
