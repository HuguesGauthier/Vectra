import asyncio
import sys
from unittest.mock import MagicMock

# Pragmatic Mock for pyodbc and vanna to avoid collection errors in environments without native drivers
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()
sys.modules["vanna.remote"] = MagicMock()
sys.modules["vanna.openai"] = MagicMock()

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Only mock internal parts that might trigger circular deps or heavy side effects if needed.
# Relying on installed llama-index packages to avoid 'is not a package' errors.

from app.schemas.advanced_analytics import AdvancedAnalyticsResponse
from app.schemas.analytics import AnalyticsResponse
from app.services.analytics_service import (
    ANALYTICS_TASK_TIMEOUT,
    AnalyticsService,
    AnalyticsTask,
    get_analytics_service,
)


@pytest.fixture
def fixed_now():
    """Consistent UTC time for deterministic testing."""
    return datetime(2026, 2, 10, 18, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_session():
    """Mock for SQLAlchemy AsyncSession."""
    session = AsyncMock(spec=AsyncSession)
    session.__aenter__.return_value = session
    return session


@pytest.fixture
def mock_session_factory(mock_session):
    """Mock for async_sessionmaker."""
    factory = MagicMock()
    factory.return_value = mock_session
    return factory


@pytest.fixture
def mock_settings_service():
    """Mock for SettingsService with default behaviors."""
    service = AsyncMock()
    # Default behavior: return the default value provided to get_value
    service.get_value.side_effect = lambda key, default=None: AsyncMock(return_value=default)()
    return service


@pytest.fixture
def service(mock_session_factory, mock_settings_service, fixed_now):
    """Configured AnalyticsService instance for testing."""
    return AnalyticsService(
        session_factory=mock_session_factory,
        settings_service=mock_settings_service,
        time_provider=lambda: fixed_now,
    )


# --- Business Metrics Tests ---


@pytest.mark.asyncio
async def test_get_business_metrics_success(service, mock_session, monkeypatch):
    """Test successful business metrics calculation with multiple metrics."""
    mock_doc_repo = AsyncMock()
    mock_doc_repo.get_aggregate_stats.return_value = {
        "total_tokens": 100000,
        "total_docs": 50,
        "total_vectors": 5000,
    }
    monkeypatch.setattr("app.services.analytics_service.DocumentRepository", MagicMock(return_value=mock_doc_repo))

    # Mock settings: cost=0.0002, saved=10.0 mins
    service.settings_service.get_value.side_effect = ["0.0002", "10.0"]

    result = await service.get_business_metrics()

    assert isinstance(result, AnalyticsResponse)
    assert result.total_docs == 50
    assert result.total_tokens == 100000
    # (100000 / 1000) * 0.0002 = 0.02
    assert result.estimated_cost == 0.02
    # (50 * 10.0) / 60.0 = 8.333... -> 8.3
    assert result.time_saved_hours == 8.3


@pytest.mark.asyncio
async def test_get_business_metrics_error_recovery(service, monkeypatch):
    """Test business metrics with DB error (should return empty response)."""
    monkeypatch.setattr(
        "app.services.analytics_service.DocumentRepository",
        MagicMock(side_effect=Exception("DB Unreachable")),
    )

    result = await service.get_business_metrics()
    assert isinstance(result, AnalyticsResponse)
    assert result.total_docs == 0


# --- Advanced Analytics Aggregator Tests ---


@pytest.mark.asyncio
async def test_get_all_advanced_analytics_aggregator(service, monkeypatch):
    """Test the main aggregator runs all tasks and returns complex response."""
    # Mock individual metric methods to isolate the aggregator logic
    methods_to_mock = [
        "get_ttft_percentiles",
        "get_step_breakdown",
        "get_cache_metrics",
        "get_trending_topics",
        "get_topic_diversity",
        "get_assistant_costs",
        "get_document_freshness",
        "get_session_distribution",
        "get_document_utilization",
        "get_reranking_impact",
        "get_connector_sync_rates",
        "get_user_stats",
    ]
    for method in methods_to_mock:
        # Return empty list or None based on expected return type
        is_list = any(
            x in method
            for x in ["breakdown", "topics", "costs", "freshness", "distribution", "utilization", "rates", "stats"]
        )
        default_val = [] if is_list else None
        setattr(service, method, AsyncMock(return_value=default_val))

    result = await service.get_all_advanced_analytics()
    assert isinstance(result, AdvancedAnalyticsResponse)


# --- Concurrency & Resiliency Tests ---


@pytest.mark.asyncio
async def test_run_tasks_concurrently_with_timeout(service, monkeypatch):
    """Verify that the service respects the global ANALYTICS_TASK_TIMEOUT."""

    async def slow_task(*args):
        await asyncio.sleep(0.05)
        return "result"

    # Mock timeout to be very low
    monkeypatch.setattr("app.services.analytics_service.ANALYTICS_TASK_TIMEOUT", 0.01)

    tasks = [AnalyticsTask(key="t1", coro_func=slow_task, default="fallback")]
    results = await service._run_tasks_concurrently(tasks)

    assert results["t1"] == "fallback"


@pytest.mark.asyncio
async def test_safe_unpack_catches_exceptions(service):
    """Verify that internal unpacking logic handles exceptions gracefully."""
    err = ValueError("Calculation Error")
    result = service._safe_unpack(err, "safe_fallback")
    assert result == "safe_fallback"


# --- Specific Metric Calculation Tests ---


@pytest.mark.asyncio
async def test_get_ttft_percentiles_mapping(service, monkeypatch):
    """Verify TTFT percentile extraction and mapping."""
    mock_repo = AsyncMock()
    mock_repo.get_ttft_percentiles.return_value = {"p50": 0.45, "p95": 1.2, "p99": 3.0}
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))

    result = await service.get_ttft_percentiles(24)
    assert result.p50 == 0.45
    assert result.period_hours == 24


