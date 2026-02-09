import sys
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta
from uuid import uuid4

# Pre-mock problematic external dependencies
sys.modules['llama_index'] = MagicMock()
sys.modules['llama_index.llms'] = MagicMock()
sys.modules['llama_index.llms.mistralai'] = MagicMock()
sys.modules['llama_index.llms.openai'] = MagicMock()
sys.modules['llama_index.llms.gemini'] = MagicMock()
sys.modules['llama_index.embeddings'] = MagicMock()
sys.modules['llama_index.core'] = MagicMock()

# Pre-mock internal modules
mock_analytics_repo = MagicMock()
mock_doc_repo = MagicMock()
mock_settings_service = MagicMock()
mock_db = MagicMock()

sys.modules['app.repositories.analytics_repository'] = mock_analytics_repo
sys.modules['app.repositories.document_repository'] = mock_doc_repo
sys.modules['app.services.settings_service'] = mock_settings_service
sys.modules['app.core.database'] = mock_db
sys.modules['app.core.settings'] = MagicMock()
sys.modules['app.services.assistant_service'] = MagicMock()
sys.modules['app.services.chat_service'] = MagicMock()
sys.modules['app.services.auth_service'] = MagicMock()
sys.modules['app.services.user_service'] = MagicMock()

import pytest

# Mock classes
mock_analytics_repo.AnalyticsRepository = MagicMock
mock_doc_repo.DocumentRepository = MagicMock
mock_settings_service.SettingsService = MagicMock
mock_settings_service.get_settings_service = MagicMock

from app.services.analytics_service import AnalyticsService, get_analytics_service
from app.schemas.analytics import AnalyticsResponse

@pytest.fixture
def mock_deps():
    session_factory = MagicMock()
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    session_factory.return_value = mock_session
    
    settings_service = AsyncMock()
    return session_factory, settings_service, mock_session

@pytest.mark.asyncio
async def test_get_business_metrics(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    mock_doc_repo_inst = AsyncMock()
    mock_doc_repo_inst.get_aggregate_stats.return_value = {
        "total_tokens": 10000,
        "total_docs": 100,
        "total_vectors": 500
    }
    monkeypatch.setattr("app.services.analytics_service.DocumentRepository", MagicMock(return_value=mock_doc_repo_inst))
    
    settings_service.get_value.side_effect = ["0.0001", "5.0"]
    
    result = await service.get_business_metrics()
    assert result.total_docs == 100
    assert result.total_tokens == 10000
    assert result.estimated_cost == 0.001
    assert result.time_saved_hours == 8.3

@pytest.mark.asyncio
async def test_get_business_metrics_error(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    monkeypatch.setattr("app.services.analytics_service.DocumentRepository", MagicMock(side_effect=Exception("DB Error")))
    
    result = await service.get_business_metrics()
    assert isinstance(result, AnalyticsResponse)
    assert result.total_docs == 0

@pytest.mark.asyncio
async def test_get_all_advanced_analytics(mock_deps):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    for method in [
        "get_ttft_percentiles", "get_step_breakdown", "get_cache_metrics",
        "get_trending_topics", "get_topic_diversity", "get_assistant_costs",
        "get_document_freshness", "get_session_distribution",
        "get_document_utilization", "get_reranking_impact",
        "get_connector_sync_rates", "get_user_stats"
    ]:
        default_val = [] if any(x in method for x in ["list", "breakdown", "topics", "costs", "freshness", "distribution", "utilization", "rates", "stats"]) else None
        setattr(service, method, AsyncMock(return_value=default_val))

    result = await service.get_all_advanced_analytics()
    assert result is not None

@pytest.mark.asyncio
async def test_ttft_percentiles(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    mock_repo = AsyncMock()
    mock_repo.get_ttft_percentiles.return_value = {"p50": 1.0, "p90": 2.0, "p95": 3.0, "p99": 4.0}
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))
    
    result = await service.get_ttft_percentiles(24)
    assert result.p50 == 1.0

@pytest.mark.asyncio
async def test_get_step_breakdown(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    mock_repo = AsyncMock()
    row = MagicMock()
    row.step_name = "test"
    row.avg_duration = 0.5
    row.step_count = 10
    row.avg_input_tokens = 100
    row.avg_output_tokens = 50
    mock_repo.get_step_breakdown.return_value = [row]
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))
    
    result = await service.get_step_breakdown(7)
    assert len(result) == 1
    assert result[0].avg_tokens["input"] == 100

@pytest.mark.asyncio
async def test_get_cache_metrics(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    mock_repo = AsyncMock()
    row = MagicMock()
    row.total_requests = 100
    row.cache_hits = 80
    mock_repo.get_cache_stats.return_value = row
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))
    
    result = await service.get_cache_metrics(24)
    assert result.hit_rate == 80.0
    
    # Test no data
    mock_repo.get_cache_stats.return_value = None
    result = await service.get_cache_metrics(24)
    assert result is None

@pytest.mark.asyncio
async def test_get_trending_topics(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    mock_repo = AsyncMock()
    topic = MagicMock()
    topic.canonical_text = "topic1"
    topic.frequency = 5
    topic.raw_variations = ["v1", "v2"]
    topic.updated_at = datetime.now(timezone.utc)
    mock_repo.get_trending_topics.return_value = [topic]
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))
    
    result = await service.get_trending_topics(None, 10)
    assert len(result) == 1

