import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.advanced_analytics import (
    AdvancedAnalyticsResponse,
    AssistantCost,
    ConnectorSyncRate,
    DocumentFreshness,
    StepBreakdown,
    SessionDistribution,
    TopicDiversity,
    TrendingTopic,
    TTFTPercentiles,
)
from app.services.analytics_service import AnalyticsService

# Create a TestClient instance
client = TestClient(app)


# Mock the get_analytics_service dependency
@pytest.fixture
def mock_analytics_service():
    service = AsyncMock(spec=AnalyticsService)
    return service


@pytest.fixture(autouse=True)
def override_get_analytics_service(mock_analytics_service):
    from app.services.analytics_service import get_analytics_service

    app.dependency_overrides[get_analytics_service] = lambda: mock_analytics_service
    yield
    app.dependency_overrides = {}


@pytest.fixture
def fixed_datetime():
    # Use a fixed datetime for predictable comparisons
    return datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
@patch("app.schemas.advanced_analytics.datetime")  # Corrected patch target
async def test_get_advanced_analytics_defaults(mock_datetime, mock_analytics_service, fixed_datetime):
    mock_datetime.utcnow.return_value = fixed_datetime
    mock_datetime.now.return_value = fixed_datetime

    expected_response = AdvancedAnalyticsResponse(
        ttft_percentiles=TTFTPercentiles(p50=10.0, p95=20.0, p99=30.0, period_hours=24),
        step_breakdown=[
            StepBreakdown(
                step_name="retrieve", avg_duration=1.0, step_count=10, avg_tokens={"input": 50.0, "output": 0.0}
            )
        ],
        cache_hit_rate=0.5,
        trending_topics=[
            TrendingTopic(
                topic="Topic A", canonical_text="topic a", frequency=10, variation_count=1, last_asked=fixed_datetime
            )
        ],
        topic_diversity=TopicDiversity(diversity_score=0.7, dominant_topic_share=0.2, total_topics=5),
        assistant_costs=[
            AssistantCost(
                assistant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13",
                assistant_name="Assistant 1",
                total_tokens=1000,
                input_tokens=800,
                output_tokens=200,
                estimated_cost_usd=0.10,
            )
        ],
        document_freshness=[DocumentFreshness(freshness_category="Fresh (<30d)", doc_count=10, percentage=0.5)],
        generated_at=fixed_datetime,
        connector_sync_rates=[
            ConnectorSyncRate(
                connector_id="conn1",
                connector_name="Con1",
                success_rate=90.0,
                total_syncs=100,
                successful_syncs=90,
                failed_syncs=10,
                avg_sync_duration=10.5,
            )
        ],
        session_distribution=[SessionDistribution(session_type="Single Question", session_count=50, percentage=50.0)],
    )
    mock_analytics_service.get_all_advanced_analytics.return_value = expected_response

    response = client.get("/api/v1/analytics/advanced")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_response.model_dump(mode="json")
    mock_analytics_service.get_all_advanced_analytics.assert_called_once_with(
        ttft_hours=24,
        step_days=7,
        cache_hours=24,
        cost_hours=24,
        trending_limit=10,
        assistant_id=None,
    )


