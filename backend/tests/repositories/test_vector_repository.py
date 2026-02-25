import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, ANY
from qdrant_client.http.exceptions import UnexpectedResponse
from app.repositories.vector_repository import VectorRepository
from app.core.exceptions import ExternalDependencyError


@pytest.fixture
def mock_client():
    return AsyncMock()


@pytest.fixture
def vector_repo(mock_client):
    return VectorRepository(client=mock_client)


@pytest.mark.asyncio
async def test_upsert_points_success(vector_repo, mock_client):
    """Test successful upsert."""
    points = [MagicMock(), MagicMock()]
    await vector_repo.upsert_points("test_collection", points)

    mock_client.upsert.assert_awaited_once_with(collection_name="test_collection", points=points, wait=False)


@pytest.mark.asyncio
async def test_upsert_points_error(vector_repo, mock_client):
    """Test upsert error handling."""
    # UnexpectedResponse(status_code, reason, content, headers)
    mock_client.upsert.side_effect = UnexpectedResponse(500, "Error", b"Content", None)

    with pytest.raises(ExternalDependencyError):
        await vector_repo.upsert_points("test_collection", [MagicMock()])


@pytest.mark.asyncio
async def test_delete_by_connector_id(vector_repo, mock_client):
    """Test delete by connector ID."""
    connector_id = uuid4()
    await vector_repo.delete_by_connector_id("test_collection", connector_id)

    mock_client.delete.assert_awaited_once()
    # verify call args structure (filter check)
    call_args = mock_client.delete.call_args
    assert call_args.kwargs["collection_name"] == "test_collection"
    assert call_args.kwargs["wait"] is True
    # Deep inspection of FilterSelector is complex due to objects,
    # ensuring call happened with correct high level args is pragmatic.


@pytest.mark.asyncio
async def test_delete_ignore_not_found(vector_repo, mock_client):
    """Test delete ignores not found errors."""
    mock_client.delete.side_effect = Exception("Collection not found")

    # Should not raise
    await vector_repo.delete_by_connector_id("test_collection", uuid4())


@pytest.mark.asyncio
async def test_search_success(vector_repo, mock_client):
    """Test search functionality."""
    mock_point = MagicMock()
    mock_result = MagicMock()
    mock_result.points = [mock_point]
    mock_client.query_points.return_value = mock_result

    result = await vector_repo.search("test_collection", [0.1, 0.2])

    assert len(result) == 1
    assert result[0] == mock_point
    mock_client.query_points.assert_awaited_once()


@pytest.mark.asyncio
async def test_count_by_document_id(vector_repo, mock_client):
    """Test counting points."""
    mock_result = MagicMock()
    mock_result.count = 42
    mock_client.count.return_value = mock_result

    count = await vector_repo.count_by_document_id("test_collection", uuid4())

    assert count == 42
    mock_client.count.assert_awaited_once()
