from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import asyncio

from app.services.vector_service import VectorService


@pytest.mark.asyncio
async def test_get_embedding_model_provider_selection():
    mock_settings = AsyncMock()
    mock_settings.get_value.side_effect = lambda k, d=None: {
        "embedding_provider": "gemini",
        "openai_api_key": "sk-fake",
        "gemini_api_key": "fake-gemini",
        "gemini_embedding_model": "models/embedding-001",
        "openai_embedding_model": "text-embedding-3-small",
    }.get(k, d)

    # Ensure a fresh service and CLEAR GLOBAL CACHE
    service = VectorService(settings_service=mock_settings)
    VectorService._model_cache = {}

    # Test Gemini
    with patch("app.factories.embedding_factory.asyncio.to_thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        await service.get_embedding_model(provider="gemini")

        assert mock_thread.called, "asyncio.to_thread was not called for Gemini"
        args, kwargs = mock_thread.call_args
        assert "GeminiEmbedding" in str(args[0])

    # Test OpenAI Explicit
    VectorService._model_cache = {}  # Clear again
    with patch("app.factories.embedding_factory.asyncio.to_thread") as mock_thread:
        mock_thread.return_value = MagicMock()
        await service.get_embedding_model(provider="openai")

        assert mock_thread.called, "asyncio.to_thread was not called for OpenAI"
        args, kwargs = mock_thread.call_args
        assert "OpenAIEmbedding" in str(args[0])


@pytest.mark.asyncio
async def test_get_query_engine_passes_embed_model():
    mock_settings = AsyncMock()
    mock_settings.get_value.return_value = "gemini"

    service = VectorService(settings_service=mock_settings)
    service.get_qdrant_client = AsyncMock()
    service.get_async_qdrant_client = AsyncMock()
    service.get_collection_name = AsyncMock(return_value="test_collection")
    service.get_embedding_model = AsyncMock(return_value="mock_embed_model")
    VectorService._model_cache = {}

    with (
        patch("llama_index.vector_stores.qdrant.QdrantVectorStore"),
        patch("llama_index.core.VectorStoreIndex") as MockIndex,
    ):
        MockIndex.from_vector_store.return_value.as_query_engine.return_value = "mock_engine"
        await service.get_query_engine(provider="openai")
        service.get_embedding_model.assert_called_with(provider="openai")
        args, kwargs = MockIndex.from_vector_store.call_args
        assert kwargs["embed_model"] == "mock_embed_model"