@pytest.mark.asyncio
@patch("app.schemas.advanced_analytics.datetime")  # Corrected patch target
async def test_get_advanced_analytics_with_params(mock_datetime, mock_analytics_service, fixed_datetime):
    mock_datetime.utcnow.return_value = fixed_datetime
    mock_datetime.now.return_value = fixed_datetime

    assistant_id = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11")
    expected_response = AdvancedAnalyticsResponse(
        ttft_percentiles=TTFTPercentiles(p50=15.0, p95=25.0, p99=35.0, period_hours=48),
        step_breakdown=[
            StepBreakdown(step_name="embed", avg_duration=2.0, step_count=5, avg_tokens={"input": 100.0, "output": 0.0})
        ],
        cache_hit_rate=0.6,
        trending_topics=[
            TrendingTopic(
                topic="Topic C", canonical_text="topic c", frequency=15, variation_count=2, last_asked=fixed_datetime
            )
        ],
        topic_diversity=TopicDiversity(diversity_score=0.8, dominant_topic_share=0.1, total_topics=10),
        assistant_costs=[
            AssistantCost(
                assistant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a15",
                assistant_name="Assistant 2",
                total_tokens=2000,
                input_tokens=1500,
                output_tokens=500,
                estimated_cost_usd=0.20,
            )
        ],
        document_freshness=[DocumentFreshness(freshness_category="Aging (30-90d)", doc_count=5, percentage=0.25)],
        generated_at=fixed_datetime,
        connector_sync_rates=[
            ConnectorSyncRate(
                connector_id="conn2",
                connector_name="Con2",
                success_rate=80.0,
                total_syncs=50,
                successful_syncs=40,
                failed_syncs=10,
                avg_sync_duration=20.0,
            )
        ],
        session_distribution=[SessionDistribution(session_type="Normal (2-5)", session_count=30, percentage=30.0)],
    )
    mock_analytics_service.get_all_advanced_analytics.return_value = expected_response

    response = client.get(
        f"/api/v1/analytics/advanced?assistant_id={assistant_id}&ttft_hours=48&step_days=14&cache_hours=48&cost_hours=48&trending_limit=20"
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_response.model_dump(mode="json")
    mock_analytics_service.get_all_advanced_analytics.assert_called_once_with(
        ttft_hours=48,
        step_days=14,
        cache_hours=48,
        cost_hours=48,
        trending_limit=20,
        assistant_id=assistant_id,
    )


@pytest.mark.asyncio
async def test_get_ttft_percentiles_defaults(mock_analytics_service):
    expected_ttft = TTFTPercentiles(p50=10.0, p95=20.0, p99=30.0, period_hours=24)
    mock_analytics_service.get_ttft_percentiles.return_value = expected_ttft

    response = client.get("/api/v1/analytics/ttft")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == expected_ttft.model_dump(mode="json")
    mock_analytics_service.get_ttft_percentiles.assert_called_once_with(24)


@pytest.mark.asyncio
async def test_get_ttft_percentiles_no_result(mock_analytics_service):
    mock_analytics_service.get_ttft_percentiles.return_value = None

    response = client.get("/api/v1/analytics/ttft?hours=12")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == TTFTPercentiles(p50=0.0, p95=0.0, p99=0.0, period_hours=12).model_dump(mode="json")
    mock_analytics_service.get_ttft_percentiles.assert_called_once_with(12)


@pytest.mark.asyncio
async def test_get_trending_topics_defaults(mock_analytics_service, fixed_datetime):
    expected_topics = [
        TrendingTopic(
            topic="Topic A", canonical_text="topic a", frequency=10, variation_count=1, last_asked=fixed_datetime
        ),
        TrendingTopic(
            topic="Topic B", canonical_text="topic b", frequency=5, variation_count=1, last_asked=fixed_datetime
        ),
    ]
    mock_analytics_service.get_trending_topics.return_value = expected_topics

    response = client.get("/api/v1/analytics/trending")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [t.model_dump(mode="json") for t in expected_topics]
    mock_analytics_service.get_trending_topics.assert_called_once_with(None, 10)


@pytest.mark.asyncio
async def test_get_trending_topics_with_params(mock_analytics_service, fixed_datetime):
    assistant_id = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12")
    expected_topics = [
        TrendingTopic(
            topic="Topic C", canonical_text="topic c", frequency=15, variation_count=2, last_asked=fixed_datetime
        )
    ]
    mock_analytics_service.get_trending_topics.return_value = expected_topics

    response = client.get(f"/api/v1/analytics/trending?assistant_id={assistant_id}&limit=5")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [t.model_dump(mode="json") for t in expected_topics]
    mock_analytics_service.get_trending_topics.assert_called_once_with(assistant_id, 5)


@pytest.mark.asyncio
async def test_get_assistant_costs_defaults(mock_analytics_service):
    expected_costs = [
        AssistantCost(
            assistant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a13",
            assistant_name="Assistant 1",
            total_tokens=1000,
            input_tokens=800,
            output_tokens=200,
            estimated_cost_usd=0.10,
        ),
        AssistantCost(
            assistant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a14",
            assistant_name="Assistant 2",
            total_tokens=500,
            input_tokens=400,
            output_tokens=100,
            estimated_cost_usd=0.05,
        ),
    ]
    mock_analytics_service.get_assistant_costs.return_value = expected_costs

    response = client.get("/api/v1/analytics/costs")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [t.model_dump(mode="json") for t in expected_costs]
    mock_analytics_service.get_assistant_costs.assert_called_once_with(24)


@pytest.mark.asyncio
async def test_get_assistant_costs_with_hours(mock_analytics_service):
    expected_costs = [
        AssistantCost(
            assistant_id="a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a15",
            assistant_name="Assistant 3",
            total_tokens=2000,
            input_tokens=1500,
            output_tokens=500,
            estimated_cost_usd=0.20,
        )
    ]
    mock_analytics_service.get_assistant_costs.return_value = expected_costs

    response = client.get("/api/v1/analytics/costs?hours=48")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [t.model_dump(mode="json") for t in expected_costs]
    mock_analytics_service.get_assistant_costs.assert_called_once_with(48)


@pytest.mark.asyncio
async def test_get_document_freshness(mock_analytics_service):
    expected_freshness = [
        DocumentFreshness(freshness_category="Fresh (<30d)", doc_count=10, percentage=0.5),
        DocumentFreshness(freshness_category="Aging (30-90d)", doc_count=5, percentage=0.25),
    ]
    mock_analytics_service.get_document_freshness.return_value = expected_freshness

    response = client.get("/api/v1/analytics/freshness")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [t.model_dump(mode="json") for t in expected_freshness]
    mock_analytics_service.get_document_freshness.assert_called_once()


# Background task tests
@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


# We need to ensure global state is reset for background tasks tests
@pytest.fixture(autouse=True)
def reset_broadcast_globals():
    from app.api.v1.endpoints import analytics

    analytics._broadcast_task = None
    analytics._broadcast_running = False
    yield
    analytics._broadcast_task = None
    analytics._broadcast_running = False


@patch("app.api.v1.endpoints.analytics.broadcast_analytics_loop")
@patch("app.api.v1.endpoints.analytics.asyncio.create_task")
@patch("app.api.v1.endpoints.analytics.logger")
async def test_start_broadcast_task(mock_logger, mock_create_task, mock_broadcast_loop):
    from app.api.v1.endpoints import analytics

    await analytics.start_broadcast_task(interval_seconds=1)
    analytics._broadcast_task.done.return_value = False
    assert analytics._broadcast_running is True
    mock_create_task.assert_called_once()
    mock_logger.info.assert_called_with("Analytics broadcast task started")

    # Test calling again when already running
    mock_create_task.reset_mock()
    await analytics.start_broadcast_task(interval_seconds=1)
    mock_create_task.assert_not_called()
    mock_logger.warning.assert_called_with("Analytics broadcast task already running")


@patch("app.api.v1.endpoints.analytics.asyncio.wait_for")
@patch("app.api.v1.endpoints.analytics.logger")
async def test_stop_broadcast_task(mock_logger, mock_wait_for):
    from app.api.v1.endpoints import analytics

    # Test stopping when no task is running
    await analytics.stop_broadcast_task()
    mock_logger.info.assert_not_called()

    # Setup a mock task to be "stopped"
    mock_task = AsyncMock(spec=asyncio.Task)
    analytics._broadcast_task = mock_task
    analytics._broadcast_running = True

    await analytics.stop_broadcast_task()
    assert analytics._broadcast_running is False
    mock_wait_for.assert_called_once_with(mock_task, timeout=10.0)
    assert analytics._broadcast_task is None
    mock_logger.info.assert_called_with("Analytics broadcast task stopped")


@patch("app.api.v1.endpoints.analytics.asyncio.wait_for")
@patch("app.api.v1.endpoints.analytics.logger")
async def test_stop_broadcast_task_timeout(mock_logger, mock_wait_for):
    from app.api.v1.endpoints import analytics

    mock_task = AsyncMock(spec=asyncio.Task)
    mock_wait_for.side_effect = asyncio.TimeoutError
    analytics._broadcast_task = mock_task
    analytics._broadcast_running = True

    await analytics.stop_broadcast_task()
    assert analytics._broadcast_running is False
    mock_wait_for.assert_called_once_with(mock_task, timeout=10.0)
    mock_task.cancel.assert_called_once()
    mock_logger.warning.assert_called_with("Analytics broadcast task did not stop gracefully, cancelling")
    assert analytics._broadcast_task is None
    mock_logger.info.assert_called_with("Analytics broadcast task stopped")


@patch("app.api.v1.endpoints.analytics.asyncio.wait_for")
@patch("app.api.v1.endpoints.analytics.logger")
async def test_stop_broadcast_task_general_exception(mock_logger, mock_wait_for):
    from app.api.v1.endpoints import analytics

    mock_task = AsyncMock(spec=asyncio.Task)
    mock_wait_for.side_effect = Exception("Test Error")
    analytics._broadcast_task = mock_task
    analytics._broadcast_running = True

    await analytics.stop_broadcast_task()
    mock_logger.error.assert_called_once()
    # Check only the first arg of the call
    assert mock_logger.error.call_args[0][0] == "Error during stop_broadcast_task: %s"
    assert str(mock_logger.error.call_args[0][1]) == "Test Error"
    assert analytics._broadcast_task is None  # Should still reset task to None
    mock_logger.info.assert_called_with("Analytics broadcast task stopped")


@patch("app.api.v1.endpoints.analytics.asyncio.sleep", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.analytics.get_session_factory")
@patch("app.api.v1.endpoints.analytics.SettingsService")
@patch("app.api.v1.endpoints.analytics.AnalyticsService")
@patch("app.api.v1.endpoints.analytics.logger")
@patch("app.core.connection_manager.manager", new_callable=AsyncMock)
@patch("app.schemas.advanced_analytics.datetime")
async def test_broadcast_analytics_loop(
    mock_datetime,
    mock_manager,
    mock_logger,
    mock_analytics_service_class,
    mock_settings_service_class,
    mock_get_session_factory_param,
    mock_sleep,
    fixed_datetime,
):
    from app.api.v1.endpoints import analytics

    # Configure mocks
    mock_analytics_instance = mock_analytics_service_class.return_value = AsyncMock(spec=AnalyticsService)
    mock_sleep.side_effect = [None, Exception("Stop loop")]

    analytics._broadcast_running = True
    with pytest.raises(Exception, match="Stop loop"):
        await analytics.broadcast_analytics_loop(interval_seconds=1)

    assert mock_analytics_instance.get_all_advanced_analytics.called
    assert mock_manager.emit_advanced_analytics_stats.called


@patch("app.api.v1.endpoints.analytics.asyncio.sleep", new_callable=AsyncMock)
@patch("app.api.v1.endpoints.analytics.get_session_factory")
@patch("app.api.v1.endpoints.analytics.SettingsService")
@patch("app.api.v1.endpoints.analytics.AnalyticsService")
@patch("app.api.v1.endpoints.analytics.logger")
@patch("app.core.connection_manager.manager", new_callable=AsyncMock)
@patch("app.schemas.advanced_analytics.datetime")
async def test_broadcast_analytics_loop_exception_handling(
    mock_datetime,
    mock_manager,
    mock_logger,
    mock_analytics_service_class,
    mock_settings_service_class,
    mock_get_session_factory_param,
    mock_sleep,
    fixed_datetime,
):
    from app.api.v1.endpoints import analytics

    # Configure mocks
    mock_analytics_instance = mock_analytics_service_class.return_value = AsyncMock(spec=AnalyticsService)
    mock_analytics_instance.get_all_advanced_analytics.side_effect = Exception("Service error")
    mock_sleep.side_effect = [None, Exception("Stop loop")]

    analytics._broadcast_running = True
    with pytest.raises(Exception, match="Stop loop"):
        await analytics.broadcast_analytics_loop(interval_seconds=1)

    assert mock_logger.error.called
    assert any("Error in analytics broadcast" in str(args) for args, kwargs in mock_logger.error.call_args_list)
