from unittest.mock import MagicMock, patch, AsyncMock
import sys
import pytest
from uuid import uuid4

# Mock dependencies globally for test collection
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

from app.strategies.search.hybrid_strategy import HybridStrategy
from app.strategies.search.base import SearchFilters, SearchResult, SearchMetadata, SearchExecutionError


@pytest.mark.asyncio
async def test_hybrid_search_happy_path():
    """Happy Path: Standard hybrid search with valid results."""
    # Mocks
    mock_vector_repo = AsyncMock()
    mock_doc_repo = AsyncMock()
    mock_conn_repo = AsyncMock()
    mock_vector_service = AsyncMock()

    # Mocking single collection resolution
    mock_vector_service.get_collection_name.return_value = "test_collection"

    # Mocking embedding
    mock_model = AsyncMock()
    mock_model.aget_query_embedding.return_value = [0.1] * 768
    mock_vector_service.get_embedding_model.return_value = mock_model

    # Mocking vector results
    doc_id = uuid4()
    mock_hit = MagicMock()
    mock_hit.score = 0.9
    mock_hit.payload = {"connector_document_id": str(doc_id), "content": "Relevant content"}
    mock_vector_repo.search.return_value = [mock_hit]

    # Mocking SQL doc check
    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.status = "INDEXED"
    mock_doc_repo.get_by_ids.return_value = [mock_doc]

    strategy = HybridStrategy(
        vector_repo=mock_vector_repo,
        document_repo=mock_doc_repo,
        connector_repo=mock_conn_repo,
        vector_service=mock_vector_service,
    )

    results = await strategy.search(query="test query")

    assert len(results) == 1
    assert results[0].document_id == doc_id
    assert results[0].score == 0.9
    mock_vector_repo.search.assert_called_once()
    mock_doc_repo.get_by_ids.assert_called_once()


@pytest.mark.asyncio
async def test_hybrid_search_sql_status_filtering():
    """Worst Case: Document exists in Vector DB but is NOT INDEXED in SQL."""
    mock_vector_repo = AsyncMock()
    mock_doc_repo = AsyncMock()
    mock_conn_repo = AsyncMock()
    mock_vector_service = AsyncMock()

    mock_vector_service.get_collection_name.return_value = "test_collection"
    mock_model = AsyncMock()
    mock_model.aget_query_embedding.return_value = [0.1] * 768
    mock_vector_service.get_embedding_model.return_value = mock_model

    doc_id = uuid4()
    mock_hit = MagicMock()
    mock_hit.score = 0.9
    mock_hit.payload = {"connector_document_id": str(doc_id)}
    mock_vector_repo.search.return_value = [mock_hit]

    # SQL doc is in PENDING state (maybe was re-indexed or deleted)
    mock_doc = MagicMock()
    mock_doc.id = doc_id
    mock_doc.status = "PENDING"
    mock_doc_repo.get_by_ids.return_value = [mock_doc]

    strategy = HybridStrategy(mock_vector_repo, mock_doc_repo, mock_conn_repo, mock_vector_service)

    results = await strategy.search(query="test", filters=SearchFilters())  # status filter empty but we enforce INDEXED

    # Should be empty because status is not INDEXED
    assert len(results) == 0


@pytest.mark.asyncio
async def test_hybrid_search_partial_failure():
    """Worst Case: One collection fails but others succeed."""
    mock_vector_repo = AsyncMock()
    mock_doc_repo = AsyncMock()
    mock_conn_repo = AsyncMock()
    mock_vector_service = AsyncMock()

    # Multiple collections
    mock_vector_service.get_collection_name.side_effect = ["coll1", "coll2"]

    mock_assistant = MagicMock()
    conn1 = MagicMock()
    conn1.configuration = {"ai_provider": "p1"}
    conn2 = MagicMock()
    conn2.configuration = {"ai_provider": "p2"}
    mock_assistant.linked_connectors = [conn1, conn2]

    # Collection 1 succeeds, Collection 2 fails
    mock_model = AsyncMock()
    mock_model.aget_query_embedding.return_value = [0.1]
    mock_vector_service.get_embedding_model.return_value = mock_model

    doc1_id = uuid4()
    mock_hit = MagicMock()
    mock_hit.score = 0.8
    mock_hit.payload = {"connector_document_id": str(doc1_id)}

    async def side_effect(collection_name, **kwargs):
        if collection_name == "coll1":
            return [mock_hit]
        raise Exception("Vector DB error")

    mock_vector_repo.search.side_effect = side_effect

    # SQL check
    mock_doc = MagicMock()
    mock_doc.id = doc1_id
    mock_doc.status = "INDEXED"
    mock_doc_repo.get_by_ids.return_value = [mock_doc]

    strategy = HybridStrategy(mock_vector_repo, mock_doc_repo, mock_conn_repo, mock_vector_service)

    results = await strategy.search(query="test", filters=SearchFilters(assistant=mock_assistant))

    assert len(results) == 1  # coll1 results only
    assert results[0].document_id == doc1_id
