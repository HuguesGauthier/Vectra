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

        Args:
            provider: Provider name ('local', 'gemini', 'openai', 'huggingface')
            settings_service: Service to fetch provider configuration
            **options: Additional options (batch_size, threads, etc.)

        Returns:
            Configured embedding model

        Raises:
            ExternalDependencyError: If provider is not configured or dependencies missing
        """
        provider = provider.lower().strip()

        logger.info(f"🏭 Factory creating embedding model | Provider: {provider}")

        # Route to provider-specific factory method
        factory_map = {
            "local": EmbeddingProviderFactory._create_local_embedding,
            "huggingface": EmbeddingProviderFactory._create_local_embedding,
            "gemini": EmbeddingProviderFactory._create_gemini_embedding,
            "openai": EmbeddingProviderFactory._create_openai_embedding,
        }

        factory_method = factory_map.get(provider)
        if not factory_method:
            logger.warning(f"Unknown provider '{provider}', defaulting to Gemini")
            factory_method = EmbeddingProviderFactory._create_gemini_embedding

        return await factory_method(settings_service, **options)

    @staticmethod
    async def _create_local_embedding(settings_service: SettingsService, **options: Any) -> BaseEmbedding:
        """Create HuggingFace local embedding model."""
        try:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding
        except ImportError:
            raise ExternalDependencyError("Local provider requires `llama-index-embeddings-huggingface`")

        # Get model name from settings
        model_name = await settings_service.get_value("local_embedding_model") or "BAAI/bge-m3"

        # Extract and sanitize options
        batch_size = options.pop("batch_size", 10)
        options.pop("threads", None)  # Not used by HuggingFace

        logger.info(f"🔹 Creating Local Embedding | Model: {model_name} | Batch: {batch_size}")

        # P0 FIX: Explicit device parameter to avoid PyTorch meta tensor error
        return await asyncio.to_thread(
            HuggingFaceEmbedding,
            model_name=model_name,
            # device="cpu", # Conflicts with accelerate in some versions if device_map is auto?
            # Actually, "cpu" is correct, but let's be extremely explicit with model_kwargs
            # P0 FIX: SImplified config to avoid meta tensor conflict
            # device="cpu", # Let SentenceTransformer detect or default
            trust_remote_code=True,
            embed_batch_size=batch_size,
            model_kwargs={"low_cpu_mem_usage": False},
        )

    @staticmethod
    async def _create_gemini_embedding(settings_service: SettingsService, **options: Any) -> BaseEmbedding:
        """Create Gemini embedding model."""
        try:
            from llama_index.embeddings.gemini import GeminiEmbedding
        except ImportError:
            raise ExternalDependencyError("Gemini provider requires `llama-index-embeddings-gemini`")

        # Get configuration from settings
        api_key = await settings_service.get_value("gemini_api_key")
        model_name = await settings_service.get_value("gemini_embedding_model") or "gemini-embedding-001"

        if not api_key:
            raise ExternalDependencyError("Gemini provider requires GEMINI_API_KEY")

        # Clean model name (remove 'models/' prefix if present)
        if model_name.startswith("models/"):
            model_name = model_name.replace("models/", "")

        # Extract options
        batch_size = options.pop("batch_size", 10)
        options.pop("threads", None)  # Not used by Gemini

        logger.info(f"🔹 Creating Gemini Embedding | Model: {model_name} | Batch: {batch_size}")

        return await asyncio.to_thread(
            GeminiEmbedding,
            model_name=model_name,
            api_key=api_key,
            embed_batch_size=batch_size,
        )

    @staticmethod
    async def _create_openai_embedding(settings_service: SettingsService, **options: Any) -> BaseEmbedding:
        """Create OpenAI embedding model."""
        try:
            from llama_index.embeddings.openai import OpenAIEmbedding
        except ImportError:
            raise ExternalDependencyError("OpenAI provider requires `llama-index-embeddings-openai`")

        # Get configuration from settings
        api_key = await settings_service.get_value("openai_api_key")
        model_name = await settings_service.get_value("openai_embedding_model") or "text-embedding-3-small"

        if not api_key:
            raise ExternalDependencyError("OpenAI provider requires OPENAI_API_KEY")

        # Extract options
        batch_size = options.pop("batch_size", 100)
        options.pop("threads", None)  # Not used by OpenAI

        logger.info(f"🔹 Creating OpenAI Embedding | Model: {model_name} | Batch: {batch_size}")

        return await asyncio.to_thread(
            OpenAIEmbedding,
            model=model_name,
            api_key=api_key,
            embed_batch_size=batch_size,
        )
