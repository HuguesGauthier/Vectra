"""
Unit tests for VectorOnlyStrategy (Refactored).
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from qdrant_client.http.models import ScoredPoint

from app.strategies.search.base import (SearchExecutionError, SearchFilters,
                                        SearchResult)
from app.strategies.search.vector_only_strategy import VectorOnlyStrategy


@pytest.fixture
def mock_deps():
    return {
        "vector_repo": AsyncMock(),
        "connector_repo": AsyncMock(),
        "vector_service": AsyncMock(),
    }


@pytest.fixture
def strategy(mock_deps):
    return VectorOnlyStrategy(**mock_deps)


@pytest.mark.asyncio
async def test_search_nominal_flow(strategy, mock_deps):
    """✅ SUCCESS: Nominal search flow with vectorization and Qdrant retrieval."""
    # Mocks
    query = "test vector"
    cid = uuid4()
    mock_deps["connector_repo"].get_by_id.return_value = MagicMock(configuration={"ai_provider": "openai"})
    mock_deps["vector_service"].get_collection_name.return_value = "vectra_vectors"

    # Mock Embedding
    mock_embed_model = AsyncMock()
    mock_embed_model.aget_query_embedding.return_value = [0.1, 0.2, 0.3]
    mock_deps["vector_service"].get_embedding_model.return_value = mock_embed_model

    # Mock Qdrant result
    mock_hit = MagicMock(spec=ScoredPoint)
    mock_hit.id = str(uuid4())
    mock_hit.score = 0.95
    mock_hit.payload = {"connector_document_id": str(uuid4()), "content": "test content", "file_name": "test.pdf"}
    mock_deps["vector_repo"].client.search.return_value = [mock_hit]

    # Execute filters with connector context
    filters = SearchFilters(connector_id=cid)
    results = await strategy.search(query, top_k=5, filters=filters)

    # Assertions
    assert len(results) == 1
    assert results[0].content == "test content"
    assert results[0].metadata.file_name == "test.pdf"

    # Verify calls
    mock_deps["vector_service"].get_embedding_model.assert_awaited_once()
    mock_embed_model.aget_query_embedding.assert_awaited_once_with(query)
    mock_deps["vector_repo"].client.search.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_missing_connector(strategy, mock_deps):
    """❌ FAILURE: Search fails gracefully on missing connector in DB (when ID passed)."""
    cid = uuid4()
    mock_deps["connector_repo"].get_by_id.return_value = None  # Not found

    filters = SearchFilters(connector_id=cid)

    with pytest.raises(SearchExecutionError) as exc:
        await strategy.search("query", filters=filters)
    assert "not found" in str(exc.value)


@pytest.mark.asyncio
async def test_search_no_connector_fallback(strategy, mock_deps):
    """✅ SUCCESS: Search falls back to default if no connector ID passed."""
    mock_deps["vector_service"].get_collection_name.return_value = "vectra_vectors"

    # Mock Embed
    mock_embed_model = AsyncMock()
    mock_embed_model.aget_query_embedding.return_value = [0.1]
    mock_deps["vector_service"].get_embedding_model.return_value = mock_embed_model

    mock_deps["vector_repo"].client.search.return_value = []

    # No filters
    results = await strategy.search("query", filters=None)
    assert results == []

    # Verify we requested default collection info
    mock_deps["vector_service"].get_collection_name.assert_awaited_with(provider="openai")
