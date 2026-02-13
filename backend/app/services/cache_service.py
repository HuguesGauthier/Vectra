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
from typing import Annotated, Any, Dict, List, Optional

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
    - Redis Connection Pool is shared (Singleton) to avoid exhaustion.
    - Qdrant Client is injected.
    """

    _redis_pool: Optional[aioredis.Redis] = None
    _init_lock: asyncio.Lock = asyncio.Lock()
    _initialized: bool = False

    def __init__(self, qdrant_client: AsyncQdrantClient, embedding_dim: int = EMBEDDING_DIM):
        """
        Initialize component.

        Args:
            qdrant_client: Initialized AsyncQdrantClient.
            embedding_dim: Dimension of embeddings (dynamic based on provider).
        """
        self.qdrant = qdrant_client
        self.embedding_dim = embedding_dim

    async def initialize(self) -> None:
        """
        Initialize Shared Redis connection and ensure Qdrant collection exists.
        Async-safe.
        """
        if self._initialized:
            return

        async with self._init_lock:
            if self._initialized:
                return

            try:
                await self._init_redis_pool()
                await self._ensure_qdrant_collection()

                # CRITICAL: Only mark as initialized if both resources are OK
                SemanticCacheService._initialized = True
                logger.info("✅ SemanticCacheService fully initialized")

            except Exception as e:
                logger.error(f"❌ Cache initialization failed: {e}. Will retry on next access.")
                # We do NOT set _initialized to True, allowing retry
                SemanticCacheService._redis_pool = None

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

    async def _ensure_qdrant_collection(self) -> None:
        """Create semantic_cache collection in Qdrant if it doesn't exist or has wrong dim."""
        try:
            exists = await self.qdrant.collection_exists(CACHE_COLLECTION_NAME)

            if exists:
                # Check if dimension matches
                coll_info = await self.qdrant.get_collection(CACHE_COLLECTION_NAME)
                current_dim = coll_info.config.params.vectors.size

                if current_dim != self.embedding_dim:
                    logger.warning(
                        f"⚠️ Dimension Mismatch! Cache dim: {current_dim}, Current config: {self.embedding_dim}"
                    )
                    logger.warning(f"♻️ Recreating cache collection '{CACHE_COLLECTION_NAME}'...")
                    await self.qdrant.delete_collection(CACHE_COLLECTION_NAME)
                    exists = False

            if not exists:
                await self.qdrant.create_collection(
                    collection_name=CACHE_COLLECTION_NAME,
                    vectors_config=VectorParams(size=self.embedding_dim, distance=Distance.COSINE),
                )
                logger.info(f"✅ Created Qdrant collection: {CACHE_COLLECTION_NAME} (dim={self.embedding_dim})")

        except Exception as e:
            logger.warning(f"Note on Qdrant collection creation: {e}")

    @property
    def redis(self) -> Optional[aioredis.Redis]:
        """Safe accessor for Redis pool."""
        return SemanticCacheService._redis_pool

    async def get_cached_response(
        self,
        question: str,
        assistant_id: str,
        embedding: List[float],
        min_score: float = settings.SEMANTIC_CACHE_SIMILARITY_THRESHOLD,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve response from cache (Exact Match -> Semantic Match).

        Args:
            question: User question.
            assistant_id: ID of the assistant.
            embedding: Vector embedding of the question.
            min_score: Minimum similarity score for semantic match.

        Returns:
            Cached response dict or None if no match found.
        """
        if not SemanticCacheService._initialized:
            await self.initialize()

        if not self.redis:
            return None

        # 1. Exact Match via Redis
        exact_key = self._generate_cache_key(question, assistant_id)
        cached_json = await self._find_exact_match(exact_key)
        if cached_json:
            return cached_json

        # 2. Semantic Search via Qdrant
        return await self._find_semantic_match(embedding, assistant_id, min_score)

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
        self, embedding: List[float], assistant_id: str, min_score: float
    ) -> Optional[Dict[str, Any]]:
        """Perform semantic similarity search in Qdrant."""
        try:
            search_response = await self.qdrant.query_points(
                collection_name=CACHE_COLLECTION_NAME,
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
        """Validate that the cache key belongs to the correct assistant."""
        if not cache_key or f"cache:{assistant_id}:" not in cache_key:
            logger.warning(f"⚠️ Semantic match mismatch logic. Ignoring. Key: {cache_key}")
            return False
        return True

    def _generate_cache_key(self, question: str, assistant_id: str) -> str:
        """Generate deterministic cache key."""
        normalized = " ".join(question.lower().split())
        q_hash = hashlib.sha256(normalized.encode()).hexdigest()
        return f"cache:{assistant_id}:{q_hash}"

    async def set_cached_response(
        self, question: str, assistant_id: str, embedding: List[float], response: Dict[str, Any]
    ) -> None:
        """
        Store response in Redis (with TTL) and Qdrant.

        Args:
            question: User question.
            assistant_id: ID of the assistant.
            embedding: Vector embedding of the question.
            response: Response to be cached.
        """
        if not SemanticCacheService._initialized:
            await self.initialize()

        if not self.redis:
            return

        try:
            cache_key = self._generate_cache_key(question, assistant_id)

            # 1. Redis Cache
            await self._cache_in_redis(cache_key, response)

            # 2. Qdrant Cache
            await self._cache_in_qdrant(cache_key, question, assistant_id, embedding)

            logger.debug(f"💾 Cache entry set: {cache_key}")

        except Exception as e:
            logger.error(f"Cache storage error: {e}", exc_info=True)

    async def _cache_in_redis(self, cache_key: str, response: Dict[str, Any]) -> None:
        """Store the response JSON in Redis with a TTL."""
        response_json = json.dumps(response, default=str)
        await self.redis.setex(
            name=cache_key,
            time=settings.REDIS_CACHE_TTL,
            value=response_json,
        )

    async def _cache_in_qdrant(self, cache_key: str, question: str, assistant_id: str, embedding: List[float]) -> None:
        """Store the semantic index in Qdrant."""
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, cache_key))
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "cache_key": cache_key,
                "question": question[:500],  # Store truncated for context visibility
                "assistant_id": assistant_id,
            },
        )
        await self.qdrant.upsert(
            collection_name=CACHE_COLLECTION_NAME,
            points=[point],
        )

    async def clear_assistant_cache(self, assistant_id: str) -> int:
        """
        Manually purge cache for an assistant (Redis keys + Qdrant vectors).

        Args:
            assistant_id: ID of the assistant whose cache should be cleared.

        Returns:
            Number of Redis keys deleted.
        """
        if not SemanticCacheService._initialized:
            await self.initialize()

        if not self.redis:
            return 0

        try:
            # 1. Redis Purge
            deleted_count = await self._purge_redis_keys(assistant_id)

            # 2. Qdrant Purge
            await self._purge_qdrant_points(assistant_id)

            logger.info(f"🧹 Manual Cache Purge: Deleted {deleted_count} Redis keys for Assistant {assistant_id}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to clear assistant cache: {e}", exc_info=True)
            raise TechnicalError(f"Cache purge failed: {e}")

    async def _purge_redis_keys(self, assistant_id: str) -> int:
        """Scan and delete all Redis keys for a specific assistant."""
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

    async def _purge_qdrant_points(self, assistant_id: str) -> None:
        """Delete semantic index points for a specific assistant from Qdrant."""
        from app.repositories.vector_repository import VectorRepository

        vector_repo = VectorRepository(self.qdrant)
        await vector_repo.delete_by_assistant_id(CACHE_COLLECTION_NAME, assistant_id)

    @classmethod
    async def shutdown(cls) -> None:
        """Cleanup singleton resources on app shutdown."""
        if cls._redis_pool:
            await cls._redis_pool.close()
            cls._redis_pool = None
            logger.info("🛑 Redis cache pool closed")


# Dependency Injection
async def get_cache_service(
    vector_service: Annotated[VectorService, Depends(get_vector_service)],
) -> SemanticCacheService:
    """
    FastAPI dependency provider for SemanticCacheService.
    Scopes the Qdrant client from VectorService.
    """
    # Dynamically determine dimension from configured provider
    provider = await vector_service.settings_service.get_value("embedding_provider")
    embedding_dim = vector_service._determine_dimension(provider or "gemini")

    qdrant_client = await vector_service.get_async_qdrant_client()
    return SemanticCacheService(qdrant_client, embedding_dim=embedding_dim)
