import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.chat_history_service import ChatHistoryService, MAX_CONTENT_LENGTH
from app.schemas.chat import Message

# --- Fixtures ---

@pytest.fixture
def mock_redis_repo():
    repo = AsyncMock()
    repo.WINDOW_SIZE = 10
    return repo

@pytest.fixture
def chat_service(mock_redis_repo):
    return ChatHistoryService(repository=mock_redis_repo)

# --- Tests ---

@pytest.mark.asyncio
async def test_add_message_truncation(chat_service, mock_redis_repo):
    """P0: Verify that massive messages are truncated to prevent DoS."""
    session_id = "session123"
    massive_content = "a" * (MAX_CONTENT_LENGTH + 100)
    
    # Act
    await chat_service.add_message(session_id, "user", massive_content)
    
    # Assert
    mock_redis_repo.push_message.assert_called_once()
    args, _ = mock_redis_repo.push_message.call_args
    assert len(args[1]["content"]) == MAX_CONTENT_LENGTH
    assert args[1]["content"] == massive_content[:MAX_CONTENT_LENGTH]


@pytest.mark.asyncio
async def test_get_history_fallback_and_hydration(chat_service, mock_redis_repo):
    """P1: Verify fallback to Postgres and efficient hydration in Redis."""
    session_id = "session123"
    
    # 1. Redis is empty
    mock_redis_repo.get_recent_messages.return_value = []
    
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
        history = await chat_service.get_history(session_id)
        
        # Assert
        assert len(history) == 2
        assert isinstance(history[0], Message)
        assert history[0].content == "hello"
        
        # Verify bulk hydration
        mock_redis_repo.push_messages.assert_awaited_once_with(session_id, postgres_messages)


@pytest.mark.asyncio
async def test_singleton_redis_lock():
    """P0: Verify thread-safe initialization of Redis client."""
    from app.services.chat_history_service import get_redis_client, _redis_lock
    import app.services.chat_history_service as chat_history_mod
    
    # Reset state
    chat_history_mod._redis_client = None
    
    with patch("app.services.chat_history_service.redis_from_url") as mock_from_url:
        mock_from_url.return_value = MagicMock()
        
        # Simultaneous calls
        await asyncio.gather(get_redis_client(), get_redis_client())
        
        # Should be called exactly once
        assert mock_from_url.call_count == 1
