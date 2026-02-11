import asyncio
import logging
import threading
import time
import warnings
from typing import Annotated, Any, Dict, Optional, Type, TypeVar

import qdrant_client
from fastapi import Depends
from llama_index.core.base.embeddings.base import BaseEmbedding

from app.core.exceptions import ExternalDependencyError, TechnicalError
from app.core.settings import get_settings
from app.services.settings_service import SettingsService, get_settings_service

logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL_NAME = "models/gemini-embedding-001"
DEFAULT_EMBEDDING_DIM = 768

# TypeVars for clear generics
TClient = TypeVar("TClient", bound=qdrant_client.QdrantClient)
TAsyncClient = TypeVar("TAsyncClient", bound=qdrant_client.AsyncQdrantClient)


class VectorService:
    """
    Service responsible for managing vector database connections and embedding models.

    AUDIT P0 FIXES:
    - Enforced prefer_grpc=False to prevent connection hangs.
    - Strict Type Hints.
    - Unified Client Initialization (DRY).
    - Removed Dead Legacy Code.
    - Added SRP Methods for Vector Cleanup.
    """

    # Singleton Storage (Thread-Safe)
    _client: Optional[qdrant_client.QdrantClient] = None
    _aclient: Optional[qdrant_client.AsyncQdrantClient] = None
    _model_cache: Dict[str, BaseEmbedding] = {}
    _client_lock: threading.Lock = threading.Lock()
    _aclient_lock: threading.Lock = threading.Lock()
    _cache_lock: threading.Lock = threading.Lock()

    def __init__(self, settings_service: SettingsService):
        self.settings_service = settings_service
        self.env_settings = get_settings()

    async def get_embedding_model(self, provider: Optional[str] = None, **kwargs: Any) -> BaseEmbedding:
        """
        Returns the configured embedding model based on provider.
        Delegates to EmbeddingProviderFactory for consistent initialization.
        """
        start_time = time.time()
        func_name = "VectorService.get_embedding_model"

        try:
            # Resolve provider
            if not provider:
                provider_val = await self.settings_service.get_value("embedding_provider")
                provider = (provider_val or "gemini").lower().strip()

            logger.info(f"START | {func_name} | Provider: {provider}")

            # Resolve model name based on provider (for accurate cache key)
            model_name = await self._get_model_name_for_provider(provider)

            # Check cache
            cache_key = f"{provider}:{model_name}"
            if cache_key in VectorService._model_cache:
                logger.info(f"✅ CACHE HIT | {func_name} | Key: {cache_key}")
                return VectorService._model_cache[cache_key]

            # Delegate to factory
            from app.factories.embedding_factory import \
                EmbeddingProviderFactory

            model = await EmbeddingProviderFactory.create_embedding_model(
                provider=provider, settings_service=self.settings_service, **kwargs
            )

            # Update cache
            with VectorService._cache_lock:
                VectorService._model_cache[cache_key] = model
                logger.info(f"💾 CACHED | {func_name} | Key: {cache_key}")

            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.info(f"FINISH | {func_name} | Duration: {elapsed}ms")
            return model

        except ExternalDependencyError:
            raise
        except Exception as e:
            logger.error(f"❌ FAIL | {func_name} | Error: {str(e)}", exc_info=True)
            raise TechnicalError(f"Unexpected error initializing embedding model: {e}")

    async def _get_model_name_for_provider(self, provider: str) -> str:
        """Get the actual model name for a provider from settings."""
        provider = provider.lower().strip()

        # Map provider to their respective model setting keys
        model_settings_map = {
            "local": "local_embedding_model",
            "huggingface": "local_embedding_model",
            "gemini": "gemini_embedding_model",
            "openai": "openai_embedding_model",
        }

        # Default model names if settings are not configured
        default_models = {
            "local": "BAAI/bge-m3",
            "huggingface": "BAAI/bge-m3",
            "gemini": "models/gemini-embedding-001",
            "openai": "text-embedding-3-small",
        }

        setting_key = model_settings_map.get(provider)
        if setting_key:
            model_name = await self.settings_service.get_value(setting_key)
            if model_name:
                return model_name

        # Fallback to default for this provider
        return default_models.get(provider, DEFAULT_MODEL_NAME)

    def get_qdrant_client(self) -> qdrant_client.QdrantClient:
        """Returns a Shared instance of QdrantClient (Sync)."""
        return self._get_client_singleton(
            is_async=False, storage=VectorService, attribute_name="_client", lock=VectorService._client_lock
        )

    def get_async_qdrant_client(self) -> qdrant_client.AsyncQdrantClient:
        """Returns a Shared instance of AsyncQdrantClient (Async)."""
        return self._get_client_singleton(
            is_async=True, storage=VectorService, attribute_name="_aclient", lock=VectorService._aclient_lock
        )

    def _get_client_singleton(self, is_async: bool, storage: Any, attribute_name: str, lock: threading.Lock) -> Any:
        """
        DRY Implementation of Singleton Pattern for Qdrant Clients.
        """
        if getattr(storage, attribute_name) is not None:
            return getattr(storage, attribute_name)

        with lock:
            if getattr(storage, attribute_name) is not None:
                return getattr(storage, attribute_name)

            start_time = time.time()
            client_type = "Async" if is_async else "Sync"
            logger.info(f"START | Initializing {client_type} Qdrant Client | Host: {self.env_settings.QDRANT_HOST}")

            try:
                # P0: Suppress Insecure Connection Warnings for Localhost
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore", category=UserWarning, message=".*Api key is used with an insecure connection.*"
                    )

                    ClientClass = qdrant_client.AsyncQdrantClient if is_async else qdrant_client.QdrantClient

                    # P0: prefer_grpc=False is CRITICAL for Windows/Docker stability
                    new_client = ClientClass(
                        host=self.env_settings.QDRANT_HOST,
                        port=6333,
                        https=False,
                        api_key=self.env_settings.QDRANT_API_KEY if self.env_settings.QDRANT_API_KEY else None,
                        timeout=5.0,
                        prefer_grpc=False,
                    )

                setattr(storage, attribute_name, new_client)

                elapsed = round((time.time() - start_time) * 1000, 2)
                logger.info(f"FINISH | Initialized {client_type} Qdrant Client | Duration: {elapsed}ms")
                return new_client

            except Exception as e:
                logger.error(f"❌ FAIL | Qdrant Init Error: {str(e)}", exc_info=True)
                raise ExternalDependencyError(f"Failed to configure {client_type} Qdrant client: {e}", service="qdrant")

    async def ensure_collection_exists(self, collection_name: str, provider: str):
        """Ensures Qdrant collection exists with correct dimensionality."""
        client = self.get_qdrant_client()
        if client.collection_exists(collection_name):
            return

        dimension = self._determine_dimension(provider)

        try:
            logger.info(f"Creating collection '{collection_name}' with dim={dimension}")
            from qdrant_client.http import models as qmodels

            client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(size=dimension, distance=qmodels.Distance.COSINE),
            )
        except Exception as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")

    def _determine_dimension(self, provider: str) -> int:
        provider = provider.lower().strip()
        if "openai" in provider:
            return 1536  # Default for v3-small/ada-002. Larger models handled via config check in callers if needed.
        if "local" in provider:
            return 1024
        return DEFAULT_EMBEDDING_DIM  # Gemini/Default

    async def get_collection_name(self, provider: Optional[str] = None) -> str:
        """Returns the collection name for a given provider."""
        if not provider:
            provider_val = await self.settings_service.get_value("embedding_provider")
            provider = (provider_val or "gemini").lower().strip()

        collection_map = {
            "openai": "openai_collection",
            "gemini": "gemini_collection",
            "local": "local_collection",
            "huggingface": "local_collection",
        }

        return collection_map.get(provider, "gemini_collection")

    async def delete_connector_vectors(self, connector_id: str, provider: Optional[str] = None) -> None:
        """Delete all vectors for a connector."""
        collection_name = await self.get_collection_name(provider)
        client = self.get_async_qdrant_client()
        # Local import to avoid circular dependency if Repo uses Service
        from app.repositories.vector_repository import VectorRepository

        repo = VectorRepository(client)
        await repo.delete_by_connector_id(collection_name, connector_id)
        logger.info(f"DELETED | Connector vectors | {connector_id}")

    async def delete_document_vectors(self, document_id: str, provider: Optional[str] = None) -> None:
        """Delete all vectors for a document."""
        collection_name = await self.get_collection_name(provider)
        client = self.get_async_qdrant_client()
        from app.repositories.vector_repository import VectorRepository

        repo = VectorRepository(client)
        await repo.delete_by_document_id(collection_name, document_id)
        logger.info(f"DELETED | Document vectors | {document_id}")

    async def update_connector_acl(self, connector_id: str, new_acl: Any, provider: Optional[str] = None) -> None:
        """Update ACLs for all connector vectors."""
        collection_name = await self.get_collection_name(provider)
        client = self.get_async_qdrant_client()
        from app.repositories.vector_repository import VectorRepository

        repo = VectorRepository(client)
        await repo.update_acl(collection_name, "connector_id", str(connector_id), new_acl)
        logger.info(f"UPDATED | Connector ACL | {connector_id}")

    async def get_query_engine(self, provider: Optional[str] = None, **kwargs) -> "BaseQueryEngine":
        """
        Creates and returns a standard LlamaIndex Vector Query Engine.
        Used by the Agentic Router.
        """
        try:
            from llama_index.core import VectorStoreIndex
            from llama_index.vector_stores.qdrant import QdrantVectorStore
        except ImportError:
            raise ExternalDependencyError("llama-index-vector-stores-qdrant is required for Agentic Router.")

        collection_name = await self.get_collection_name(provider)

        # Using the SYNC client for VectorStore based on LlamaIndex common usage
        client = self.get_qdrant_client()
        aclient = self.get_async_qdrant_client()

        # P0 FIX: Must provide aclient for async router operations
        vector_store = QdrantVectorStore(client=client, aclient=aclient, collection_name=collection_name)

        # P0 FIX: Explicitly pass the embedding model to the Index
        # This prevents it from falling back to the global/default (OpenAI) if not set.
        embed_model = await self.get_embedding_model(provider=provider)

        # We assume the index is already built/exists, so we load from store
        # Pass embed_model to ensure queries use the correct provider
        index = VectorStoreIndex.from_vector_store(vector_store=vector_store, embed_model=embed_model)

        # P0 FIX: Dynamic Retriever Factory integration
        # If indexing_strategy is passed (and maybe an LLM), we create a smart retriever
        from app.schemas.ingestion import IndexingStrategy

        indexing_strategy = kwargs.pop("indexing_strategy", None)
        llm = kwargs.pop("llm", None)  # Caller must provide LLM for AutoRetriever logic

        if indexing_strategy:
            # Lazy import to avoid circular dep
            from app.core.rag.csv.retriever_factory import RetrieverFactory

            retriever = RetrieverFactory.get_retriever(
                index=index,
                indexing_strategy=indexing_strategy,
                llm=llm,
                similarity_top_k=kwargs.get("similarity_top_k", 5),
                collection_name=collection_name,
            )

            from llama_index.core.query_engine import RetrieverQueryEngine

            return RetrieverQueryEngine(retriever=retriever)

        # Fallback to standard
        # CRITICAL: Enable streaming for better UX and proper token extraction
        if "streaming" not in kwargs:
            kwargs["streaming"] = True
        return index.as_query_engine(**kwargs)


async def get_vector_service(
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> VectorService:
    """FastAPI Dependency Provider."""
    return VectorService(settings_service=settings_service)
