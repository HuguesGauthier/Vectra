from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.cache_service import SemanticCacheService


@pytest.fixture
def mock_qdrant():
    return AsyncMock()


@pytest.mark.asyncio
async def test_singleton_redis_initialization(mock_qdrant):
    """
    P0: Verify that Redis connection is initialized only once (Singleton).
    """
    # Reset singleton state for test
    SemanticCacheService._redis_pool = None
    SemanticCacheService._initialized = False

    service1 = SemanticCacheService(mock_qdrant)
    service2 = SemanticCacheService(mock_qdrant)

    with patch("redis.asyncio.from_url", new_callable=AsyncMock) as mock_redis_cls:
        mock_client = AsyncMock()
        mock_redis_cls.return_value = mock_client

        # Parallel initialization attempt
        import asyncio

        await asyncio.gather(service1.initialize(), service2.initialize())

        # Should be called exactly ONCE due to lock
        assert mock_redis_cls.call_count == 1
        assert SemanticCacheService._redis_pool is not None


@pytest.mark.asyncio
async def test_clear_assistant_cache_flow(mock_qdrant):
    """
    Verify complete flow of cache clearing (Redis + Qdrant).
    """
    service = SemanticCacheService(mock_qdrant)

    # Mock initialized state
    mock_redis = AsyncMock()
    SemanticCacheService._redis_pool = mock_redis
    SemanticCacheService._initialized = True

    # Mock Redis SCAN
    # First call returns (cursor="1", [key1]), Second (cursor="0", [key2])
    mock_redis.scan.side_effect = [("1", ["cache:123:abc"]), ("0", ["cache:123:def"])]

    deleted_count = await service.clear_assistant_cache("123")

    # Verify Redis deletes
    assert mock_redis.delete.call_count == 2
    assert deleted_count == 2

    # Verify Qdrant delete with filter
    mock_qdrant.delete.assert_called_once()
    args, kwargs = mock_qdrant.delete.call_args
    assert kwargs["collection_name"] == "semantic_cache"
    # Inspect filter structure if needed, but existence of call is main check here.
