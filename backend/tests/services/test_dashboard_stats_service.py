import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone
from app.services.dashboard_stats_service import DashboardStatsService
from app.schemas.dashboard_stats import ConnectStats, VectorizeStats, ChatStats

@pytest.fixture
def mock_db():
    return AsyncMock()

@pytest.fixture
def stats_service(mock_db):
    return DashboardStatsService(db=mock_db)

@pytest.mark.asyncio
async def test_get_connect_stats_happy_path(stats_service, mock_db):
    # Setup mock result
    mock_row = MagicMock()
    mock_row.total = 10
    mock_row.active = 5
    mock_row.last_sync = datetime.now(timezone.utc)
    mock_row.error_count = 0
    
    mock_result = MagicMock()
    mock_result.first.return_value = mock_row
    mock_db.execute.return_value = mock_result
    
    stats = await stats_service.get_connect_stats()
    
    assert isinstance(stats, ConnectStats)
    assert stats.total_connectors == 10
    assert stats.active_pipelines == 5
    assert stats.system_status == "ok"

@pytest.mark.asyncio
async def test_get_connect_stats_error_case(stats_service, mock_db):
    mock_db.execute.side_effect = Exception("DB Error")
    
    stats = await stats_service.get_connect_stats()
    
    assert isinstance(stats, ConnectStats)
    # Defaults should be returned on error
    assert stats.total_connectors == 0
    assert stats.system_status == "ok" # Default in ConnectStats? actually it's a pydantic model, check defaults

@pytest.mark.asyncio
async def test_get_vectorize_stats_happy_path(stats_service, mock_db):
    mock_row = MagicMock()
    mock_row.total_vectors = 1000
    mock_row.total_tokens = 50000
    mock_row.total_docs = 100
    mock_row.indexed_docs = 90
    mock_row.failed_docs = 10
    
    mock_result = MagicMock()
    mock_result.first.return_value = mock_row
    mock_db.execute.return_value = mock_result
    
    stats = await stats_service.get_vectorize_stats()
    
    assert stats.total_vectors == 1000
    assert stats.indexing_success_rate == 0.9
    assert stats.failed_docs_count == 10

@pytest.mark.asyncio
async def test_get_chat_stats_happy_path(stats_service, mock_db):
    mock_row = MagicMock()
    mock_row.sessions = 5
    mock_row.avg_ttft = 0.5
    mock_row.total_tokens = 10000
    
    mock_result = MagicMock()
    mock_result.first.return_value = mock_row
    mock_db.execute.return_value = mock_result
    
    stats = await stats_service.get_chat_stats()
    
    assert stats.monthly_sessions == 5
    assert stats.avg_latency_ttft == 0.5
    assert stats.total_tokens_used == 10000
