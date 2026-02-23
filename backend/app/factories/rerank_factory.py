import logging
from typing import Any, Optional
import asyncio

from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

class RerankProviderFactory:
    """
    Factory for creating reranker instances (Cohere, Local FastEmbed).
    Centralizes initialization and configuration retrieval.
    """

    _local_reranker = None
    _cohere_clients = {} # Cache clients by API key

    @staticmethod
    async def create_reranker(provider: str, settings_service: SettingsService) -> Any:
        """
        Create a reranker instance for the specified provider.
        """
        provider = provider.lower().strip()
        
        if provider == "cohere":
            return await RerankProviderFactory._get_cohere_client(settings_service)
        elif provider == "local":
            return await RerankProviderFactory._get_local_reranker(settings_service)
        else:
            logger.warning(f"Unknown rerank provider '{provider}', defaulting to Local")
            return await RerankProviderFactory._get_local_reranker(settings_service)

    @staticmethod
    async def _get_cohere_client(settings_service: SettingsService) -> Any:
        try:
            import cohere
        except ImportError:
            raise ImportError("Cohere reranker requires `cohere` package. Install with `pip install cohere`.")

        api_key = await settings_service.get_value("cohere_api_key")
        if not api_key:
            logger.error("Cohere API Key missing in settings.")
            return None

        if api_key not in RerankProviderFactory._cohere_clients:
            logger.info("Initializing Cohere AsyncClient")
            RerankProviderFactory._cohere_clients[api_key] = cohere.AsyncClient(api_key=api_key)
        
        return RerankProviderFactory._cohere_clients[api_key]

    @staticmethod
    async def _get_local_reranker(settings_service: SettingsService) -> Any:
        try:
            from fastembed import TextReranker
        except ImportError:
            raise ImportError("Local reranker requires `fastembed` package. Install with `pip install fastembed`.")

        model_name = await settings_service.get_value("local_rerank_model") or "BAAI/bge-reranker-base"
        
        if not RerankProviderFactory._local_reranker:
            logger.info(f"Initializing Local FastEmbed Reranker with model: {model_name}")
            # TextReranker initialization can be blocking/heavy, but usually fast enough.
            # Running in thread to be safe if needed, but here we stay simple.
            RerankProviderFactory._local_reranker = TextReranker(model_name=model_name)
            
        return RerankProviderFactory._local_reranker