@pytest.mark.asyncio
async def test_get_topic_diversity(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    mock_repo = AsyncMock()
    mock_repo.get_topic_frequencies.return_value = [(10,), (5,), (5,)]
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))
    
    result = await service.get_topic_diversity(None)
    assert result.total_topics == 3
    
    # Test no topics
    mock_repo.get_topic_frequencies.return_value = []
    result = await service.get_topic_diversity(None)
    assert result is None
    
    # Test 0 total topics
    mock_repo.get_topic_frequencies.return_value = [(0,)]
    result = await service.get_topic_diversity(None)
    assert result is None

@pytest.mark.asyncio
async def test_get_assistant_costs(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    mock_repo = AsyncMock()
    row = MagicMock()
    row.id = uuid4()
    row.name = "Assistant 1"
    row.input_tokens = 1000
    row.output_tokens = 500
    row.total_tokens = 1500
    mock_repo.get_assistant_usage_sums.return_value = [row]
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))
    
    result = await service.get_assistant_costs(24)
    assert len(result) == 1

@pytest.mark.asyncio
async def test_get_document_freshness(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    mock_repo = AsyncMock()
    row = MagicMock()
    row.freshness_category = "Fresh"
    row.doc_count = 50
    mock_repo.get_document_freshness_stats.return_value = [row]
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))
    
    result = await service.get_document_freshness()
    assert result[0].percentage == 100.0
    
    # Test no docs
    mock_repo.get_document_freshness_stats.return_value = []
    result = await service.get_document_freshness()
    assert result == []

@pytest.mark.asyncio
async def test_get_session_distribution(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    mock_repo = AsyncMock()
    r1 = MagicMock(); r1.q_count = 1
    r2 = MagicMock(); r2.q_count = 3
    r3 = MagicMock(); r3.q_count = 10
    mock_repo.get_session_counts.return_value = [r1, r2, r3]
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))
    
    result = await service.get_session_distribution(7)
    assert len(result) == 3
    
    # Test no sessions
    mock_repo.get_session_counts.return_value = []
    result = await service.get_session_distribution(7)
    assert result == []

@pytest.mark.asyncio
async def test_get_document_utilization(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    mock_repo = AsyncMock()
    # Hot
    row_hot = MagicMock(); row_hot.doc_id = uuid4(); row_hot.retrieval_count = 15
    # Warm
    row_warm = MagicMock(); row_warm.doc_id = uuid4(); row_warm.retrieval_count = 5
    # Cold
    row_cold = MagicMock(); row_cold.doc_id = uuid4(); row_cold.retrieval_count = 0
    
    mock_repo.get_document_retrieval_stats.return_value = [row_hot, row_warm, row_cold]
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))
    
    result = await service.get_document_utilization(30)
    assert result[0].status == "hot"
    assert result[1].status == "warm"
    assert result[2].status == "cold"

@pytest.mark.asyncio
async def test_get_reranking_impact(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    mock_repo = AsyncMock()
    row = MagicMock()
    row.avg_improvement = 0.2
    row.reranking_count = 100
    mock_repo.get_reranking_stats.return_value = row
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))
    
    result = await service.get_reranking_impact(24)
    assert result.avg_score_improvement == 0.2
    
    # Test None or 0 count
    mock_repo.get_reranking_stats.return_value = None
    result = await service.get_reranking_impact(24)
    assert result is None
    
    row.reranking_count = 0
    mock_repo.get_reranking_stats.return_value = row
    result = await service.get_reranking_impact(24)
    assert result is None

@pytest.mark.asyncio
async def test_get_connector_sync_rates(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    mock_repo = AsyncMock()
    row = MagicMock()
    row.id = uuid4()
    row.name = "Connector 1"
    row.total_syncs = 10
    row.successful_syncs = 9
    row.failed_syncs = 1
    row.avg_duration = 120.0
    mock_repo.get_connector_sync_stats.return_value = [row]
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))
    
    result = await service.get_connector_sync_rates(7)
    assert len(result) == 1
    assert result[0].success_rate == 90.0

@pytest.mark.asyncio
async def test_get_user_stats(mock_deps, monkeypatch):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    mock_repo = AsyncMock()
    row = MagicMock()
    row.user_id = uuid4()
    row.email = "test@example.com"
    row.first_name = "Test"
    row.last_name = "User"
    row.total_tokens = 5000
    row.interaction_count = 20
    row.last_active = datetime.now(timezone.utc)
    mock_repo.get_user_usage_stats.return_value = [row]
    monkeypatch.setattr("app.services.analytics_service.AnalyticsRepository", MagicMock(return_value=mock_repo))
    
    result = await service.get_user_stats(30)
    assert len(result) == 1
    assert result[0].full_name == "Test User"
    
    # Test only email
    row.first_name = None; row.last_name = None
    result = await service.get_user_stats(30)
    assert result[0].full_name == "test@example.com"

@pytest.mark.asyncio
async def test_safe_result_with_exception(mock_deps):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    result = service._safe_result(Exception("Error"), [])
    assert result == []

@pytest.mark.asyncio
async def test_fetch_business_settings_error(mock_deps):
    session_factory, settings_service, mock_session = mock_deps
    service = AnalyticsService(session_factory, settings_service)
    
    settings_service.get_value.side_effect = ["invalid", "5.0"]
    cost, saved = await service._fetch_business_settings()
    assert cost == 0.0001 # Default
    assert saved == 5.0

def test_get_analytics_service():
    session_factory = MagicMock()
    settings_service = MagicMock()
    service = get_analytics_service(session_factory, settings_service)
    assert isinstance(service, AnalyticsService)
