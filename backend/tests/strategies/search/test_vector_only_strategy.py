from unittest.mock import MagicMock, patch, AsyncMock
import sys
import pytest
from uuid import uuid4

# Mock dependencies globally for test collection
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

from app.strategies.search.vector_only_strategy import VectorOnlyStrategy
from app.strategies.search.base import SearchFilters, SearchResult, SearchMetadata


@pytest.mark.asyncio
async def test_vector_only_search_happy_path():
    """Happy Path: Standard vector search with valid results."""
    mock_vector_repo = AsyncMock()
    mock_conn_repo = AsyncMock()
    mock_vector_service = AsyncMock()

    mock_vector_service.get_collection_name.return_value = "test_collection"
    mock_model = AsyncMock()
    mock_model.aget_query_embedding.return_value = [0.1] * 768
    mock_vector_service.get_embedding_model.return_value = mock_model

    doc_id = uuid4()
    mock_hit = MagicMock()
    mock_hit.score = 0.9
    mock_hit.payload = {"connector_document_id": str(doc_id), "content": "Cool content"}
    mock_vector_repo.search.return_value = [mock_hit]

    strategy = VectorOnlyStrategy(mock_vector_repo, mock_conn_repo, mock_vector_service)

    results = await strategy.search(query="search for cool stuff")

    assert len(results) == 1
    assert results[0].document_id == doc_id
    assert results[0].score == 0.9
    mock_vector_repo.search.assert_called_once()


@pytest.mark.asyncio
async def test_vector_only_multi_collection():
    """Test searching across multiple collections via assistant."""
    mock_vector_repo = AsyncMock()
    mock_conn_repo = AsyncMock()
    mock_vector_service = AsyncMock()

    # Mock assistant with 2 connectors
    mock_assistant = MagicMock()
    conn1 = MagicMock()
    conn1.configuration = {"ai_provider": "gemini"}
    conn2 = MagicMock()
    conn2.configuration = {"ai_provider": "openai"}
    mock_assistant.linked_connectors = [conn1, conn2]

    mock_vector_service.get_collection_name.side_effect = ["coll_gemini", "coll_openai"]

    mock_model = AsyncMock()
    mock_model.aget_query_embedding.return_value = [0.1]
    mock_vector_service.get_embedding_model.return_value = mock_model

    mock_hit1 = MagicMock()
    mock_hit1.score = 0.95
    mock_hit1.payload = {"connector_document_id": str(uuid4())}

    mock_hit2 = MagicMock()
    mock_hit2.score = 0.85
    mock_hit2.payload = {"connector_document_id": str(uuid4())}

    # Return different results for each collection
    async def side_effect(collection_name, **kwargs):
        if collection_name == "coll_gemini":
            return [mock_hit1]
        return [mock_hit2]

    mock_vector_repo.search.side_effect = side_effect

    strategy = VectorOnlyStrategy(mock_vector_repo, mock_conn_repo, mock_vector_service)

    results = await strategy.search(query="test", filters=SearchFilters(assistant=mock_assistant))

    assert len(results) == 2
    assert results[0].score == 0.95
    assert results[1].score == 0.85
    assert mock_vector_repo.search.call_count == 2


@pytest.mark.asyncio
async def test_vector_only_partial_error():
    """Test that one collection failure doesn't crash the whole search."""
    mock_vector_repo = AsyncMock()
    mock_conn_repo = AsyncMock()
    mock_vector_service = AsyncMock()

    mock_assistant = MagicMock()
    conn1 = MagicMock()
    conn1.configuration = {"ai_provider": "p1"}
    conn2 = MagicMock()
    conn2.configuration = {"ai_provider": "p2"}
    mock_assistant.linked_connectors = [conn1, conn2]

    mock_vector_service.get_collection_name.side_effect = ["c1", "c2"]

    mock_model = AsyncMock()
    mock_model.aget_query_embedding.return_value = [0.1]
    mock_vector_service.get_embedding_model.return_value = mock_model

    mock_hit = MagicMock()
    mock_hit.score = 0.7
    mock_hit.payload = {"connector_document_id": str(uuid4())}

    async def side_effect(collection_name, **kwargs):
        if collection_name == "c1":
            return [mock_hit]
        raise Exception("Serious Bummer")

    mock_vector_repo.search.side_effect = side_effect

    strategy = VectorOnlyStrategy(mock_vector_repo, mock_conn_repo, mock_vector_service)

    results = await strategy.search(query="test", filters=SearchFilters(assistant=mock_assistant))

    assert len(results) == 1
    assert results[0].score == 0.7
    assert mock_vector_repo.search.call_count == 2
