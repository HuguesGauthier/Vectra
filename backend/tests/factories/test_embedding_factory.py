"""
Unit tests for EmbeddingProviderFactory.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.factories.embedding_factory import EmbeddingProviderFactory
from app.core.exceptions import ExternalDependencyError


class TestEmbeddingProviderFactory:
    """Test Embedding Provider Factory."""

    @pytest.mark.asyncio
    @patch("llama_index.embeddings.openai.OpenAIEmbedding")
    async def test_create_openai_embedding(self, mock_openai):
        """Should create OpenAI embedding with correct params."""
        # 1. Setup mocks
        mock_settings = AsyncMock()
        mock_settings.get_value.side_effect = lambda key: (
            "sk-test-key" if "api_key" in key else "text-embedding-3-small"
        )

        # 2. Run
        await EmbeddingProviderFactory.create_embedding_model("openai", mock_settings, batch_size=50)

        # 3. Verify
        # Since we use asyncio.to_thread, we check what was passed to the constructor
        mock_openai.assert_called_once_with(model="text-embedding-3-small", api_key="sk-test-key", embed_batch_size=50)

    @pytest.mark.asyncio
    @patch("llama_index.embeddings.gemini.GeminiEmbedding")
    async def test_create_gemini_embedding(self, mock_gemini):
        """Should create Gemini embedding with correct params."""
        # 1. Setup mocks
        mock_settings = AsyncMock()
        mock_settings.get_value.side_effect = lambda key: "gemini-key" if "api_key" in key else "models/embedding-001"

        # 2. Run
        await EmbeddingProviderFactory.create_embedding_model("gemini", mock_settings)

        # 3. Verify
        mock_gemini.assert_called_once_with(
            model_name="embedding-001",  # 'models/' prefix removed
            api_key="gemini-key",
            embed_batch_size=10,  # Default for Gemini
        )

    @pytest.mark.asyncio
    @patch("llama_index.embeddings.huggingface.HuggingFaceEmbedding")
    async def test_create_local_embedding(self, mock_hf):
        """Should create Local (HuggingFace) embedding with correct params."""
        # 1. Setup mocks
        mock_settings = AsyncMock()
        mock_settings.get_value.return_value = "BAAI/bge-large-en"

        # 2. Run
        await EmbeddingProviderFactory.create_embedding_model("local", mock_settings, batch_size=5)

        # 3. Verify
        mock_hf.assert_called_once_with(
            model_name="BAAI/bge-large-en",
            trust_remote_code=True,
            embed_batch_size=5,
            model_kwargs={"low_cpu_mem_usage": False},
        )

    @pytest.mark.asyncio
    async def test_missing_api_key_raises_error(self):
        """Should raise ExternalDependencyError if API key is missing for cloud providers."""
        mock_settings = AsyncMock()
        mock_settings.get_value.return_value = None  # No API key

        with pytest.raises(ExternalDependencyError) as exc:
            await EmbeddingProviderFactory.create_embedding_model("openai", mock_settings)

        assert "requires OPENAI_API_KEY" in str(exc.value)

    @pytest.mark.asyncio
    @patch("llama_index.embeddings.gemini.GeminiEmbedding")
    async def test_unknown_provider_defaults_to_gemini(self, mock_gemini):
        """Should fallback to Gemini for unknown providers."""
        mock_settings = AsyncMock()
        mock_settings.get_value.side_effect = lambda key: "gemini-key" if "api_key" in key else "val"

        await EmbeddingProviderFactory.create_embedding_model("quantum-ai", mock_settings)

        mock_gemini.assert_called_once()
