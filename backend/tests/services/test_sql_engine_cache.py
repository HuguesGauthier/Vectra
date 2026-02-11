import pytest
import time
from uuid import uuid4
from app.services.sql_engine_cache import SQLEngineCache


@pytest.fixture
def cache():
    return SQLEngineCache(max_size=3, ttl_seconds=2)


def test_cache_set_get(cache):
    a_id = uuid4()
    c_id = uuid4()
    engine = "engine_instance"

    cache.set_engine(a_id, c_id, engine)
    retrieved = cache.get_engine(a_id, c_id)

    assert retrieved == engine


def test_cache_ttl_expiration(cache):
    a_id = uuid4()
    c_id = uuid4()
    cache.set_engine(a_id, c_id, "engine")

    # Wait for TTL to expire
    time.sleep(2.1)

    assert cache.get_engine(a_id, c_id) is None


def test_cache_lru_eviction(cache):
    # Cache size is 3
    ids = [(uuid4(), uuid4()) for _ in range(4)]

    for i in range(3):
        cache.set_engine(ids[i][0], ids[i][1], f"engine_{i}")

    # Access the first one to make it most recent
    cache.get_engine(ids[0][0], ids[0][1])

    # Add 4th one, should evict the 2nd one (index 1) which is LRU
    cache.set_engine(ids[3][0], ids[3][1], "engine_3")

    assert cache.get_engine(ids[1][0], ids[1][1]) is None
    assert cache.get_engine(ids[0][0], ids[0][1]) == "engine_0"
    assert cache.get_engine(ids[2][0], ids[2][1]) == "engine_2"
    assert cache.get_engine(ids[3][0], ids[3][1]) == "engine_3"


def test_invalidate_assistant(cache):
    a_id = uuid4()
    c1_id = uuid4()
    c2_id = uuid4()

    cache.set_engine(a_id, c1_id, "engine1")
    cache.set_engine(a_id, c2_id, "engine2")
    cache.set_engine(uuid4(), uuid4(), "engine3")

    count = cache.invalidate_assistant(a_id)
    assert count == 2
    assert cache.get_engine(a_id, c1_id) is None
    assert cache.get_engine(a_id, c2_id) is None
    assert len(cache._cache) == 1


def test_invalidate_connector(cache):
    a1_id = uuid4()
    a2_id = uuid4()
    c_id = uuid4()

    cache.set_engine(a1_id, c_id, "engine1")
    cache.set_engine(a2_id, c_id, "engine2")

    count = cache.invalidate_connector(c_id)
    assert count == 2
    assert cache.get_engine(a1_id, c_id) is None
    assert cache.get_engine(a2_id, c_id) is None


def test_clear(cache):
    cache.set_engine(uuid4(), uuid4(), "e1")
    cache.set_engine(uuid4(), uuid4(), "e2")

    assert cache.clear() == 2
    assert len(cache._cache) == 0
