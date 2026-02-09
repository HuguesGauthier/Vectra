import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import ExternalDependencyError
from app.repositories.vector_repository import VectorRepository
from app.services.vector_service import VectorService


# Mock SettingsService
class MockSettingsService:
    async def get_value(self, key):
        defaults = {
            "embedding_provider": "gemini",
            "gemini_api_key": "fake_key",
            "gemini_embedding_model": "models/text-embedding-004",
            "openai_api_key": "fake_openai_key",
            "QDRANT_HOST": "localhost",
            "QDRANT_API_KEY": None,
        }
        return defaults.get(key)


@pytest.fixture
def mock_settings_service():
    return MockSettingsService()


@pytest.fixture
def mock_env_settings():
    with patch("app.services.vector_service.get_settings") as mock_get:
        mock_settings = MagicMock()
        mock_settings.QDRANT_HOST = "localhost"
        mock_settings.QDRANT_API_KEY = None
        mock_get.return_value = mock_settings
        yield mock_settings


@pytest.mark.asyncio
async def test_vector_service_client_singleton(mock_settings_service, mock_env_settings):
    """
    Test that VectorService correctly manages Qdrant client singleton
    and respects prefer_grpc=False.
    """
    with patch("qdrant_client.AsyncQdrantClient") as MockQdrant:
        # Define side_effect or return_value if needed
        mock_client_instance = AsyncMock()
        MockQdrant.return_value = mock_client_instance

        service = VectorService(mock_settings_service)

        # 1. First Call - Should create client
        client1 = service.get_async_qdrant_client()

        # Verify call args
        MockQdrant.assert_called_with(
            host="localhost", port=6333, https=False, api_key=None, timeout=5.0, prefer_grpc=False  # CRITICAL P0 Check
        )

        # 2. Second Call - Should return same instance
        client2 = service.get_async_qdrant_client()
        assert client1 is client2
        assert MockQdrant.call_count == 1  # Singleton verified


@pytest.mark.asyncio
async def test_vector_repository_delete(mock_settings_service):
    """
    Test VectorRepository delete_by_assistant_id robustness.
    """
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


if __name__ == "__main__":
    # verification run
    asyncio.run(test_vector_service_client_singleton(MockSettingsService()))
    print("Tests passed manually")
