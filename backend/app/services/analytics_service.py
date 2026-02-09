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

# --- Constants ---
DEFAULT_COST_PER_1K_TOKENS: str = "0.0001"
DEFAULT_MIN_SAVED_PER_DOC: str = "5.0"
DEFAULT_TRENDING_LIMIT: int = 10
DEFAULT_USER_STATS_DAYS: int = 30
COST_PER_INPUT_TOKEN: float = 0.00001
COST_PER_OUTPUT_TOKEN: float = 0.00003

T = TypeVar("T")


@dataclass
class AnalyticsTask:
    """Configuration for an advanced analytics task.

    Attributes:
        key: The key identifying the task in the results dictionary.
        coro: The coroutine function to execute.
        args: Positional arguments to pass to the coroutine.
        default: Default value to return if the task fails.
    """

    key: str
    coro: Callable[..., Coroutine[Any, Any, Any]]
    args: Tuple[Any, ...] = ()
    default: Any = None


class AnalyticsService:
    """Unified Analytics Service.

    Responsibilities (SRP):
    1. Metric Aggregation (Parallelized).
    2. Data Transformation (DB Rows -> Pydantic Schemas).
    3. Configuration Management (Settings integration).

    Attributes:
        session_factory: Factory for creating AsyncSession instances.
        settings_service: Service for retrieving application settings.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings_service: SettingsService,
    ) -> None:
        """Initialize AnalyticsService.

        Args:
            session_factory: Factory to create new AsyncSession instances for parallel tasks.
            settings_service: The settings service instance.
        """
        self.session_factory = session_factory
        self.settings_service = settings_service

    # --- Public API ---

    async def get_business_metrics(self) -> AnalyticsResponse:
        """Aggregates simple business metrics with error handling.

        Returns:
            AnalyticsResponse: The aggregated business metrics containing document,
                vector, and token counts, along with estimated costs and time saved.
        """
        try:
            settings_task = self._fetch_business_settings()

            async with self.session_factory() as session:
                document_repo = DocumentRepository(session)
                stats = await document_repo.get_aggregate_stats()

            cost_per_1k, min_saved = await settings_task

            return self._calculate_business_metrics(stats, cost_per_1k, min_saved)

        except Exception as e:
            logger.error("Failed to calculate business metrics: %s", e, exc_info=True)
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
        """Generate a complete advanced analytics report by running all metric queries concurrently.

        Args:
            ttft_hours: Hours to look back for TTFT calculations.
            step_days: Days to look back for step breakdown and other metrics.
            cache_hours: Hours to look back for cache metrics.
            cost_hours: Hours to look back for assistant costs.
            trending_limit: Limit for the number of trending topics.
            assistant_id: Optional assistant ID to filter metrics.

        Returns:
            AdvancedAnalyticsResponse: The complete advanced analytics report.
        """
        tasks = self._get_advanced_analytics_tasks(
            ttft_hours, step_days, cache_hours, cost_hours, trending_limit, assistant_id
        )
        results = await self._run_tasks_concurrently(tasks)
        return AdvancedAnalyticsResponse(**results)

    # --- Individual Metric Methods ---

    async def get_ttft_percentiles(self, hours: int) -> Optional[TTFTPercentiles]:
        """Fetch Time To First Token (TTFT) percentiles.

        Args:
            hours: The number of hours to look back.

        Returns:
            Optional[TTFTPercentiles]: The TTFT percentiles, or None if no data is available.
        """

        async def _fetch(repo: AnalyticsRepository) -> Optional[Dict[str, Any]]:
            return await repo.get_ttft_percentiles(self._get_cutoff_time(hours=hours))

        data = await self._execute_repo_task(_fetch)
        return TTFTPercentiles(**data, period_hours=hours) if data else None

    async def get_step_breakdown(self, days: int) -> List[StepBreakdown]:
        """Fetch average duration and token counts for each step in the pipeline.

        Args:
            days: The number of days to look back.

        Returns:
            List[StepBreakdown]: A list of StepBreakdown objects.
        """
        rows = await self._execute_repo_task(
            lambda repo: repo.get_step_breakdown(self._get_cutoff_time(days=days))
        )
        return [self._map_step_row(row) for row in rows]

    async def get_cache_metrics(self, hours: int) -> Optional[CacheMetrics]:
        """Fetch cache hit rate and total requests.

        Args:
            hours: The number of hours to look back.

        Returns:
            Optional[CacheMetrics]: The cache metrics, or None if no data is available.
        """
        row = await self._execute_repo_task(
            lambda repo: repo.get_cache_stats(self._get_cutoff_time(hours=hours))
        )
        if not row or not getattr(row, "total_requests", 0):
            return None
        return self._calculate_cache_metrics(row, hours)

    async def get_trending_topics(
        self, assistant_id: Optional[UUID], limit: int
    ) -> List[TrendingTopic]:
        """Fetch the most frequently asked topics.

        Args:
            assistant_id: The ID of the assistant to filter by.
            limit: The maximum number of topics to return.

        Returns:
            List[TrendingTopic]: A list of TrendingTopic objects.
        """
        topics = await self._execute_repo_task(
            lambda repo: repo.get_trending_topics(limit, assistant_id)
        )
        return [self._map_trending_topic(t) for t in topics]

    async def get_topic_diversity(
        self, assistant_id: Optional[UUID]
    ) -> Optional[TopicDiversity]:
        """Calculate a diversity score for topics.

        Args:
            assistant_id: The ID of the assistant to filter by.

        Returns:
            Optional[TopicDiversity]: The topic diversity metrics, or None if no data is available.
        """
        rows = await self._execute_repo_task(
            lambda repo: repo.get_topic_frequencies(assistant_id)
        )
        if not rows:
            return None
        return self._calculate_diversity_metrics(rows)

    async def get_assistant_costs(self, hours: int) -> List[AssistantCost]:
        """Fetch token usage and estimated costs per assistant.

        Args:
            hours: The number of hours to look back.

        Returns:
            List[AssistantCost]: A list of AssistantCost objects.
        """
        rows = await self._execute_repo_task(
            lambda repo: repo.get_assistant_usage_sums(self._get_cutoff_time(hours=hours))
        )
        return [self._map_cost_row(row) for row in rows]

    async def get_document_freshness(self) -> List[DocumentFreshness]:
        """Fetch statistics on the age of documents in the system.

        Returns:
            List[DocumentFreshness]: A list of DocumentFreshness objects.
        """
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        ninety_days_ago = now - timedelta(days=90)

        rows = await self._execute_repo_task(
            lambda repo: repo.get_document_freshness_stats(thirty_days_ago, ninety_days_ago)
        )
        return self._calculate_freshness_percentages(rows)

    async def get_session_distribution(self, days: int) -> List[SessionDistribution]:
        """Categorize user sessions by the number of questions asked.

        Args:
            days: The number of days to look back.

        Returns:
            List[SessionDistribution]: A list of SessionDistribution objects.
        """
        rows = await self._execute_repo_task(
            lambda repo: repo.get_session_counts(self._get_cutoff_time(days=days))
        )
        return self._calculate_session_distribution(rows)

    async def get_document_utilization(self, days: int) -> List[DocumentUtilization]:
        """Fetch how frequently documents are being retrieved.

        Args:
            days: The number of days to look back.

        Returns:
            List[DocumentUtilization]: A list of DocumentUtilization objects.
        """
        rows = await self._execute_repo_task(
            lambda repo: repo.get_document_retrieval_stats(self._get_cutoff_time(days=days))
        )
        return [self._map_utilization_row(row) for row in rows]

    async def get_reranking_impact(self, hours: int) -> Optional[RerankingImpact]:
        """Fetch statistics on the effectiveness of the reranking step.

        Args:
            hours: The number of hours to look back.

        Returns:
            Optional[RerankingImpact]: The reranking impact metrics, or None if no data is available.
        """
        row = await self._execute_repo_task(
            lambda repo: repo.get_reranking_stats(self._get_cutoff_time(hours=hours))
        )
        if row and getattr(row, "reranking_count", 0) > 0:
            return self._map_reranking_impact(row)
        return None

    async def get_connector_sync_rates(self, days: int) -> List[ConnectorSyncRate]:
        """Fetch success/failure rates for connector sync jobs.

        Args:
            days: The number of days to look back.

        Returns:
            List[ConnectorSyncRate]: A list of ConnectorSyncRate objects.
        """
        rows = await self._execute_repo_task(
            lambda repo: repo.get_connector_sync_stats(self._get_cutoff_time(days=days))
        )
        return [self._map_sync_rate_row(row) for row in rows]

    async def get_user_stats(self, days: int) -> List[UserStat]:
        """Fetch usage statistics per user.

        Args:
            days: The number of days to look back.

        Returns:
            List[UserStat]: A list of UserStat objects.
        """
        rows = await self._execute_repo_task(
            lambda repo: repo.get_user_usage_stats(self._get_cutoff_time(days=days))
        )
        return [self._map_user_stat_row(row) for row in rows]

    # --- Private Helper Methods ---

    def _get_advanced_analytics_tasks(
        self,
        ttft_hours: int,
        step_days: int,
        cache_hours: int,
        cost_hours: int,
        trending_limit: int,
        assistant_id: Optional[UUID],
    ) -> List[AnalyticsTask]:
        """Create a list of all advanced analytics tasks.

        Args:
            ttft_hours: Hours to look back for TTFT calculations.
            step_days: Days to look back for step breakdown.
            cache_hours: Hours to look back for cache metrics.
            cost_hours: Hours to look back for assistant costs.
            trending_limit: Limit for trending topics.
            assistant_id: ID of the assistant to filter by.

        Returns:
            List[AnalyticsTask]: A list of AnalyticsTask objects.
        """
        return [
            AnalyticsTask("ttft_percentiles", self.get_ttft_percentiles, (ttft_hours,)),
            AnalyticsTask("step_breakdown", self.get_step_breakdown, (step_days,), []),
            AnalyticsTask("cache_metrics", self.get_cache_metrics, (cache_hours,)),
            AnalyticsTask(
                "trending_topics", self.get_trending_topics, (assistant_id, trending_limit), []
            ),
            AnalyticsTask("topic_diversity", self.get_topic_diversity, (assistant_id,)),
            AnalyticsTask("assistant_costs", self.get_assistant_costs, (cost_hours,), []),
            AnalyticsTask("document_freshness", self.get_document_freshness, (), []),
            AnalyticsTask("session_distribution", self.get_session_distribution, (step_days,), []),
            AnalyticsTask(
                "document_utilization",
                self.get_document_utilization,
                (DEFAULT_USER_STATS_DAYS,),
                [],
            ),
            AnalyticsTask("reranking_impact", self.get_reranking_impact, (cache_hours,)),
            AnalyticsTask(
                "connector_sync_rates", self.get_connector_sync_rates, (step_days,), []
            ),
            AnalyticsTask("user_stats", self.get_user_stats, (DEFAULT_USER_STATS_DAYS,), []),
        ]

    async def _execute_repo_task(
        self, task: Callable[[AnalyticsRepository], Coroutine[Any, Any, T]]
    ) -> T:
        """Execute a task with an AnalyticsRepository.

        Args:
            task: The task coroutine function to execute.

        Returns:
            T: The result of the task.
        """
        async with self.session_factory() as session:
            repo = AnalyticsRepository(session)
            return await task(repo)

    async def _run_tasks_concurrently(self, tasks: List[AnalyticsTask]) -> Dict[str, Any]:
        """Run a list of analytics tasks concurrently.

        Args:
            tasks: The list of tasks to run.

        Returns:
            Dict[str, Any]: A dictionary of results where keys match task keys.
        """
        coroutines = [task.coro(*task.args) for task in tasks]
        results = await asyncio.gather(*coroutines, return_exceptions=True)
        return {
            tasks[i].key: self._safe_result(results[i], tasks[i].default)
            for i in range(len(tasks))
        }

    @staticmethod
    def _get_cutoff_time(days: int = 0, hours: int = 0) -> datetime:
        """Calculate a cutoff datetime based on a relative timedelta.

        Args:
            days: The number of days to subtract.
            hours: The number of hours to subtract.

        Returns:
            datetime: The calculated cutoff datetime in UTC.
        """
        return datetime.now(timezone.utc) - timedelta(days=days, hours=hours)

    @staticmethod
    def _safe_result(result: Any, default: T) -> T:
        """Return the default value if the result is an exception.

        Args:
            result: The result of a task execution.
            default: The default value to return on failure.

        Returns:
            T: The result or the default value.
        """
        if isinstance(result, Exception):
            logger.error("A task failed during parallel execution: %s", result, exc_info=result)
            return default
        return result

    async def _fetch_business_settings(self) -> Tuple[float, float]:
        """Fetch analytics settings concurrently.

        Returns:
            Tuple[float, float]: (cost_per_1k_tokens, minutes_saved_per_doc).
        """
        cost_task = self.settings_service.get_value(
            "analytics_cost_per_1k_tokens", default=DEFAULT_COST_PER_1K_TOKENS
        )
        min_saved_task = self.settings_service.get_value(
            "analytics_minutes_saved_per_doc", default=DEFAULT_MIN_SAVED_PER_DOC
        )
        cost_str, min_saved_str = await asyncio.gather(cost_task, min_saved_task)
        try:
            return float(cost_str), float(min_saved_str)
        except (ValueError, TypeError):
            return float(DEFAULT_COST_PER_1K_TOKENS), float(DEFAULT_MIN_SAVED_PER_DOC)

    @staticmethod
    def _calculate_business_metrics(
        stats: Dict[str, Any], cost_per_1k: float, min_saved: float
    ) -> AnalyticsResponse:
        """Calculate and build the AnalyticsResponse.

        Args:
            stats: Raw aggregate statistics.
            cost_per_1k: Cost per 1000 tokens.
            min_saved: Minutes saved per document.

        Returns:
            AnalyticsResponse: Calculated business metrics.
        """
        total_tokens = stats.get("total_tokens", 0)
        total_docs = stats.get("total_docs", 0)

        return AnalyticsResponse(
            total_docs=total_docs,
            total_vectors=stats.get("total_vectors", 0),
            total_tokens=total_tokens,
            estimated_cost=round((total_tokens / 1000.0) * cost_per_1k, 4),
            time_saved_hours=round((total_docs * min_saved) / 60.0, 1),
        )

    @staticmethod
    def _map_step_row(row: Any) -> StepBreakdown:
        """Map a database row to a StepBreakdown Pydantic model.

        Args:
            row: Database row from step breakdown query.

        Returns:
            StepBreakdown: Mapped step breakdown metrics.
        """
        item = StepBreakdown(
            step_name=getattr(row, "step_name", "unknown"),
            avg_duration=float(getattr(row, "avg_duration", 0)),
            step_count=int(getattr(row, "step_count", 0)),
        )
        avg_input = getattr(row, "avg_input_tokens", None)
        avg_output = getattr(row, "avg_output_tokens", None)
        if avg_input is not None or avg_output is not None:
            item.avg_tokens = {
                "input": float(avg_input or 0),
                "output": float(avg_output or 0),
            }
        return item

    @staticmethod
    def _calculate_diversity_metrics(rows: List[Any]) -> Optional[TopicDiversity]:
        """Calculate Herfindahl index based diversity score.

        Args:
            rows: List of topic frequency rows.

        Returns:
            Optional[TopicDiversity]: Calculated diversity metrics.
        """
        freqs = [r[0] for r in rows if r and len(r) > 0]
        total_topics = sum(freqs)
        if total_topics == 0:
            return None

        # Herfindahl index: measures topic concentration.
        herfindahl_index = sum((f / total_topics) ** 2 for f in freqs)
        dominant_topic_share = (max(freqs) / total_topics) * 100

        return TopicDiversity(
            diversity_score=round(1 - herfindahl_index, 3),
            total_topics=len(freqs),
            dominant_topic_share=round(dominant_topic_share, 2),
        )

    @staticmethod
    def _calculate_cache_metrics(row: Any, hours: int) -> CacheMetrics:
        """Calculate cache metrics from a database row.

        Args:
            row: Database row with cache stats.
            hours: Time period in hours.

        Returns:
            CacheMetrics: Calculated cache effectiveness metrics.
        """
        total_requests = getattr(row, "total_requests", 0)
        cache_hits = getattr(row, "cache_hits", 0)
        hit_rate = (
            round((cache_hits / total_requests) * 100, 2) if total_requests > 0 else 0.0
        )

        return CacheMetrics(
            hit_rate=hit_rate,
            total_requests=total_requests,
            cache_hits=cache_hits,
            cache_misses=total_requests - cache_hits,
            period_hours=hours,
        )

    @staticmethod
    def _map_trending_topic(t: Any) -> TrendingTopic:
        """Map a database row to a TrendingTopic Pydantic model.

        Args:
            t: Database row with trending topic data.

        Returns:
            TrendingTopic: Mapped trending topic info.
        """
        return TrendingTopic(
            canonical_text=getattr(t, "canonical_text", ""),
            frequency=getattr(t, "frequency", 0),
            variation_count=len(getattr(t, "raw_variations", [])),
            last_asked=getattr(t, "updated_at", None) or getattr(t, "created_at", None),
        )

    @staticmethod
    def _map_cost_row(row: Any) -> AssistantCost:
        """Map a database row to an AssistantCost Pydantic model.

        Args:
            row: Database row with assistant usage data.

        Returns:
            AssistantCost: Mapped assistant cost metrics.
        """
        input_tokens = int(getattr(row, "input_tokens", 0) or 0)
        output_tokens = int(getattr(row, "output_tokens", 0) or 0)
        estimated_cost = (input_tokens * COST_PER_INPUT_TOKEN) + (
            output_tokens * COST_PER_OUTPUT_TOKEN
        )

        return AssistantCost(
            assistant_id=str(getattr(row, "id", "")),
            assistant_name=getattr(row, "name", "Unknown"),
            total_tokens=int(getattr(row, "total_tokens", 0) or 0),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=round(estimated_cost, 4),
        )

    @staticmethod
    def _calculate_freshness_percentages(rows: List[Any]) -> List[DocumentFreshness]:
        """Calculate the percentage of documents in each freshness category.

        Args:
            rows: List of document freshness rows.

        Returns:
            List[DocumentFreshness]: Freshness breakdown for documents.
        """
        total_docs = sum(getattr(row, "doc_count", 0) for row in rows)
        if total_docs == 0:
            return []

        return [
            DocumentFreshness(
                freshness_category=getattr(row, "freshness_category", "unknown"),
                doc_count=getattr(row, "doc_count", 0),
                percentage=round((getattr(row, "doc_count", 0) / total_docs) * 100, 2),
            )
            for row in rows
        ]

    @staticmethod
    def _calculate_session_distribution(rows: List[Any]) -> List[SessionDistribution]:
        """Calculate the distribution of user sessions.

        Args:
            rows: List of session question count rows.

        Returns:
            List[SessionDistribution]: Breakdown of session intensity.
        """
        buckets = {"Single Question": 0, "Normal (2-5)": 0, "Power User (5+)": 0}
        total_sessions = 0
        for row in rows:
            AnalyticsService._categorize_session_count(buckets, getattr(row, "q_count", 0))
            total_sessions += 1

        if total_sessions == 0:
            return []

        return [
            SessionDistribution(
                session_type=k,
                session_count=v,
                percentage=round((v / total_sessions) * 100, 2),
            )
            for k, v in buckets.items()
        ]

    @staticmethod
    def _categorize_session_count(buckets: Dict[str, int], count: int) -> None:
        """Increment the appropriate session category bucket.

        Args:
            buckets: Dictionary of category counters.
            count: Question count in the session.
        """
        if count == 1:
            buckets["Single Question"] += 1
        elif 2 <= count <= 5:
            buckets["Normal (2-5)"] += 1
        else:
            buckets["Power User (5+)"] += 1

    @staticmethod
    def _map_utilization_row(row: Any) -> DocumentUtilization:
        """Map a database row to a DocumentUtilization Pydantic model.

        Args:
            row: Database row with document retrieval stats.

        Returns:
            DocumentUtilization: Mapped document usage metrics.
        """
        retrieval_count = getattr(row, "retrieval_count", 0)
        if retrieval_count > 10:
            status = "hot"
        elif retrieval_count > 0:
            status = "warm"
        else:
            status = "cold"

        return DocumentUtilization(
            file_name=str(getattr(row, "doc_id", "unknown")),
            connector_name="Unknown",  # Placeholder
            retrieval_count=retrieval_count,
            last_retrieved=getattr(row, "last_retrieved", None),
            status=status,
        )

    @staticmethod
    def _map_reranking_impact(row: Any) -> RerankingImpact:
        """Map a database row to a RerankingImpact Pydantic model.

        Args:
            row: Database row with reranking effectiveness data.

        Returns:
            RerankingImpact: Mapped reranking impact metrics.
        """
        return RerankingImpact(
            avg_score_improvement=round(getattr(row, "avg_improvement", 0) or 0, 3),
            reranking_enabled_count=getattr(row, "reranking_count", 0),
            avg_position_change=None,  # Placeholder for future implementation
        )

    @staticmethod
    def _map_sync_rate_row(row: Any) -> ConnectorSyncRate:
        """Map a database row to a ConnectorSyncRate Pydantic model.

        Args:
            row: Database row with connector sync stats.

        Returns:
            ConnectorSyncRate: Mapped connector reliability metrics.
        """
        total_syncs = getattr(row, "total_syncs", 0) or 0
        successful_syncs = getattr(row, "successful_syncs", 0) or 0
        success_rate = (
            round((successful_syncs / total_syncs) * 100, 2) if total_syncs > 0 else 0.0
        )

        return ConnectorSyncRate(
            connector_id=str(getattr(row, "id", "")),
            connector_name=getattr(row, "name", "Unknown"),
            success_rate=success_rate,
            total_syncs=total_syncs,
            successful_syncs=successful_syncs,
            failed_syncs=getattr(row, "failed_syncs", 0) or 0,
            avg_sync_duration=(
                round(row.avg_duration, 2) if getattr(row, "avg_duration", None) else None
            ),
        )

    @staticmethod
    def _map_user_stat_row(row: Any) -> UserStat:
        """Map a database row to a UserStat Pydantic model.

        Args:
            row: Database row with user activity stats.

        Returns:
            UserStat: Mapped user engagement metrics.
        """
        email = getattr(row, "email", "unknown")
        first_name = getattr(row, "first_name", None)
        last_name = getattr(row, "last_name", None)

        full_name = email
        if first_name or last_name:
            full_name = f"{first_name or ''} {last_name or ''}".strip()

        return UserStat(
            user_id=str(getattr(row, "user_id", "")),
            email=email,
            full_name=full_name,
            total_tokens=int(getattr(row, "total_tokens", 0) or 0),
            interaction_count=int(getattr(row, "interaction_count", 0) or 0),
            last_active=getattr(row, "last_active", None),
        )


# --- Dependency Injection ---


def get_analytics_service(
    session_factory: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_session_factory)
    ],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> AnalyticsService:
    """FastAPI dependency provider for the AnalyticsService.

    Args:
        session_factory: The SQLAlchemy session factory.
        settings_service: The application settings service.

    Returns:
        AnalyticsService: A configured instance of the analytics service.
    """
    return AnalyticsService(session_factory=session_factory, settings_service=settings_service)
