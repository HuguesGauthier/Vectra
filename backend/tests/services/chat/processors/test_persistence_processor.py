import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time
from app.services.chat.processors.persistence_processor import (
    UserPersistenceProcessor,
    AssistantPersistenceProcessor,
    ROLE_USER,
    ROLE_ASSISTANT
)
from app.services.chat.types import ChatContext

@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=ChatContext)
    ctx.session_id = "test-session"
    ctx.message = "Hello"
    ctx.language = "en"
    ctx.db = AsyncMock()
    ctx.chat_history_service = AsyncMock()
    ctx.chat_history_service.add_message = AsyncMock()
    ctx.metrics = MagicMock()
    ctx.assistant = MagicMock()
    ctx.assistant.id = "assistant-id"
    ctx.user_id = "user-id"
    
    # Assistant specific
    ctx.full_response_text = "Hi there"
    ctx.retrieved_sources = []
    ctx.visualization = None
    ctx.sql_results = []
    ctx.metadata = {}
    return ctx

@pytest.mark.asyncio
async def test_user_persistence_hot_and_cold(mock_context):
    processor = UserPersistenceProcessor()
    
    # Mock Postgres Repo via patch since it's instantiated inside
    with patch("app.services.chat.processors.persistence_processor.ChatPostgresRepository") as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.add_message = AsyncMock()
        
        async for _ in processor.process(mock_context):
            pass
            
        # Verify Hot Storage (Redis)
        mock_context.chat_history_service.add_message.assert_awaited_once_with(
            "test-session", ROLE_USER, "Hello"
        )
        
        # Verify Cold Storage (Postgres)
        mock_repo_instance.add_message.assert_awaited_once()
        call_args = mock_repo_instance.add_message.call_args
        assert call_args[0] == ("test-session", ROLE_USER, "Hello")
        assert call_args[1]["assistant_id"] == "assistant-id"

@pytest.mark.asyncio
async def test_assistant_persistence_sanitize_metadata(mock_context):
    processor = AssistantPersistenceProcessor()
    
    # Create non-serializable metadata
    class NonSerializable:
        pass
        
    mock_context.metadata = {"bad_obj": NonSerializable()}
    
    # We expect _sanitize_metadata to handle this gracefully (convert to str or empty dict if very bad)
    # The default=str should handle the object representation
    
    sanitized = processor._sanitize_metadata(mock_context.metadata)
    assert "bad_obj" in sanitized
    assert isinstance(sanitized["bad_obj"], str)

@pytest.mark.asyncio
async def test_assistant_persistence_call_flow(mock_context):
    processor = AssistantPersistenceProcessor()
    
    with patch("app.services.chat.processors.persistence_processor.ChatPostgresRepository") as MockRepo:
        mock_repo_instance = MockRepo.return_value
        mock_repo_instance.add_message = AsyncMock()
        
        async for _ in processor.process(mock_context):
            pass
            
        # Verify Hot Storage
        mock_context.chat_history_service.add_message.assert_awaited_once()
        
        # Verify Cold Storage
        mock_repo_instance.add_message.assert_awaited_once()

