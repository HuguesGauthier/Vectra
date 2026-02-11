from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.trending_service import TrendingService


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def mock_settings_service(mock_db_session):
    ss = MagicMock()
    # Mock return value for get_value
    ss.get_value = AsyncMock(return_value="fake_val")
    return ss


@pytest.fixture
def mock_vector_service(mock_settings_service):
    vs = MagicMock()
    vs.get_qdrant_client = MagicMock()
    vs.get_async_qdrant_client = MagicMock()

    # Mock collections check used in _ensure_collection_exists_sync
    # _ensure_collection_exists_sync calls client.get_collections().collections
    client = vs.get_qdrant_client.return_value
    collections_resp = MagicMock()
    collections_resp.collections = []
    client.get_collections.return_value = collections_resp

    return vs


@pytest.fixture
def service(mock_db_session, mock_repository, mock_vector_service, mock_settings_service):
    return TrendingService(
        db=mock_db_session,
        repository=mock_repository,
        vector_service=mock_vector_service,
        settings_service=mock_settings_service,
    )


@pytest.mark.asyncio
async def test_process_user_question_nominal(service, mock_repository, mock_vector_service):
    """Test nominal question processing (Create New Topic)."""
    # Arrange
    client = mock_vector_service.get_qdrant_client.return_value
    client.search.return_value = []  # No match

    mock_repository.create.return_value = MagicMock(id=uuid4(), created_at=None)

    # Use arguments compliant with process_user_question(question, assistant_id, embedding)
    await service.process_user_question(question="What is Vectra?", assistant_id=uuid4(), embedding=[0.1] * 10)

    mock_repository.create.assert_called_once()
    assert client.upsert.called


@pytest.mark.asyncio
async def test_ensure_collection_invoked(service, mock_vector_service):
    """Test that collection existence check is invoked implicitly."""
    client = mock_vector_service.get_qdrant_client.return_value
    client.search.return_value = []

    await service.process_user_question("Q", uuid4(), [0.1])

    # Check that get_collections was called (part of _ensure_collection_exists_sync)
    client.get_collections.assert_called()


@pytest.mark.asyncio
async def test_trending_service_delete(mock_db_session):
    """Test delete delegation to vector repo."""
    mock_vector_repo = AsyncMock()
    from app.services.trending_service import TrendingService
    service = TrendingService(mock_db_session, vector_repository=mock_vector_repo)

    aid = uuid4()
    await service.delete_assistant_topics(aid)

    mock_vector_repo.delete_by_assistant_id.assert_called_with("trending_topics", aid)
