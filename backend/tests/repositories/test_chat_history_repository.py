import pytest
import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch, call
from sqlalchemy.exc import SQLAlchemyError
from app.repositories.chat_history_repository import ChatRedisRepository, ChatPostgresRepository
from app.core.exceptions import TechnicalError

# --- ChatRedisRepository Tests ---


@pytest.fixture
def mock_redis():
    return AsyncMock()


@pytest.fixture
def redis_repo(mock_redis):
    return ChatRedisRepository(redis_client=mock_redis)


@pytest.mark.asyncio
async def test_redis_push_messages_success(redis_repo, mock_redis):
    """Test pushing messages to Redis."""
    session_id = "test-session"
    messages = [{"role": "user", "content": "Hello"}]

    # Mock pipeline: Context manager is async, methods are sync, execute is async
    # Redis pipeline() returns a context manager
    mock_redis.pipeline = MagicMock()

    # The pipeline object itself (used inside the 'with' block)
    pipeline = MagicMock()
    pipeline.execute = AsyncMock()

    # The context manager returned by pipeline()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=pipeline)
    ctx.__aexit__ = AsyncMock()

    # pipeline() returns the context manager
    mock_redis.pipeline.return_value = ctx

    await redis_repo.push_messages(session_id, messages)

    # Verify calls
    key = redis_repo._get_key(session_id)
    pipeline.rpush.assert_called_once()
    pipeline.ltrim.assert_called_once()
    pipeline.expire.assert_called_once()
    pipeline.execute.assert_called_once()


@pytest.mark.asyncio
async def test_redis_push_messages_empty(redis_repo, mock_redis):
    """Test pushing empty messages list."""
    await redis_repo.push_messages("session", [])
    mock_redis.pipeline.assert_not_called()


@pytest.mark.asyncio
async def test_redis_get_recent_messages_success(redis_repo, mock_redis):
    """Test retrieving messages from Redis."""
    session_id = "test-session"
    messages = [{"role": "user", "content": "Hello"}]

    mock_redis.lrange.return_value = [json.dumps(msg).encode() for msg in messages]

    result = await redis_repo.get_recent_messages(session_id)

    assert len(result) == 1
    assert result[0]["content"] == "Hello"


@pytest.mark.asyncio
async def test_redis_get_recent_messages_malformed(redis_repo, mock_redis):
    """Test retrieving malformed messages."""
    session_id = "test-session"
    mock_redis.lrange.return_value = [b"invalid-json"]

    result = await redis_repo.get_recent_messages(session_id)

    assert result == []


@pytest.mark.asyncio
async def test_redis_clear(redis_repo, mock_redis):
    """Test clearing Redis history."""
    session_id = "test-session"
    await redis_repo.clear(session_id)
    mock_redis.delete.assert_called_once()


# --- ChatPostgresRepository Tests ---


@pytest.fixture
def mock_db():
    mock = AsyncMock()
    mock.add = MagicMock()
    return mock


@pytest.fixture(autouse=True)
def mock_select():
    """Patch sqlalchemy select."""
    with patch("app.repositories.chat_history_repository.select") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_delete():
    """Patch sqlalchemy delete."""
    with patch("app.repositories.chat_history_repository.delete") as mock:
        yield mock


@pytest.fixture
def postgres_repo(mock_db):
    return ChatPostgresRepository(db=mock_db)


@pytest.mark.asyncio
async def test_postgres_add_message_success(postgres_repo, mock_db):
    """Test adding message to Postgres."""
    await postgres_repo.add_message(session_id="session", role="user", content="Hello")

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_postgres_add_message_error(postgres_repo, mock_db):
    """Test error handling in add_message."""
    mock_db.commit.side_effect = SQLAlchemyError("DB Error")

    # Should log error but not raise (as per implementation)
    await postgres_repo.add_message("session", "user", "msg")

    mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_postgres_get_messages_success(postgres_repo, mock_db):
    """Test getting messages from Postgres."""
    mock_msg = MagicMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_msg]
    mock_db.execute.return_value = mock_result

    result = await postgres_repo.get_messages("session")

    assert len(result) == 1
    assert result[0] == mock_msg


@pytest.mark.asyncio
async def test_postgres_clear_history_success(postgres_repo, mock_db):
    """Test clearing Postgres history."""
    mock_result = MagicMock()
    mock_result.rowcount = 5
    mock_db.execute.return_value = mock_result

    result = await postgres_repo.clear_history("session")

    assert result is True
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_postgres_purge_old_messages(postgres_repo, mock_db):
    """Test purging old messages."""
    mock_result = MagicMock()
    mock_result.rowcount = 10
    mock_db.execute.return_value = mock_result

    count = await postgres_repo.purge_old_messages(retention_days=30)

    assert count == 10
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_postgres_get_last_n_messages(postgres_repo, mock_db):
    """Test getting last N messages."""
    # Create mock messages
    msg1 = MagicMock()
    msg1.role = "user"
    msg1.content = "Older"

    msg2 = MagicMock()
    msg2.role = "assistant"
    msg2.content = "Newer"

    # DB returns them in descending order (Newer, Older)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [msg2, msg1]
    mock_db.execute.return_value = mock_result

    result = await postgres_repo.get_last_n_messages("session", limit=2)

    # Result should be reversed -> chronological (Older, Newer)
    assert len(result) == 2
    assert result[0]["content"] == "Older"
    assert result[1]["content"] == "Newer"
