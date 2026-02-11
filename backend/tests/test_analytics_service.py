import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.services.analytics_service import AnalyticsService, AnalyticsTask
from app.schemas.analytics import AnalyticsResponse

# --- Fixtures ---

@pytest.fixture
def mock_session_factory():
    factory = MagicMock()
    session = AsyncMock()
    factory.return_value.__aenter__.return_value = session
    return factory


@pytest.fixture
def mock_settings_service():
    service = AsyncMock()
    # Fixed settings mock to return values
    async def get_val(k, default=None):
        return default
    service.get_value.side_effect = get_val
    return service


@pytest.fixture
def analytics_service(mock_session_factory, mock_settings_service):
    return AnalyticsService(
        session_factory=mock_session_factory,
        settings_service=mock_settings_service
    )


# --- Tests ---

@pytest.mark.asyncio
async def test_get_business_metrics_happy_path(analytics_service, mock_session_factory):
    """Happy path: aggregation of tokens, docs and cost."""
    # Arrange
    # Mock DocumentRepository within the context of AnalyticsService.get_business_metrics
    with patch("app.services.analytics_service.DocumentRepository") as MockRepo:
        repo_instance = MockRepo.return_value
        repo_instance.get_aggregate_stats = AsyncMock(return_value={
            "total_tokens": 1000000,
            "total_docs": 100,
            "total_vectors": 500
        })
        
        # Act
        result = await analytics_service.get_business_metrics()
        
        # Assert
        assert isinstance(result, AnalyticsResponse)
        assert result.total_tokens == 1000000
        assert result.total_docs == 100
        # Check calculation (cost: 1000k * 0.0001 = 0.1)
        assert result.estimated_cost == 0.1
        # Time saved: (100 * 5) / 60 = 8.33 -> 8.3
        assert result.time_saved_hours == 8.3


@pytest.mark.asyncio
async def test_get_business_metrics_degraded_on_failure(analytics_service, mock_session_factory):
    """Robustness check: verify degraded state logging on failure."""
    # Arrange
    with patch("app.services.analytics_service.DocumentRepository") as MockRepo:
        repo_instance = MockRepo.return_value
        repo_instance.get_aggregate_stats.side_effect = Exception("DB Connection Lost")
        
        # Act
        result = await analytics_service.get_business_metrics()
        
        # Assert
        assert result.total_docs == 0  # Empty response on failure


@pytest.mark.asyncio
async def test_run_tasks_concurrently_success(analytics_service):
    """Verify concurrent task execution success flow."""
    async def fast_coro(*args):
        return "fast"

    tasks = [
        AnalyticsTask("task1", fast_coro, (), "default1"),
        AnalyticsTask("task2", fast_coro, (), "default2")
    ]
    
    # Act
    results = await analytics_service._run_tasks_concurrently(tasks)
    
    # Assert
    assert results["task1"] == "fast"
    assert results["task2"] == "fast"


def test_calculate_diversity_metrics_logic(analytics_service):
    """Test the math logic behind topic diversity."""
    # Arrange
    # Simulating rows result: frequencies [10, 10] -> perfect diversity among 2 topics
    rows = [(10,), (10,)]
    
    # Act
    result = analytics_service._calculate_diversity_metrics(rows)
    
    # Assert
    # Total topics = 2, Total scale = 20
    # Herfindahl = (10/20)^2 + (10/20)^2 = 0.25 + 0.25 = 0.5
    # Score = 1 - 0.5 = 0.5
    assert result.diversity_score == 0.5
    assert result.total_topics == 2
    assert result.dominant_topic_share == 50.0
