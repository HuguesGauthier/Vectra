from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.models.topic_stat import TopicStat
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.document_repository import DocumentRepository
from app.services.analytics_service import AnalyticsService
from app.services.settings_service import SettingsService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.mark.asyncio
async def test_business_metrics(mock_db):
    """Test get_business_metrics logic."""
    mock_doc_repo = AsyncMock(spec=DocumentRepository)
    mock_doc_repo.get_aggregate_stats.return_value = {"total_docs": 10, "total_tokens": 10000, "total_vectors": 50}
    mock_settings = AsyncMock(spec=SettingsService)
    mock_settings.get_value.side_effect = ["0.0001", "5.0"]  # cost, time_saved

    service = AnalyticsService(db=mock_db, document_repo=mock_doc_repo, settings_service=mock_settings)

    metrics = await service.get_business_metrics()

    assert metrics.total_docs == 10
    assert metrics.estimated_cost == 0.001  # 10000 / 1000 * 0.0001
    assert (
        metrics.time_saved_hours == 0.8
    )  # (10 * 5) / 60 = 0.833 -> round 0.8? Schema says 1 decimal? round(0.833, 1) = 0.8
    # Actually wait round(0.8333) -> 0.8.


@pytest.mark.asyncio
async def test_advanced_analytics_facade(mock_db):
    """Test get_all_advanced_analytics orchestration."""
    mock_repo = AsyncMock(spec=AnalyticsRepository)
    mock_doc_repo = AsyncMock()
    mock_settings = AsyncMock()

    # Mock return values for repo
    mock_repo.get_ttft_percentiles.return_value = {"p50": 0.5, "p95": 1.0, "p99": 2.0}
    mock_repo.get_step_breakdown.return_value = []
    mock_repo.get_cache_stats.return_value = MagicMock(cache_hits=5, total_requests=10)
    mock_repo.get_trending_topics.return_value = []
    mock_repo.get_topic_frequencies.return_value = []

    # Fully mock other calls to prevent AsyncMock comparison errors
    mock_repo.get_assistant_usage_sums.return_value = []
    mock_repo.get_document_freshness_stats.return_value = []
    mock_repo.get_session_counts.return_value = []
    mock_repo.get_document_retrieval_stats.return_value = []
    mock_repo.get_reranking_stats.return_value = None  # Return None for simplicity
    mock_repo.get_connector_sync_stats.return_value = []

    service = AnalyticsService(
        db=mock_db, analytics_repo=mock_repo, document_repo=mock_doc_repo, settings_service=mock_settings
    )

    result = await service.get_all_advanced_analytics()

    assert result is not None
    assert result.ttft_percentiles.p50 == 0.5
    assert result.cache_metrics.hit_rate == 50.0


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_business_metrics(AsyncMock()))
    asyncio.run(test_advanced_analytics_facade(AsyncMock()))
    print("Manual Test Run Passed")
