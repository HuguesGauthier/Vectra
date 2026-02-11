import json
import hashlib
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.services.cache_service import SemanticCacheService, CACHE_COLLECTION_NAME
from app.core.exceptions import TechnicalError

# --- Fixtures ---

@pytest.fixture
def mock_qdrant():
    return AsyncMock()

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton state of SemanticCacheService before each test."""
    SemanticCacheService._redis_pool = None
    SemanticCacheService._initialized = False
    # We can't easily reset the Lock but it shouldn't be necessary for isolation
    yield


@pytest.fixture
def cache_service(mock_qdrant):
    return SemanticCacheService(mock_qdrant)

# --- ported from audit tests ---

@pytest.mark.asyncio
async def test_singleton_redis_initialization(mock_qdrant):
    """P0: Verify that Redis connection is initialized only once (Singleton)."""
    SemanticCacheService._redis_pool = None
    SemanticCacheService._initialized = False

    service1 = SemanticCacheService(mock_qdrant)
    service2 = SemanticCacheService(mock_qdrant)

    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_redis_cls:
        mock_client = AsyncMock()
        mock_redis_cls.return_value = mock_client

        await asyncio.gather(service1.initialize(), service2.initialize())

        assert mock_redis_cls.call_count == 1
        assert SemanticCacheService._redis_pool is not None

# --- New tests ---

@pytest.mark.asyncio
async def test_initialization_resilience_allows_retry(mock_qdrant):
    """P1: Verify that a failed initialization doesn't lock the service in a broken state."""
    service = SemanticCacheService(mock_qdrant)
    
    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_redis_cls:
        # First attempt fails
        mock_redis_cls.side_effect = Exception("Redis Down")
        await service.initialize()
        
        assert SemanticCacheService._initialized is False
        assert SemanticCacheService._redis_pool is None
        
        # Second attempt succeeds
        mock_redis_cls.side_effect = None
        mock_redis_cls.return_value = AsyncMock()
        
        await service.initialize()
        
        assert SemanticCacheService._initialized is True
        assert SemanticCacheService._redis_pool is not None

@pytest.mark.asyncio
async def test_get_cached_response_exact_hit(cache_service):
    """Verify exact match Redis hit."""
    mock_redis = AsyncMock()
    SemanticCacheService._redis_pool = mock_redis
    SemanticCacheService._initialized = True
    
    question = "What is Vectra?"
    assistant_id = str(uuid4())
    expected_response = {"answer": "A powerful RAG platform"}
    
    # Mock Redis GET
    mock_redis.get.return_value = json.dumps(expected_response)
    
    # Act
    result = await cache_service.get_cached_response(question, assistant_id, embedding=[0.1]*768)
    
    # Assert
    assert result == expected_response
    mock_redis.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_cached_response_semantic_hit(cache_service, mock_qdrant):
    """Verify semantic match Qdrant hit followed by Redis lookup."""
    mock_redis = AsyncMock()
    SemanticCacheService._redis_pool = mock_redis
    SemanticCacheService._initialized = True
    
    question = "Who made Vectra?"
    assistant_id = str(uuid4())
    cache_key = f"cache:{assistant_id}:hash123"
    expected_response = {"answer": "Google Deepmind team"}
    
    # 1. Redis exact match fails
    mock_redis.get.side_effect = [None, json.dumps(expected_response)]
    
    # 2. Qdrant find a match
    mock_hit = MagicMock()
    mock_hit.payload = {"cache_key": cache_key}
    mock_hit.score = 0.95
    
    mock_search_result = MagicMock()
    mock_search_result.points = [mock_hit]
    mock_qdrant.query_points.return_value = mock_search_result
    
    # Act
    result = await cache_service.get_cached_response(question, assistant_id, embedding=[0.1]*768)
    
    # Assert
    assert result == expected_response
    assert mock_qdrant.query_points.called
    assert mock_redis.get.call_count == 2 # 1 exact, 1 semantic lookup


@pytest.mark.asyncio
async def test_clear_assistant_cache_flow(cache_service, mock_qdrant):
    """Verify complete flow of cache clearing (Redis + Qdrant)."""
    mock_redis = AsyncMock()
    SemanticCacheService._redis_pool = mock_redis
    SemanticCacheService._initialized = True

    # Mock Redis SCAN
    mock_redis.scan.side_effect = [("0", ["key1", "key2"])] # cursor "0" stops search immediately here for simplicity

    # Mock Qdrant delete indirectly (it uses VectorRepository internally)
    with patch("app.repositories.vector_repository.VectorRepository.delete_by_assistant_id") as mock_delete_vec:
        await cache_service.clear_assistant_cache("123")
        
        # Verify Redis deletes
        mock_redis.delete.assert_called_with("key1", "key2")
        # Verify Qdrant delete
        mock_delete_vec.assert_awaited_once_with(CACHE_COLLECTION_NAME, "123")
