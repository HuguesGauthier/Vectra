from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import ExternalDependencyError
import importlib
import app.services.vector_service

importlib.reload(app.services.vector_service)
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

    service = VectorService(settings_service=mock_settings)

    print("DEBUG: Patching GeminiEmbedding...")
    # Test Gemini (Default)
    with patch("llama_index.embeddings.gemini.GeminiEmbedding") as MockGemini:
        await service.get_embedding_model(provider="gemini")
        MockGemini.assert_called_once()

    # Test OpenAI Explicit
    with patch("llama_index.embeddings.openai.OpenAIEmbedding") as MockOpenAI:
        await service.get_embedding_model(provider="openai")
        MockOpenAI.assert_called_once()


@pytest.mark.asyncio
async def test_get_query_engine_passes_embed_model():
    mock_settings = AsyncMock()
    mock_settings.get_value.return_value = "gemini"

    service = VectorService(settings_service=mock_settings)
    service.get_qdrant_client = MagicMock()
    service.get_async_qdrant_client = MagicMock()
    service.get_collection_name = AsyncMock(return_value="test_collection")
    service.get_embedding_model = AsyncMock(return_value="mock_embed_model")

    print("DEBUG: Patching QdrantVectorStore...")
    with (
        patch("llama_index.vector_stores.qdrant.QdrantVectorStore"),
        patch("llama_index.core.VectorStoreIndex") as MockIndex,
    ):

        MockIndex.from_vector_store.return_value.as_query_engine.return_value = "mock_engine"

        # Call with provider
        await service.get_query_engine(provider="openai")

        # Verify get_embedding_model called with correct provider
        service.get_embedding_model.assert_called_with(provider="openai")

        # Verify from_vector_store receives embed_model
        args, kwargs = MockIndex.from_vector_store.call_args
        assert kwargs["embed_model"] == "mock_embed_model"
