import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi import FastAPI
import asyncio
from datetime import datetime

from app.api.v1.endpoints.analytics import (
    router, get_analytics_service, start_broadcast_task, stop_broadcast_task,
    broadcast_analytics_loop
)
from app.schemas.advanced_analytics import (
    AdvancedAnalyticsResponse, TTFTPercentiles, TrendingTopic,
    AssistantCost, DocumentFreshness, CacheMetrics, TopicDiversity
)

@pytest.fixture
def mock_service():
    return AsyncMock()

@pytest.fixture
def client(mock_service):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_analytics_service] = lambda: mock_service
    return TestClient(app)

def test_get_advanced_analytics(client, mock_service):
    mock_service.get_all_advanced_analytics.return_value = AdvancedAnalyticsResponse(
        ttft_percentiles=TTFTPercentiles(p50=0.5, p95=1.0, p99=1.5, period_hours=24),
        step_breakdown=[],
        cache_metrics=CacheMetrics(hit_rate=50.0, total_requests=10, cache_hits=5, cache_misses=5, period_hours=24),
        session_distribution=[],
        trending_topics=[],
        topic_diversity=TopicDiversity(total_topics=0, diversity_score=0.0, dominant_topic_share=0.0),
        assistant_costs=[],
        document_utilization=[],
        user_stats=[],
        document_freshness=[],
        reranking_impact=None,
        connector_sync_rates=[],
        generated_at=datetime.utcnow()
    )
    
    response = client.get("/advanced")
    assert response.status_code == 200
    mock_service.get_all_advanced_analytics.assert_called_once()

def test_get_ttft_percentiles(client, mock_service):
    mock_service.get_ttft_percentiles.return_value = TTFTPercentiles(
        p50=0.5, p95=1.0, p99=1.5, period_hours=24
    )
    
    response = client.get("/ttft?hours=24")
    assert response.status_code == 200
    assert response.json()["p50"] == 0.5
    mock_service.get_ttft_percentiles.assert_called_with(24)

def test_get_ttft_percentiles_empty(client, mock_service):
    mock_service.get_ttft_percentiles.return_value = None
    
    response = client.get("/ttft?hours=24")
    assert response.status_code == 200
    assert response.json()["p50"] == 0.0
    
def test_get_trending_topics(client, mock_service):
    mock_service.get_trending_topics.return_value = []
    
    response = client.get("/trending")
    assert response.status_code == 200
    assert response.json() == []
    mock_service.get_trending_topics.assert_called_once()

def test_get_assistant_costs(client, mock_service):
    mock_service.get_assistant_costs.return_value = []
    
    response = client.get("/costs")
    assert response.status_code == 200
    assert response.json() == []
    mock_service.get_assistant_costs.assert_called_once()

def test_get_document_freshness(client, mock_service):
    mock_service.get_document_freshness.return_value = []
    
    response = client.get("/freshness")
    assert response.status_code == 200
    assert response.json() == []
    mock_service.get_document_freshness.assert_called_once()

@pytest.mark.asyncio
async def test_broadcast_tasks():
    # We need to be careful not to actually run the loop for long
    with patch("app.api.v1.endpoints.analytics.broadcast_analytics_loop", return_value=AsyncMock()):
        await start_broadcast_task(interval_seconds=1)
        import app.api.v1.endpoints.analytics as analytics_module
        assert analytics_module._broadcast_task is not None
        
        await stop_broadcast_task()
        assert analytics_module._broadcast_task is None

@pytest.mark.asyncio
async def test_broadcast_analytics_loop_iteration():
    import app.api.v1.endpoints.analytics as analytics_module
    
    mock_manager = AsyncMock()
    mock_stats = MagicMock()
    mock_stats.model_dump.return_value = {}
    
    mock_service = AsyncMock()
    mock_service.get_all_advanced_analytics.return_value = mock_stats
    
    # Mocking dependencies inside the loop
    with patch("app.core.connection_manager.manager", mock_manager), \
         patch("app.api.v1.endpoints.analytics.get_session_factory", MagicMock()), \
         patch("app.api.v1.endpoints.analytics.SettingsService", MagicMock()), \
         patch("app.api.v1.endpoints.analytics.AnalyticsService", MagicMock(return_value=mock_service)), \
         patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        
        # To break the loop after one iteration
        def stop_loop(*args, **kwargs):
            analytics_module._broadcast_running = False
            return AsyncMock() # for sleep if needed
            
        mock_sleep.side_effect = stop_loop
        
        # Set running to true to ensure it runs at least once
        analytics_module._broadcast_running = True
        await broadcast_analytics_loop(interval_seconds=0.1)
        
        mock_manager.emit_advanced_analytics_stats.assert_called_once()

@pytest.mark.asyncio
async def test_broadcast_analytics_loop_error():
    import app.api.v1.endpoints.analytics as analytics_module
    
    with patch("app.api.v1.endpoints.analytics.get_session_factory", side_effect=Exception("Test Error")), \
         patch("asyncio.sleep", AsyncMock()) as mock_sleep:
        
        def stop_loop(*args, **kwargs):
            analytics_module._broadcast_running = False
            
        mock_sleep.side_effect = stop_loop
        
        # Should not raise exception
        analytics_module._broadcast_running = True
        await broadcast_analytics_loop(interval_seconds=0.1)

@pytest.mark.asyncio
async def test_stop_broadcast_task_none():
    import app.api.v1.endpoints.analytics as analytics_module
    analytics_module._broadcast_task = None
    await stop_broadcast_task() # Should return immediately

@pytest.mark.asyncio
async def test_stop_broadcast_task_timeout():
    import app.api.v1.endpoints.analytics as analytics_module
    mock_task = MagicMock(spec=asyncio.Task)
    analytics_module._broadcast_task = mock_task
    
    with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
        await stop_broadcast_task()
        mock_task.cancel.assert_called_once()
        assert analytics_module._broadcast_task is None

@pytest.mark.asyncio
async def test_stop_broadcast_task_error():
    import app.api.v1.endpoints.analytics as analytics_module
    mock_task = MagicMock(spec=asyncio.Task)
    analytics_module._broadcast_task = mock_task
    
    with patch("asyncio.wait_for", side_effect=Exception("Random error")):
        await stop_broadcast_task()
        assert analytics_module._broadcast_task is None

@pytest.mark.asyncio
async def test_start_broadcast_task_already_running():
    import app.api.v1.endpoints.analytics as analytics_module
    mock_task = MagicMock(spec=asyncio.Task)
    mock_task.done.return_value = False
    analytics_module._broadcast_task = mock_task
    
    await start_broadcast_task()
    # Should not create a new task
    assert analytics_module._broadcast_task == mock_task
