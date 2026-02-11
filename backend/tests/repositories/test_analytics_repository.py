import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.exc import SQLAlchemyError
from app.repositories.analytics_repository import AnalyticsRepository


@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def analytics_repo(mock_db):
    """Create an AnalyticsRepository instance with mock db."""
    return AnalyticsRepository(db=mock_db)


@pytest.mark.asyncio
async def test_get_ttft_percentiles_success(analytics_repo, mock_db):
    """Test TTFT percentiles calculation with valid data."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    # Mock result
    mock_row = MagicMock()
    mock_row.p50 = 1.5
    mock_row.p95 = 3.2
    mock_row.p99 = 5.1

    mock_result = MagicMock()
    mock_result.first.return_value = mock_row
    mock_db.execute.return_value = mock_result

    result = await analytics_repo.get_ttft_percentiles(cutoff)

    assert result is not None
    assert result["p50"] == 1.5
    assert result["p95"] == 3.2
    assert result["p99"] == 5.1


@pytest.mark.asyncio
async def test_get_ttft_percentiles_no_data(analytics_repo, mock_db):
    """Test TTFT percentiles with no data."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_db.execute.return_value = mock_result

    result = await analytics_repo.get_ttft_percentiles(cutoff)

    assert result is None


@pytest.mark.asyncio
async def test_get_ttft_percentiles_error_handling(analytics_repo, mock_db):
    """Test TTFT percentiles error handling."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    mock_db.execute.side_effect = SQLAlchemyError("Database error")

    result = await analytics_repo.get_ttft_percentiles(cutoff)

    assert result is None


@pytest.mark.asyncio
async def test_get_step_breakdown_success(analytics_repo, mock_db):
    """Test step breakdown query."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    mock_rows = [
        MagicMock(step_name="retrieval", avg_duration=0.5, step_count=100),
        MagicMock(step_name="generation", avg_duration=1.2, step_count=100),
    ]

    mock_result = MagicMock()
    mock_result.all.return_value = mock_rows
    mock_db.execute.return_value = mock_result

    result = await analytics_repo.get_step_breakdown(cutoff)

    assert len(result) == 2
    assert result[0].step_name == "retrieval"


@pytest.mark.asyncio
async def test_get_step_breakdown_error_handling(analytics_repo, mock_db):
    """Test step breakdown error handling."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    mock_db.execute.side_effect = SQLAlchemyError("Database error")

    result = await analytics_repo.get_step_breakdown(cutoff)

    assert result == []


@pytest.mark.asyncio
async def test_get_cache_stats_success(analytics_repo, mock_db):
    """Test cache stats retrieval."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    mock_row = MagicMock()
    mock_row.cache_hits = 50
    mock_row.total_requests = 100

    mock_result = MagicMock()
    mock_result.first.return_value = mock_row
    mock_db.execute.return_value = mock_result

    result = await analytics_repo.get_cache_stats(cutoff)

    assert result is not None
    assert result.cache_hits == 50
    assert result.total_requests == 100


@pytest.mark.asyncio
async def test_get_cache_stats_error_handling(analytics_repo, mock_db):
    """Test cache stats error handling."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    mock_db.execute.side_effect = SQLAlchemyError("Database error")

    result = await analytics_repo.get_cache_stats(cutoff)

    assert result is None


@pytest.mark.asyncio
async def test_get_trending_topics_success(analytics_repo, mock_db):
    """Test trending topics query."""
    limit = 10
    assistant_id = uuid4()

    mock_topics = [MagicMock(), MagicMock()]

    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_topics
    mock_result.scalars.return_value = mock_scalars
    mock_db.execute.return_value = mock_result

    result = await analytics_repo.get_trending_topics(limit, assistant_id)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_trending_topics_error_handling(analytics_repo, mock_db):
    """Test trending topics error handling."""
    limit = 10

    mock_db.execute.side_effect = SQLAlchemyError("Database error")

    result = await analytics_repo.get_trending_topics(limit)

    assert result == []


@pytest.mark.asyncio
async def test_get_assistant_usage_sums_success(analytics_repo, mock_db):
    """Test assistant usage sums query."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    mock_rows = [
        MagicMock(id=uuid4(), name="Assistant 1", input_tokens=1000, output_tokens=500, total_tokens=1500),
    ]

    mock_result = MagicMock()
    mock_result.all.return_value = mock_rows
    mock_db.execute.return_value = mock_result

    result = await analytics_repo.get_assistant_usage_sums(cutoff)

    assert len(result) == 1
    assert result[0].total_tokens == 1500


@pytest.mark.asyncio
async def test_get_document_retrieval_stats_success(analytics_repo, mock_db):
    """Test document retrieval stats query."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    limit = 50

    mock_rows = [
        MagicMock(file_name="doc1.pdf", connector_name="Connector 1", retrieval_count=10),
    ]

    mock_result = MagicMock()
    mock_result.all.return_value = mock_rows
    mock_db.execute.return_value = mock_result

    result = await analytics_repo.get_document_retrieval_stats(cutoff, limit)

    assert len(result) == 1
    assert result[0].file_name == "doc1.pdf"


@pytest.mark.asyncio
async def test_get_session_counts_success(analytics_repo, mock_db):
    """Test session counts query."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    mock_rows = [
        MagicMock(session_id=uuid4(), q_count=5),
    ]

    mock_result = MagicMock()
    mock_result.all.return_value = mock_rows
    mock_db.execute.return_value = mock_result

    result = await analytics_repo.get_session_counts(cutoff)

    assert len(result) == 1
    assert result[0].q_count == 5
