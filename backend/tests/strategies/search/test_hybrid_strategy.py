"""
Unit tests for HybridStrategy (Refactored).
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from qdrant_client.http.models import ScoredPoint

from app.strategies.search.base import (SearchExecutionError, SearchFilters,
                                        SearchResult)
from app.strategies.search.hybrid_strategy import HybridStrategy


@pytest.fixture
def mock_deps():
    return {
        "vector_repo": AsyncMock(),
        "document_repo": AsyncMock(),
        "connector_repo": AsyncMock(),
        "vector_service": AsyncMock(),
    }


@pytest.fixture
def strategy(mock_deps):
    return HybridStrategy(**mock_deps)


@pytest.mark.asyncio
async def test_search_nominal_flow(strategy, mock_deps):
    """✅ SUCCESS: Nominal search flow with vectorization and Qdrant retrieval."""
    # Mocks
    query = "test query"
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
    mock_hit.payload = {"connector_document_id": str(uuid4()), "_node_content": "test content", "file_name": "test.pdf"}
    # FIXED: Use vector_repo.search instead of client.search
    mock_deps["vector_repo"].search.return_value = [mock_hit]

    # Execute
    filters = SearchFilters(connector_id=cid)
    results = await strategy.search(query, top_k=5, filters=filters)

    # Assertions
    assert len(results) == 1
    assert results[0].content == "test content"
    assert results[0].metadata.file_name == "test.pdf"

    # Verify calls
    mock_deps["vector_service"].get_embedding_model.assert_awaited()
    mock_embed_model.aget_query_embedding.assert_awaited_with(query)
    mock_deps["vector_repo"].search.assert_awaited()


@pytest.mark.asyncio
async def test_search_missing_connector(strategy, mock_deps):
    """❌ FAILURE: Search fails gracefully on missing connector."""
    cid = uuid4()
    mock_deps["connector_repo"].get_by_id.return_value = None  # Not found

    filters = SearchFilters(connector_id=cid)

    with pytest.raises(SearchExecutionError) as exc:
        await strategy.search("query", filters=filters)
    assert "not found" in str(exc.value)


@pytest.mark.asyncio
async def test_search_qdrant_failure(strategy, mock_deps):
    """❌ FAILURE: Strategy handles Qdrant failure gracefully (multi-collection behavior)."""
    mock_deps["connector_repo"].get_by_id.return_value = MagicMock(configuration={"ai_provider": "openai"})
    mock_deps["vector_service"].get_collection_name.return_value = "vectra_vectors"

    mock_embed_model = AsyncMock()
    mock_embed_model.aget_query_embedding.return_value = [0.1]
    mock_deps["vector_service"].get_embedding_model.return_value = mock_embed_model

    # Qdrant fails
    mock_deps["vector_repo"].search.side_effect = Exception("Qdrant Down")

    filters = SearchFilters(connector_id=uuid4())

    # With multi-collection support, single collection failures are handled gracefully
    # No exception is raised, but empty results are returned
    results = await strategy.search("query", filters=filters)
    assert len(results) == 0  # Graceful degradation
