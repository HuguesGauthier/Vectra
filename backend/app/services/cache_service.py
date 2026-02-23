"""
Semantic Cache Service.

Implements intelligent caching for RAG responses using:
- Redis for JSON storage (fast retrieval)
- Qdrant for semantic similarity search (find similar questions)

ARCHITECT NOTE:
- Uses Singleton pattern for Redis Connection Pool to prevent connection leaks.
- Implements strict typing and separation of concerns.
"""

import asyncio
import hashlib
import json
import logging
import uuid
from typing import Annotated, Any, Dict, List, Optional, Set

import redis.asyncio as aioredis
from fastapi import Depends
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, MatchValue, PointStruct, SearchParams, VectorParams

from app.core.exceptions import TechnicalError
from app.core.settings import settings
from app.services.vector_service import VectorService, get_vector_service

logger = logging.getLogger(__name__)

# Constants
CACHE_COLLECTION_NAME = "semantic_cache"
EMBEDDING_DIM = 768  # Gemini text-embedding-004 dimension
REDIS_CONNECT_TIMEOUT = 5.0
MAX_REDIS_CONNECTIONS = 50
SCAN_BATCH_COUNT = 100


class SemanticCacheService:
    """
    Semantic cache using Redis for storage and Qdrant for similarity search.

    Architecture:
    - Redis Connection Pool is shared (Singleton).
    - Uses VectorService for Qdrant interactions and dimension resolution.
    """

    _redis_pool: Optional[aioredis.Redis] = None
    _init_lock: asyncio.Lock = asyncio.Lock()
    _initialized_providers: Set[str] = set()

    def __init__(self, vector_service: VectorService):
        """
        Initialize component.

        Args:
            vector_service: Injected VectorService instance.
        """
        self.vector_service = vector_service

    async def _ensure_resources(self, provider: str) -> str:
        """
        Ensure Redis pool and Qdrant collection for provider exist.
        Returns the resolved collection name.
        """
        # 1. Init Redis (Global)
        if SemanticCacheService._redis_pool is None:
            async with self._init_lock:
                if SemanticCacheService._redis_pool is None:
                    await self._init_redis_pool()

        # 2. Resolve Collection Name
        collection_name = f"semantic_cache_{provider}"

        # 3. Init Collection (Per Provider) - Logic moved to VectorService usually, but we call ensure here
        if provider not in SemanticCacheService._initialized_providers:
            async with self._init_lock:
                if provider not in SemanticCacheService._initialized_providers:
                    await self.vector_service.ensure_collection_exists(collection_name, provider=provider)
                    SemanticCacheService._initialized_providers.add(provider)

        return collection_name

    async def _init_redis_pool(self) -> None:
        """Initialize the shared Redis connection pool."""
        if SemanticCacheService._redis_pool is not None:
            return

        SemanticCacheService._redis_pool = await aioredis.from_url(
            f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=REDIS_CONNECT_TIMEOUT,
            max_connections=MAX_REDIS_CONNECTIONS,
            socket_keepalive=True,
        )
        await SemanticCacheService._redis_pool.ping()
        logger.info("✅ Redis cache pool initialized")

    @property
    def redis(self) -> Optional[aioredis.Redis]:
        """Safe accessor for Redis pool."""
        return SemanticCacheService._redis_pool

    async def get_cached_response(
        self,
        question: str,
        assistant_id: str,
        embedding: Optional[List[float]] = None,
        embedding_provider: str = "ollama",
        min_score: float = settings.SEMANTIC_CACHE_SIMILARITY_THRESHOLD,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve response from cache."""
        try:
            collection_name = await self._ensure_resources(embedding_provider)

            if not self.redis:
                return None

            # 1. Exact Match via Redis
            exact_key = self._generate_cache_key(question, assistant_id)
            cached_json = await self._find_exact_match(exact_key)
            if cached_json:
                return cached_json

            # 2. Semantic Search (Skip if no embedding)
            if embedding is None:
                return None

            return await self._find_semantic_match(embedding, assistant_id, min_score, collection_name)

        except Exception as e:
            logger.error(f"Cache retrieval failed: {e}")
            return None

    async def _find_exact_match(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Attempt to find an exact match in Redis."""
        try:
            cached_json = await self.redis.get(cache_key)
            if cached_json:
                logger.info(f"⚡ Cache HIT: Exact match ({cache_key})")
                return json.loads(cached_json)
        except Exception as e:
            logger.error(f"Redis lookup error: {e}")
        return None

    async def _find_semantic_match(
        self, embedding: List[float], assistant_id: str, min_score: float, collection_name: str
    ) -> Optional[Dict[str, Any]]:
        """Perform semantic similarity search in Qdrant."""
        try:
            client = await self.vector_service.get_async_qdrant_client()
            search_response = await client.query_points(
                collection_name=collection_name,
                query=embedding,
                limit=1,
                score_threshold=min_score,
                search_params=SearchParams(exact=False),
                query_filter=Filter(must=[FieldCondition(key="assistant_id", match=MatchValue(value=assistant_id))]),
            )

            if not search_response.points:
                return None

            hit = search_response.points[0]
            cache_key = hit.payload.get("cache_key")

            if not self._is_valid_cache_key(cache_key, assistant_id):
                return None

            cached_json = await self.redis.get(cache_key)
            if not cached_json:
                logger.warning(f"⚠️ Qdrant index exists but Redis key missing: {cache_key}")
                return None

            logger.info(f"✅ Cache HIT: Semantic match ({cache_key}, score={hit.score:.3f})")
            return json.loads(cached_json)

        except Exception as e:
            logger.error(f"Semantic search error: {e}")
            return None

    def _is_valid_cache_key(self, cache_key: Optional[str], assistant_id: str) -> bool:
        if not cache_key or f"cache:{assistant_id}:" not in cache_key:
            return False
        return True

    def _generate_cache_key(self, question: str, assistant_id: str) -> str:
        normalized = " ".join(question.lower().split())
        q_hash = hashlib.sha256(normalized.encode()).hexdigest()
        return f"cache:{assistant_id}:{q_hash}"

    async def set_cached_response(
        self,
        question: str,
        assistant_id: str,
        embedding: List[float],
        response: Dict[str, Any],
        embedding_provider: str = "ollama",
    ) -> None:
        """Store response in Redis and Qdrant."""
        try:
            collection_name = await self._ensure_resources(embedding_provider)

            if not self.redis:
                return

            cache_key = self._generate_cache_key(question, assistant_id)

            # 1. Redis Cache
            await self._cache_in_redis(cache_key, response)

            # 2. Qdrant Cache
            await self._cache_in_qdrant(cache_key, question, assistant_id, embedding, collection_name)

            logger.debug(f"💾 Cache entry set: {cache_key}")

        except Exception as e:
            logger.error(f"Cache storage error: {e}", exc_info=True)

    async def _cache_in_redis(self, cache_key: str, response: Dict[str, Any]) -> None:
        response_json = json.dumps(response, default=str)
        await self.redis.setex(
            name=cache_key,
            time=settings.REDIS_CACHE_TTL,
            value=response_json,
        )

    async def _cache_in_qdrant(
        self, cache_key: str, question: str, assistant_id: str, embedding: List[float], collection_name: str
    ) -> None:
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, cache_key))
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "cache_key": cache_key,
                "question": question[:500],
                "assistant_id": assistant_id,
            },
        )
        client = await self.vector_service.get_async_qdrant_client()
        await client.upsert(
            collection_name=collection_name,
            points=[point],
        )

    async def clear_assistant_cache(self, assistant_id: str) -> int:
        # Note: Clearing cache for an assistant is complex with multiple providers.
        # We would need to know WHICH provider to clear, or clear all.
        # For now, let's assume we iterate known providers or just clear the default.
        # Ideally we iterate `_initialized_providers`.

        # Simplified: Just clear Redis keys (shared) and try to clear from all initialized collections.
        if SemanticCacheService._redis_pool is None:
            async with self._init_lock:
                await self._init_redis_pool()

        count = await self._purge_redis_keys(assistant_id)

        # Best effort clear on all likely collections?
        # Or we rely on _initialized_providers
        for provider in SemanticCacheService._initialized_providers:
            collection_name = f"semantic_cache_{provider}"
            await self._purge_qdrant_points(assistant_id, collection_name)

        return count

    async def _purge_redis_keys(self, assistant_id: str) -> int:
        if not self.redis:
            return 0
        pattern = f"cache:{assistant_id}:*"
        cursor = "0"
        count = 0
        while True:
            cursor, batch = await self.redis.scan(cursor=cursor, match=pattern, count=SCAN_BATCH_COUNT)
            if batch:
                await self.redis.delete(*batch)
                count += len(batch)
            if cursor in ("0", 0):
                break
        return count

    async def _purge_qdrant_points(self, assistant_id: str, collection_name: str) -> None:
        client = await self.vector_service.get_async_qdrant_client()
        from app.repositories.vector_repository import VectorRepository

        vector_repo = VectorRepository(client)
        await vector_repo.delete_by_assistant_id(collection_name, assistant_id)

    @classmethod
    async def shutdown(cls) -> None:
        if cls._redis_pool:
            await cls._redis_pool.close()
            cls._redis_pool = None
            logger.info("🛑 Redis cache pool closed")


# Dependency Injection
async def get_cache_service(
    vector_service: Annotated[VectorService, Depends(get_vector_service)],
) -> SemanticCacheService:
    """Dependency Provider"""
    return SemanticCacheService(vector_service)
