import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from uuid import uuid4
from app.services.chat.processors.trending_processor import TrendingProcessor, TIMEOUT_TRENDING_ANALYSIS
from app.services.chat.types import ChatContext

@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=ChatContext)
    ctx.session_id = str(uuid4())
    ctx.message = "Hello world"
    ctx.language = "en"
    ctx.db = AsyncMock()
    ctx.settings_service = AsyncMock()
    ctx.vector_service = AsyncMock()
    ctx.assistant = MagicMock()
    ctx.assistant.id = "assistant-id"
    ctx.assistant.linked_connectors = []
    
    # Defaults for eligibility
    ctx.trending_enabled = True
    ctx.question_embedding = [0.1, 0.2, 0.3]
    ctx.captured_source_embedding = None
    
    # Metrics for usage
    ctx.user_id = str(uuid4())
    ctx.start_time = 1000.0
    ctx.metrics = {}
    
    return ctx

@pytest.mark.asyncio
async def test_should_run_trending_true(mock_context):
    processor = TrendingProcessor()
    assert processor._should_run_trending(mock_context) is True

@pytest.mark.asyncio
async def test_should_run_trending_false_disabled(mock_context):
    processor = TrendingProcessor()
    mock_context.trending_enabled = False
    assert processor._should_run_trending(mock_context) is False

@pytest.mark.asyncio
async def test_should_run_trending_false_no_embedding(mock_context):
    processor = TrendingProcessor()
    mock_context.question_embedding = None
    mock_context.captured_source_embedding = None
    assert processor._should_run_trending(mock_context) is False

@pytest.mark.asyncio
async def test_execute_trending_safe_success(mock_context):
    processor = TrendingProcessor()
    
    with patch("app.services.chat.processors.trending_processor.TrendingService") as MockService, \
         patch("app.services.chat.processors.trending_processor.TopicRepository"):
        
        mock_svc = MockService.return_value
        mock_svc.process_user_question = AsyncMock()
        
        async for _ in processor._execute_trending_safe(mock_context):
            pass
            
        mock_svc.process_user_question.assert_awaited_once()

@pytest.mark.asyncio
async def test_execute_trending_safe_timeout(mock_context):
    processor = TrendingProcessor()
    
    with patch("app.services.chat.processors.trending_processor.TrendingService") as MockService, \
         patch("app.services.chat.processors.trending_processor.TopicRepository"):
        
        mock_svc = MockService.return_value
        # Simulate a task that takes longer than the timeout
        async def slow_process(*args, **kwargs):
            await asyncio.sleep(TIMEOUT_TRENDING_ANALYSIS + 0.1)
            
        mock_svc.process_user_question = AsyncMock(side_effect=slow_process)
        
        # We need to mock wait_for to actually raise TimeoutError because 
        # real time sleeping in tests is flaky and slow.
        # But here we want to verifying the processor HANDLES the timeout.
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            async for _ in processor._execute_trending_safe(mock_context):
                pass
        
        # Should not raise exception, just log and finish

@pytest.mark.asyncio
async def test_persist_usage_statistics_safe(mock_context):
    processor = TrendingProcessor()
    
    with patch("app.services.chat.processors.trending_processor.UsageRepository") as MockRepo:
        # Mock DB add/commit
        mock_context.db.add = MagicMock()
        mock_context.db.commit = AsyncMock()
        
        await processor._persist_usage_statistics_safe(mock_context)
        
        mock_context.db.add.assert_called_once()
        mock_context.db.commit.assert_awaited_once()
