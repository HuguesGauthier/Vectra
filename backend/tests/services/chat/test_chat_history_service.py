from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import MAX_CONTENT_LENGTH, Message, MessageRole
from app.services.chat_history_service import (ChatHistoryService,
                                               get_redis_client)


@pytest.fixture
def mock_repository():
    return AsyncMock()


@pytest.fixture
def service(mock_repository):
    return ChatHistoryService(mock_repository)


@pytest.mark.asyncio
async def test_add_message_valid(service, mock_repository):
    """Test adding a normal valid message."""
    await service.add_message("session_123", "user", "Hello World")

    mock_repository.push_message.assert_called_once()
    call_args = mock_repository.push_message.call_args[0]
    assert call_args[0] == "session_123"
    assert call_args[1] == {"role": "user", "content": "Hello World"}


@pytest.mark.asyncio
async def test_add_message_truncate_massive_content(service, mock_repository):
    """Test that massive messages are truncated to MAX_CONTENT_LENGTH."""
    massive_content = "A" * (MAX_CONTENT_LENGTH + 100)
    await service.add_message("session_overflow", "user", massive_content)

    mock_repository.push_message.assert_called_once()
    stored_data = mock_repository.push_message.call_args[0][1]

    assert len(stored_data["content"]) == MAX_CONTENT_LENGTH
    assert stored_data["content"] == "A" * MAX_CONTENT_LENGTH


@pytest.mark.asyncio
async def test_get_history_deserialize(service, mock_repository):
    """Test validation and deserialization of history items."""
    mock_repository.get_recent_messages.return_value = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
        {"role": "invalid", "content": "Skipped"},  # Should be skipped or error handled if validation strict
    ]

    # Note: MessageRole enum validation will fail for "invalid" role during Message(**item)

    history = await service.get_history("session_123")

    assert history[0].content == "Hi"
    assert history[1].role == MessageRole.ASSISTANT
    assert history[1].content == "Hello"


@pytest.mark.asyncio
async def test_get_history_fallback_and_hydration(service, mock_repository):
    """P1: Verify fallback to Postgres and efficient hydration in Redis."""
    session_id = "session123"

    # 1. Redis is empty
    mock_repository.get_recent_messages.return_value = []

    # 2. Postgres has messages (Return dicts compatible with Message schema)
    postgres_messages = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"}
    ]

    # Mocking BOTH the DB session and the Postgres repo call
    # Note: Import of SessionLocal, ChatPostgresRepository happens inside get_history
    with patch("app.core.database.SessionLocal") as mock_session_cls, \
         patch("app.repositories.chat_history_repository.ChatPostgresRepository") as mock_pg_repo_cls:

        mock_session = AsyncMock()
        mock_session_cls.return_value = mock_session

        mock_pg_repo = AsyncMock()
        mock_pg_repo.get_last_n_messages.return_value = postgres_messages
        mock_pg_repo_cls.return_value = mock_pg_repo

        # Act
        history = await service.get_history(session_id)

        # Assert
        assert len(history) == 2
        assert isinstance(history[0], Message)
        assert history[0].content == "hello"

        # Verify bulk hydration
        mock_repository.push_messages.assert_awaited_once_with(session_id, postgres_messages)


@pytest.mark.asyncio
async def test_redis_singleton():
    """Test that get_redis_client returns the same instance."""
    # We need to patch redis_from_url to properly mock initialization
    with patch("app.services.chat_history_service.redis_from_url") as mock_redis_ctor:
        mock_client = MagicMock()
        mock_redis_ctor.return_value = mock_client

        # Reset global state for test (unsafe in parallel but ok for unit test here)
        import app.services.chat_history_service as svc

        svc._redis_client = None

        client1 = await get_redis_client()
        client2 = await get_redis_client()

        assert client1 is client2
        assert client1 is mock_client
        mock_redis_ctor.assert_called_once()  # Should only be called once


@pytest.mark.asyncio
async def test_singleton_redis_lock():
    """P0: Verify thread-safe initialization of Redis client."""
    from app.services.chat_history_service import get_redis_client, _redis_lock
    import app.services.chat_history_service as chat_history_mod
    import asyncio

    # Reset state
    chat_history_mod._redis_client = None

    with patch("app.services.chat_history_service.redis_from_url") as mock_from_url:
        mock_from_url.return_value = MagicMock()

        # Simultaneous calls
        await asyncio.gather(get_redis_client(), get_redis_client())

        # Should be called exactly once
        assert mock_from_url.call_count == 1
