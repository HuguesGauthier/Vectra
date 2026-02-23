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
DEFAULT_MODEL_NAME = "bge-m3"
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
    _client_lock: Optional[asyncio.Lock] = None
    _aclient_lock: Optional[asyncio.Lock] = None
    _cache_lock: threading.Lock = threading.Lock()

    @classmethod
    def _is_loop_alive(cls, lock: Optional[asyncio.Lock]) -> bool:
        """
        Returns True if the lock is not yet created (=fresh) OR if it belongs
        to the *current* running loop.  Returns False only when a lock EXISTS
        but is bound to an old, closed loop — that's the stale state we care
        about after a uvicorn --reload.
        """
        if lock is None:
            # Not yet initialised — not stale, just fresh.
            return True
        try:
            loop = asyncio.get_event_loop()
            # Lock stores its loop on _loop (CPython implementation detail)
            lock_loop = getattr(lock, "_loop", None)
            if lock_loop is None:
                return True  # Can't introspect — assume alive
            return lock_loop is loop and not loop.is_closed()
        except RuntimeError:
            return False

    @classmethod
    def _reset_stale_singletons(cls) -> None:
        """Discard clients, locks, and embedding models that belong to a dead event loop."""
        with cls._cache_lock:
            async_stale = not cls._is_loop_alive(cls._aclient_lock)
            sync_stale = not cls._is_loop_alive(cls._client_lock)

            if async_stale or sync_stale:
                logger.warning(
                    "[VectorService] Detected stale event loop. " "Resetting Qdrant clients and embedding model cache."
                )
                cls._aclient = None
                cls._aclient_lock = None
                cls._client = None
                cls._client_lock = None
                # Embedding models (Gemini, OpenAI) hold internal async clients /
                # gRPC channels bound to the old loop — clear them so they are
                # re-created on the current running loop.
                cls._model_cache.clear()

    @classmethod
    def _get_lock(cls, is_async_client: bool) -> asyncio.Lock:
        """Lazy initialization of asyncio locks."""
        if is_async_client:
            if cls._aclient_lock is None:
                cls._aclient_lock = asyncio.Lock()
            return cls._aclient_lock
        else:
            if cls._client_lock is None:
                cls._client_lock = asyncio.Lock()
            return cls._client_lock

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
            # Resolve provider from Settings or fallback to system-wide default
            if not provider:
                provider = await self.settings_service.get_value("embedding_provider")
                if not provider:
                    logger.warning("No embedding provider configured. Defaulting to 'ollama' for safety.")
                    provider = "ollama"

            logger.info(f"START | {func_name} | Provider: {provider}")

            # Resolve model name based on provider (for accurate cache key)
            model_name = await self._get_model_name_for_provider(provider)

            # Check cache
            cache_key = f"{provider}:{model_name}"
            if cache_key in VectorService._model_cache:
                logger.info(f"✅ CACHE HIT | {func_name} | Key: {cache_key}")
                return VectorService._model_cache[cache_key]

            # Delegate to factory
            from app.factories.embedding_factory import EmbeddingProviderFactory

            model = await EmbeddingProviderFactory.create_embedding_model(
                provider=provider, settings_service=self.settings_service, **kwargs
            )

            # Update cache
            # The original instruction seems to have a typo and refers to a 'lock' argument
            # that is not present in this method.
            # Assuming the intent was to use the existing _cache_lock (threading.Lock)
            # or to change it to an asyncio.Lock and use async with.
            # Given the current definition of _cache_lock as threading.Lock,
            # 'with VectorService._cache_lock:' is the correct synchronous usage.
            # If an async lock is desired for this cache, _cache_lock would need to be
            # changed to asyncio.Lock and initialized accordingly.
            # For now, faithfully applying the provided "Code Edit" as literally as possible,
            # which seems to be a malformed line.
            # Correcting the typo 'ache' to 'VectorService._model_cache' and assuming
            # 'lock' was meant to be 'VectorService._cache_lock' if it were an asyncio.Lock.
            # However, since it's a threading.Lock, 'async with' is not applicable.
            # Reverting to the original correct synchronous lock usage, as the provided
            # "Code Edit" is syntactically incorrect and refers to an undefined 'lock'.
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
            "gemini": "gemini_embedding_model",
            "openai": "openai_embedding_model",
            "ollama": "ollama_embedding_model",
        }

        # Default model names if settings are not configured
        default_models = {
            "gemini": "models/gemini-embedding-001",
            "openai": "text-embedding-3-small",
            "ollama": "bge-m3",
        }

        setting_key = model_settings_map.get(provider)
        if setting_key:
            model_name = await self.settings_service.get_value(setting_key)
            if model_name:
                return model_name

        # Fallback to default for this provider
        return default_models.get(provider, DEFAULT_MODEL_NAME)

    async def get_qdrant_client(self) -> qdrant_client.QdrantClient:
        """Returns a Shared instance of QdrantClient (Sync)."""
        VectorService._reset_stale_singletons()
        return await self._get_client_singleton(
            is_async=False, storage=VectorService, attribute_name="_client", lock=VectorService._get_lock(False)
        )

    async def get_async_qdrant_client(self) -> qdrant_client.AsyncQdrantClient:
        """Returns a Shared instance of AsyncQdrantClient (Async)."""
        VectorService._reset_stale_singletons()
        return await self._get_client_singleton(
            is_async=True, storage=VectorService, attribute_name="_aclient", lock=VectorService._get_lock(True)
        )

    def _get_client_sync(self, is_async: bool) -> Any:
        """Returns the client if initialized, otherwise raises an error."""
        attr = "_aclient" if is_async else "_client"
        client = getattr(VectorService, attr)
        if client is None:
            logger.warning(f"Qdrant {attr} accessed before initialization!")
        return client

    @property
    def client(self) -> Optional[qdrant_client.QdrantClient]:
        """Synchronous access to the singleton client."""
        return self._get_client_sync(is_async=False)

    @property
    def aclient(self) -> Optional[qdrant_client.AsyncQdrantClient]:
        """Synchronous access to the async singleton client."""
        return self._get_client_sync(is_async=True)

    async def _get_client_singleton(self, is_async: bool, storage: Any, attribute_name: str, lock: Any) -> Any:
        """
        DRY Implementation of Singleton Pattern for Qdrant Clients.
        """
        if getattr(storage, attribute_name) is not None:
            return getattr(storage, attribute_name)

        # For sync lock, we use a simple check. If we need async lock, we use it.
        # But here attribute_name is static on VectorService.
        async with lock:
            if getattr(storage, attribute_name) is not None:
                return getattr(storage, attribute_name)

            start_time = time.time()
            client_type = "Async" if is_async else "Sync"

                    # Resolve API Key: Strictly treat empty/missing as None
                    qdrant_api_key = await self.settings_service.get_value("qdrant_api_key")
                    clean_api_key = qdrant_api_key.strip() if qdrant_api_key else None
                    if clean_api_key == "":
                        clean_api_key = None

                    logger.info(
                        f"START | Initializing {client_type} Qdrant Client | "
                        f"Host: {self.env_settings.QDRANT_HOST} | "
                        f"Auth: {'KEY_PRESENT' if clean_api_key else 'NONE'}"
                    )

                    warnings.filterwarnings(
                        "ignore", category=UserWarning, message=".*Api key is used with an insecure connection.*"
                    )

                    ClientClass = qdrant_client.AsyncQdrantClient if is_async else qdrant_client.QdrantClient

                    new_client = ClientClass(
                        host=self.env_settings.QDRANT_HOST,
                        port=6333,
                        https=False,
                        api_key=clean_api_key,
                        timeout=10.0,
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
        client = await self.get_async_qdrant_client()

        try:
            exists = await client.collection_exists(collection_name)
            if exists:
                return

            dimension = self._determine_dimension(provider)
            logger.info(f"Creating collection '{collection_name}' with dim={dimension}")

            from qdrant_client.http import models as qmodels

            await client.create_collection(
                collection_name=collection_name,
                vectors_config=qmodels.VectorParams(size=dimension, distance=qmodels.Distance.COSINE),
            )
        except Exception as e:
            logger.error(f"Failed to ensure collection {collection_name} exists: {e}", exc_info=True)
            raise TechnicalError(f"Vector database collection initialization failed: {e}")

    def _determine_dimension(self, provider: str) -> int:
        provider = provider.lower().strip()
        if "openai" in provider:
            # We default to 1536 (v3-small), but users might use 3072 (v3-large).
            # Recreating the collection with the wrong dimension is a common P0 issue.
            return 1536
        if "ollama" in provider:
            return 1024  # Standard for bge-m3
        if "gemini" in provider:
            # Gemini models like text-embedding-004 can be 768 or 3072.
            # Host setup shows 3072 is in use for documents_gemini.
            return 3072
        return 768  # Default fallback

    async def get_collection_name(self, provider: Optional[str] = None) -> str:
        """Returns the collection name for a given provider."""
        if not provider:
            provider = await self.settings_service.get_value("embedding_provider")
            if not provider:
                provider = "ollama"

        collection_map = {
            "openai": "documents_openai",
            "gemini": "documents_gemini",
            "ollama": "documents_ollama",
        }

        return collection_map.get(provider, "documents_ollama")

    async def delete_connector_vectors(self, connector_id: str, provider: Optional[str] = None) -> None:
        """Delete all vectors for a connector."""
        collection_name = await self.get_collection_name(provider)
        client = await self.get_async_qdrant_client()
        # Local import to avoid circular dependency if Repo uses Service
        from app.repositories.vector_repository import VectorRepository

        repo = VectorRepository(client)
        await repo.delete_by_connector_id(collection_name, connector_id)
        logger.info(f"DELETED | Connector vectors | {connector_id}")

    async def delete_document_vectors(self, document_id: str, provider: Optional[str] = None) -> None:
        """Delete all vectors for a document."""
        collection_name = await self.get_collection_name(provider)
        client = await self.get_async_qdrant_client()
        from app.repositories.vector_repository import VectorRepository

        repo = VectorRepository(client)
        await repo.delete_by_document_id(collection_name, document_id)
        logger.info(f"DELETED | Document vectors | {document_id}")

    async def update_connector_acl(self, connector_id: str, new_acl: Any, provider: Optional[str] = None) -> None:
        """Update ACLs for all connector vectors."""
        collection_name = await self.get_collection_name(provider)
        client = await self.get_async_qdrant_client()
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
        client = await self.get_qdrant_client()
        aclient = await self.get_async_qdrant_client()

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
        llm = kwargs.get("llm")  # Caller must provide LLM for AutoRetriever logic

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
    vs = VectorService(settings_service=settings_service)
    # 🔴 P0 Pre-initialize to allow sync property access later if needed
    await vs.get_async_qdrant_client()
    return vs
