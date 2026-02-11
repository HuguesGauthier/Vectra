from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from app.core.exceptions import ExternalDependencyError
from app.repositories.vector_repository import VectorRepository

@pytest.mark.asyncio
async def test_vector_repository_delete():
    """Test VectorRepository delete_by_assistant_id robustness."""
    mock_client = AsyncMock()
    repo = VectorRepository(mock_client)
    assistant_id = uuid4()

    # Success Case
    await repo.delete_by_assistant_id("test_collection", assistant_id)
    mock_client.delete.assert_called_once()

    # Failure Case (Protocol Error)
    mock_client.delete.side_effect = Exception("Connection Refused")
    with pytest.raises(ExternalDependencyError):
        await repo.delete_by_assistant_id("test_collection", assistant_id)
