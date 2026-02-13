import sys
from unittest.mock import ANY, AsyncMock, MagicMock, patch

# Pragmatic Mock for pyodbc and vanna to avoid collection errors in environments without native drivers
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

import pytest

from app.core.exceptions import ExternalDependencyError, TechnicalError
from app.services.vector_service import VectorService


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_settings_service(mock_db):
    ss = MagicMock()
    ss.db = mock_db
    # Default mock values
    ss.get_value = AsyncMock(return_value="fake_val")
    return ss


@pytest.fixture
def mock_qdrant_module():
    with patch("app.services.vector_service.qdrant_client") as qc:
        # Mock the instances returned by constructors
        qc.QdrantClient.return_value = MagicMock()
        qc.AsyncQdrantClient.return_value = AsyncMock()
        yield qc


class TestVectorService:

    def setup_method(self):
        # Reset shared client storage for clean testing
        VectorService._client = None
        VectorService._aclient = None

    @pytest.mark.asyncio
    async def test_singleton_logic(self, mock_settings_service, mock_qdrant_module):
        """Test that qdrant client is stored at class level but accessible via instance."""
        s1 = VectorService(mock_settings_service)
        s2 = VectorService(mock_settings_service)

        # First call
        client1 = await s1.get_qdrant_client()
        assert mock_qdrant_module.QdrantClient.called

        # Reset mock to verify it's NOT called again
        mock_qdrant_module.QdrantClient.reset_mock()

        # Second call on DIFFERENT instance
        client2 = await s2.get_qdrant_client()
        assert not mock_qdrant_module.QdrantClient.called
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_get_qdrant_client_config(self, mock_settings_service, mock_qdrant_module):
        """Test client configuration parameters (timeout, grpc=False)."""
        service = VectorService(mock_settings_service)
        await service.get_qdrant_client()

        mock_qdrant_module.QdrantClient.assert_called_with(
            host=ANY,
            port=ANY,
            https=ANY,
            api_key=ANY,
            timeout=ANY,
            prefer_grpc=False,
        )

    @pytest.mark.asyncio
    async def test_ensure_collection_exists_skips_if_present(self, mock_settings_service, mock_qdrant_module):
        """Verify that we don't try to create if collection exists."""
        service = VectorService(mock_settings_service)
        mock_aclient = await service.get_async_qdrant_client()
        mock_aclient.collection_exists = AsyncMock(return_value=True)
        # Explicitly mock create_collection as AsyncMock to avoid 'function' object AttributeError
        mock_aclient.create_collection = AsyncMock()

        await service.ensure_collection_exists("test_col", "gemini")

        mock_aclient.create_collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_ensure_collection_exists_creates_if_missing(self, mock_settings_service, mock_qdrant_module):
        """Verify that we create collection with correct dimension if missing."""
        service = VectorService(mock_settings_service)
        mock_aclient = await service.get_async_qdrant_client()
        mock_aclient.collection_exists = AsyncMock(return_value=False)
        mock_aclient.create_collection = AsyncMock()

        await service.ensure_collection_exists("test_col", "openai")

        # OpenAI = 1536
        mock_aclient.create_collection.assert_awaited_once()
        args = mock_aclient.create_collection.call_args[1]
        assert args["collection_name"] == "test_col"
        assert args["vectors_config"].size == 1536

    @pytest.mark.asyncio
    async def test_get_embedding_model_gemini(self, mock_settings_service):
        """Test Gemini embedding model creation via factory."""
        service = VectorService(mock_settings_service)

        async def mock_get_value(key, default=None):
            return {
                "embedding_provider": "gemini",
                "gemini_embedding_model": "models/embedding-001",
            }.get(key, default)

        mock_settings_service.get_value.side_effect = mock_get_value

        with patch("app.factories.embedding_factory.EmbeddingProviderFactory.create_embedding_model") as mock_factory:
            mock_factory.return_value = MagicMock()
            await service.get_embedding_model()
            mock_factory.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_collection_name_logic(self, mock_settings_service):
        """Test collection naming mapping."""
        service = VectorService(mock_settings_service)
        assert await service.get_collection_name(provider="gemini") == "gemini_collection"
        assert await service.get_collection_name(provider="openai") == "openai_collection"
        assert await service.get_collection_name(provider="local") == "local_collection"
