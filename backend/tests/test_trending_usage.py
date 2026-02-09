from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.usage_stat import UsageStat
from app.repositories.usage_repository import UsageRepository
from app.services.trending_service import TrendingService


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.mark.asyncio
async def test_usage_repository_daily(mock_db):
    """Test get_daily_usage SQL construction and execution."""
    repo = UsageRepository(mock_db)

    # Create a synchronous Mock for the Result object
    mock_result = MagicMock()
    mock_result.all.return_value = [MagicMock(date="2023-01-01", count=10, total_tokens=100, avg_duration=5.0)]
    # Ensure await db.execute() returns this synchronous mock
    mock_db.execute.return_value = mock_result

    result = await repo.get_daily_usage(uuid4(), days=7)

    assert len(result) == 1
    assert result[0]["count"] == 10
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_trending_service_process_no_match(mock_db):
    """Test ingestion when no match is found (create new topic)."""
    # Mock Dependencies
    mock_repo = AsyncMock()
    mock_settings = AsyncMock()
    mock_vector = AsyncMock()
    mock_vector_repo = AsyncMock()

    # Setup Qdrant response (Empty)
    mock_client = AsyncMock()
    mock_vector.get_async_qdrant_client.return_value = mock_client
    mock_client.query_points.return_value.points = []

    service = TrendingService(
        db=mock_db,
        repository=mock_repo,
        vector_service=mock_vector,
        settings_service=mock_settings,
        vector_repository=mock_vector_repo,
    )

    question = "How to optimize Python?"
    embedding = [0.1] * 768

    # Mock Repository Create
    mock_topic = MagicMock()
    mock_topic.id = uuid4()
    mock_topic.created_at = datetime.now(timezone.utc)
    mock_repo.create.return_value = mock_topic

    await service.process_user_question(question, uuid4(), embedding)

    # Verifications
    mock_vector.ensure_collection_exists.assert_called_once()
    mock_repo.create.assert_called_once()  # Should create topic
    mock_vector_repo.upsert_points.assert_called_once()  # Should upsert to Qdrant


@pytest.mark.asyncio
async def test_trending_service_delete(mock_db):
    """Test delete delegation to vector repo."""
    mock_vector_repo = AsyncMock()
    service = TrendingService(mock_db, vector_repository=mock_vector_repo)

    aid = uuid4()
    await service.delete_assistant_topics(aid)

    mock_vector_repo.delete_by_assistant_id.assert_called_with("trending_topics", aid)


if __name__ == "__main__":
    import asyncio

    asyncio.run(test_usage_repository_daily(AsyncMock()))
    asyncio.run(test_trending_service_process_no_match(AsyncMock()))
    asyncio.run(test_trending_service_delete(AsyncMock()))
    print("Manual Test Run Passed")
