import threading
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ExternalDependencyError, TechnicalError
from app.services.settings_service import SettingsService
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
        qc.AsyncQdrantClient.return_value = MagicMock()
        yield qc


class TestVectorService:

    def setup_method(self):
        # Reset shared client storage for clean testing
        VectorService._client = None
        VectorService._aclient = None
        # Reset locks if needed (though usually fine)

    def test_not_singleton_instance(self, mock_settings_service):
        """Test that VectorService is NO LONGER a singleton by instance."""
        s1 = VectorService(mock_settings_service)
        s2 = VectorService(mock_settings_service)
        assert s1 is not s2  # Wait, actually it should be different instances!
        # Ah, I didn't verify if I kept __new__. Let me check.

    @pytest.mark.asyncio
    async def test_get_qdrant_client_creates_once_shared_across_instances(
        self, mock_settings_service, mock_qdrant_module
    ):
        """Test that qdrant client is stored at class level but accessible via instance."""
        s1 = VectorService(mock_settings_service)
        s2 = VectorService(mock_settings_service)

        # First call
        client1 = s1.get_qdrant_client()
        assert mock_qdrant_module.QdrantClient.called

        # Reset mock to verify it's NOT called again
        mock_qdrant_module.QdrantClient.reset_mock()

        # Second call on DIFFERENT instance
        client2 = s2.get_qdrant_client()
        assert not mock_qdrant_module.QdrantClient.called
        assert client1 is client2

    def test_get_qdrant_client_config(self, mock_settings_service, mock_qdrant_module):
        """Test client configuration parameters (timeout, grpc)."""
        service = VectorService(mock_settings_service)
        service.get_qdrant_client()

        mock_qdrant_module.QdrantClient.assert_called_with(
            host=ANY,
            port=6333,
            https=False,  # Current implementation uses False based on QDRANT_HOST scheme
            api_key=ANY,
            timeout=5.0,
            prefer_grpc=True,
        )

    @pytest.mark.asyncio
    async def test_get_embedding_model_gemini(self, mock_settings_service):
        """Test Gemini embedding model creation."""
        service = VectorService(mock_settings_service)

        async def mock_get_value(key, default=None):
            return {
                "embedding_provider": "gemini",
                "gemini_api_key": "fake_gemini_key",
                "gemini_embedding_model": "models/embedding-001",
            }.get(key, default)

        mock_settings_service.get_value.side_effect = mock_get_value

        with patch.dict("sys.modules", {"llama_index.embeddings.gemini": MagicMock()}):
            with patch("llama_index.embeddings.gemini.GeminiEmbedding") as MockGemini:
                await service.get_embedding_model()
                MockGemini.assert_called()

    @pytest.mark.asyncio
    async def test_get_embedding_model_openai(self, mock_settings_service):
        """Test OpenAI embedding model creation."""
        service = VectorService(mock_settings_service)

        async def mock_get_value(key, default=None):
            return {
                "embedding_provider": "openai",
                "openai_api_key": "fake_openai_key",
                "openai_embedding_model": "text-embedding-3-small",
            }.get(key, default)

        mock_settings_service.get_value.side_effect = mock_get_value

        with patch.dict("sys.modules", {"llama_index.embeddings.openai": MagicMock()}):
            with patch("llama_index.embeddings.openai.OpenAIEmbedding") as MockOpenAI:
                await service.get_embedding_model(provider="openai")
                MockOpenAI.assert_called()

    @pytest.mark.asyncio
    async def test_get_embedding_model_missing_key_raises_error(self, mock_settings_service):
        """Test that missing API key raises ExternalDependencyError."""
        service = VectorService(mock_settings_service)

        async def mock_get_value(key, default=None):
            return {"embedding_provider": "gemini", "gemini_api_key": None}.get(key, default)  # Missing key

        mock_settings_service.get_value.side_effect = mock_get_value

        with pytest.raises(ExternalDependencyError):
            await service.get_embedding_model(provider="gemini")

    @pytest.mark.asyncio
    async def test_get_collection_name(self, mock_settings_service):
        """Test collection naming logic."""
        service = VectorService(mock_settings_service)

        # Mock settings to return None to test the standard formatting
        mock_settings_service.get_value.return_value = None

        assert await service.get_collection_name(provider="gemini") == "vectra_gemini"
        assert await service.get_collection_name(provider="openai") == "vectra_openai"
        assert await service.get_collection_name(provider="local") == "vectra_local"

        # Test sanitization
        assert await service.get_collection_name(provider="Custom-Provider!") == "vectra_customprovider"

    @pytest.mark.asyncio
    async def test_get_async_qdrant_client(self, mock_settings_service, mock_qdrant_module):
        """Test async client creation."""
        service = VectorService(mock_settings_service)
        service.get_async_qdrant_client()
        assert mock_qdrant_module.AsyncQdrantClient.called
