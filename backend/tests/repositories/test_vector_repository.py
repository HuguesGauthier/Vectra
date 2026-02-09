"""
Tests for VectorRepository.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import PointStruct

from app.core.exceptions import ExternalDependencyError
from app.repositories.vector_repository import VectorRepository


@pytest.fixture
def mock_client():
    return AsyncMock()


@pytest.fixture
def repository(mock_client):
    return VectorRepository(mock_client)


@pytest.mark.asyncio
async def test_upsert_points_success(repository, mock_client):
    # Arrange
    points = [PointStruct(id=1, vector=[0.1] * 1536, payload={})]

    # Act
    await repository.upsert_points("test_col", points)

    # Assert
    mock_client.upsert.assert_awaited_once()


@pytest.mark.asyncio
async def test_upsert_points_failure(repository, mock_client):
    # Arrange
    points = [PointStruct(id=1, vector=[0.1] * 1536, payload={})]
    mock_client.upsert.side_effect = Exception("Connection Refused")

    # Act & Assert
    with pytest.raises(ExternalDependencyError):
        await repository.upsert_points("test_col", points)


@pytest.mark.asyncio
async def test_delete_by_connector_success(repository, mock_client):
    # Arrange
    cid = uuid4()

    # Act
    await repository.delete_by_connector_id("test_col", cid)

    # Assert
    mock_client.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_acl_success(repository, mock_client):
    # Arrange
    cid = uuid4()
    acl = ["group:admin"]

    # Act
    await repository.update_acl("test_col", "connector_id", str(cid), acl)

    # Assert
    mock_client.set_payload.assert_awaited_once()
    # Verify payload structure
    call_kwargs = mock_client.set_payload.call_args[1]
    assert call_kwargs["payload"] == {"connector_acl": acl}
