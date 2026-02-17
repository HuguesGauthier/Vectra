import asyncio
import logging
from typing import Any, Dict, Optional

from llama_index.core.base.embeddings.base import BaseEmbedding

from app.core.exceptions import ExternalDependencyError
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


class EmbeddingProviderFactory:
    """
    Factory for creating embedding models with provider-specific configurations.
    Centralizes all provider initialization logic for consistency and maintainability.
    """

    @staticmethod
    async def create_embedding_model(provider: str, settings_service: SettingsService, **options: Any) -> BaseEmbedding:
        """
        Create an embedding model for the specified provider.
        """
        provider = provider.lower().strip()

        # P1: Unify common options
        batch_size = options.pop("batch_size", None)
        options.pop("threads", None)  # Clean up unused threads option

        logger.info(f"🏭 Factory creating embedding model | Provider: {provider}")

        # Route to provider-specific factory method
        if provider == "openai":
            return await EmbeddingProviderFactory._create_openai_embedding(
                settings_service, batch_size=batch_size or 100, **options
            )
        elif provider == "gemini":
            return await EmbeddingProviderFactory._create_gemini_embedding(
                settings_service, batch_size=batch_size or 10, **options
            )
        elif provider == "ollama":
            return await EmbeddingProviderFactory._create_ollama_embedding(
                settings_service, batch_size=batch_size or 10, **options
            )
        else:
            logger.warning(f"Unknown provider '{provider}', defaulting to Ollama")
            return await EmbeddingProviderFactory._create_ollama_embedding(
                settings_service, batch_size=batch_size or 10, **options
            )

    @staticmethod
    async def _create_gemini_embedding(
        settings_service: SettingsService, batch_size: int, **options: Any
    ) -> BaseEmbedding:
        """Create Gemini embedding model."""
        try:
            from llama_index.embeddings.gemini import GeminiEmbedding
        except ImportError:
            raise ExternalDependencyError("Gemini provider requires `llama-index-embeddings-gemini`")

        api_key = await settings_service.get_value("gemini_api_key")
        model_name = await settings_service.get_value("gemini_embedding_model") or "gemini-embedding-001"

        if not api_key:
            raise ExternalDependencyError("Gemini provider requires GEMINI_API_KEY")

        if model_name.startswith("models/"):
            model_name = model_name.replace("models/", "")

        logger.info(f"🔹 Creating Gemini Embedding | Model: {model_name} | Batch: {batch_size}")

        return await asyncio.to_thread(
            GeminiEmbedding,
            model_name=model_name,
            api_key=api_key,
            embed_batch_size=batch_size,
        )

    @staticmethod
    async def _create_openai_embedding(
        settings_service: SettingsService, batch_size: int, **options: Any
    ) -> BaseEmbedding:
        """Create OpenAI embedding model."""
        try:
            from llama_index.embeddings.openai import OpenAIEmbedding
        except ImportError:
            raise ExternalDependencyError("OpenAI provider requires `llama-index-embeddings-openai`")

        api_key = await settings_service.get_value("openai_api_key")
        model_name = await settings_service.get_value("openai_embedding_model") or "text-embedding-3-small"

        if not api_key:
            raise ExternalDependencyError("OpenAI provider requires OPENAI_API_KEY")

        logger.info(f"🔹 Creating OpenAI Embedding | Model: {model_name} | Batch: {batch_size}")

        return await asyncio.to_thread(
            OpenAIEmbedding,
            model=model_name,
            api_key=api_key,
            embed_batch_size=batch_size,
        )

    @staticmethod
    async def _create_ollama_embedding(
        settings_service: SettingsService, batch_size: int, **options: Any
    ) -> BaseEmbedding:
        """Create Ollama embedding model."""
        try:
            from llama_index.embeddings.ollama import OllamaEmbedding
        except ImportError:
            raise ExternalDependencyError("Ollama provider requires `llama-index-embeddings-ollama`")

        base_url = await settings_service.get_value("ollama_base_url")
        model_name = await settings_service.get_value("ollama_embedding_model")

        logger.info(f"🔹 Creating Ollama Embedding | URL: {base_url} | Model: {model_name} | Batch: {batch_size}")

        return await asyncio.to_thread(
            OllamaEmbedding,
            model_name=model_name,
            base_url=base_url,
            embed_batch_size=batch_size,
        )