@pytest.mark.asyncio
async def test_get_step_breakdown_mapping(service, monkeypatch):
    """Verify step breakdown durations and token mapping."""
    mock_repo = AsyncMock()
    row = MagicMock()
    row.step_name = "synthesis"
    row.avg_duration = 1.25
    row.step_count = 100
    row.avg_input_tokens = 500
    row.avg_output_tokens = 250
    mock_repo.get_step_breakdown.return_value = [row]
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))

    result = await service.get_step_breakdown(7)
    assert len(result) == 1
    assert result[0].step_name == "synthesis"
    assert result[0].avg_tokens["input"] == 500


@pytest.mark.asyncio
async def test_get_topic_diversity_empty_case(service, monkeypatch):
    """Ensure diversity score returns None when no data exists (backward compatibility)."""
    mock_repo = AsyncMock()
    mock_repo.get_topic_frequencies.return_value = []
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))

    result = await service.get_topic_diversity(None)
    assert result is None


def test_calculate_diversity_metrics_logic(service):
    """Test the math logic behind topic diversity."""
    # Arrange
    # Simulating rows result: frequencies [10, 10] -> perfect diversity among 2 topics
    rows = [(10,), (10,)]

    # Act
    result = service._calculate_diversity_metrics(rows)

    # Assert
    # Total topics = 2, Total scale = 20
    # Herfindahl = (10/20)^2 + (10/20)^2 = 0.25 + 0.25 = 0.5
    # Score = 1 - 0.5 = 0.5
    assert result.diversity_score == 0.5
    assert result.total_topics == 2
    assert result.dominant_topic_share == 50.0


@pytest.mark.asyncio
async def test_get_assistant_costs_calculation(service, monkeypatch):
    """Test token cost estimation per assistant."""
    mock_repo = AsyncMock()
    row = MagicMock()
    row.id = uuid4()
    row.name = "Bot Alpha"
    row.input_tokens = 2000
    row.output_tokens = 1000
    row.total_tokens = 3000
    mock_repo.get_assistant_usage_sums.return_value = [row]
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))

    result = await service.get_assistant_costs(24)
    assert len(result) == 1
    # Costs: (2000 / 1000 * 0.00001) + (1000 / 1000 * 0.00003) = 0.00002 + 0.00003 = 0.00005
    assert result[0].estimated_cost_usd == 0.00005


@pytest.mark.asyncio
async def test_get_document_freshness_percentages(service, monkeypatch):
    """Verify freshness bucket percentage calculations."""
    mock_repo = AsyncMock()
    rows = [
        MagicMock(freshness_category="Fresh", doc_count=20),
        MagicMock(freshness_category="Stale", doc_count=80),
    ]
    mock_repo.get_document_freshness_stats.return_value = rows
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))

    result = await service.get_document_freshness()
    assert result[0].percentage == 20.0
    assert result[1].percentage == 80.0


@pytest.mark.asyncio
async def test_get_document_utilization_enriched_mapping(service, monkeypatch):
    """Verify document utilization report uses enriched names from repository."""
    mock_repo = AsyncMock()
    row = MagicMock()
    row.file_name = "report.pdf"
    row.connector_name = "SharePoint"
    row.retrieval_count = 15
    row.last_retrieved = datetime.now(timezone.utc)
    mock_repo.get_document_retrieval_stats.return_value = [row]
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))

    result = await service.get_document_utilization(30)
    assert len(result) == 1
    assert result[0].file_name == "report.pdf"
    assert result[0].connector_name == "SharePoint"
    assert result[0].status == "hot"


@pytest.mark.asyncio
async def test_get_user_stats_mapping_robustness(service, monkeypatch):
    """Verify user stat mapping handles missing names gracefully."""
    mock_repo = AsyncMock()
    row = MagicMock()
    row.user_id = uuid4()
    row.email = "anon@example.com"
    row.first_name = None
    row.last_name = None
    row.total_tokens = 10
    row.interaction_count = 1
    row.last_active = datetime.now(timezone.utc)
    mock_repo.get_user_usage_stats.return_value = [row]
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))

    result = await service.get_user_stats(30)
    assert result[0].full_name == "anon@example.com"


# --- DI Provider Test ---


def test_get_analytics_service_provider():
    """Verify the FastAPI dependency provider works as expected."""
    mock_factory = MagicMock()
    mock_settings = MagicMock()
    instance = get_analytics_service(mock_factory, mock_settings)
    assert isinstance(instance, AnalyticsService)
