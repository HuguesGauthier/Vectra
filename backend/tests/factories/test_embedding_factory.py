import sys
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import asyncio

from app.factories.embedding_factory import EmbeddingProviderFactory


class TestEmbeddingProviderFactory:
    @pytest.mark.asyncio
    async def test_create_openai_embedding(self):
        mock_settings = AsyncMock()
        mock_settings.get_value.return_value = "sk-fake"

        # Patch asyncio.to_thread which is used to instantiate the model
        with patch("app.factories.embedding_factory.asyncio.to_thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            await EmbeddingProviderFactory.create_embedding_model("openai", mock_settings)

            # Verify it was called with something that looks like OpenAIEmbedding
            # and our expected args
            args, kwargs = mock_thread.call_args
            # args[0] is the class being instantiated
            assert "OpenAIEmbedding" in str(args[0])

    @pytest.mark.asyncio
    async def test_create_gemini_embedding(self):
        mock_settings = AsyncMock()
        mock_settings.get_value.return_value = "fake-key"

        with patch("app.factories.embedding_factory.asyncio.to_thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            await EmbeddingProviderFactory.create_embedding_model("gemini", mock_settings)

            args, kwargs = mock_thread.call_args
            assert "GeminiEmbedding" in str(args[0])

    @pytest.mark.asyncio
    async def test_unknown_provider_defaults_to_ollama(self):
        mock_settings = AsyncMock()
        mock_settings.get_value.return_value = "fake-url"

        with patch("app.factories.embedding_factory.asyncio.to_thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            # We need to mock the import too since it's lazy loaded
            with patch.dict(sys.modules, {"llama_index.embeddings.ollama": MagicMock()}):
                await EmbeddingProviderFactory.create_embedding_model("unknown", mock_settings)

                args, kwargs = mock_thread.call_args
                # It should fallback to OllamaEmbedding
                assert "OllamaEmbedding" in str(args[0])
