import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.chat.processors.semantic_cache_processor import SemanticCacheProcessor
from app.services.chat.types import ChatContext, PipelineStepType

@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=ChatContext)
    ctx.session_id = "test_session"
    ctx.original_message = "test question"
    ctx.language = "en"
    ctx.assistant = MagicMock()
    ctx.assistant.id = "assistant_123"
    ctx.assistant.use_semantic_cache = True
    ctx.assistant.cache_similarity_threshold = 0.9
    ctx.cache_service = AsyncMock()
    ctx.vector_service = AsyncMock()
    ctx.metrics = MagicMock()
    ctx.should_stop = False
    return ctx

@pytest.mark.asyncio
async def test_process_cache_hit(mock_context):
    # Setup
    processor = SemanticCacheProcessor()
    
    # Mock Embedding
    mock_embed_model = MagicMock()
    # get_text_embedding is synchronous in the model, but we wrapped it in to_thread
    mock_embed_model.get_text_embedding.return_value = [0.1, 0.2, 0.3]
    mock_context.vector_service.get_embedding_model.return_value = mock_embed_model
    
    # Mock Cache Hit
    cached_response = {
        "response": "Cached Answer",
        "sources": [{"metadata": "source1"}],
        "sql_results": [{"id": 1}]
    }
    mock_context.cache_service.get_cached_response.return_value = cached_response

    # Execute
    chunks = []
    async for chunk in processor.process(mock_context):
        chunks.append(chunk)

    # Assertions
    assert mock_context.should_stop is True
    assert mock_context.full_response_text == "Cached Answer"
    assert mock_context.sql_results == [{"id": 1}]
    
    # Verify Metrics
    mock_context.metrics.record_completed_step.assert_called_with(
        step_type=PipelineStepType.CACHE_LOOKUP,
        label="Cache Lookup",
        duration=pytest.approx(0, abs=1), # Duration is small
        payload={"hit": True}
    )
    
    # Verify Embedding called (it was offloaded to thread, so we verify the model method was called)
    mock_embed_model.get_text_embedding.assert_called_with("test question")

@pytest.mark.asyncio
async def test_process_cache_miss(mock_context):
    # Setup
    processor = SemanticCacheProcessor()
    
    mock_embed_model = MagicMock()
    mock_embed_model.get_text_embedding.return_value = [0.1, 0.2, 0.3]
    mock_context.vector_service.get_embedding_model.return_value = mock_embed_model
    
    # Mock Cache Miss
    mock_context.cache_service.get_cached_response.return_value = None

    # Execute
    chunks = []
    async for chunk in processor.process(mock_context):
        chunks.append(chunk)

    # Assertions
    assert mock_context.should_stop is False # Pipeline continues
    
    # Verify Metrics: Hit = False
    args, kwargs = mock_context.metrics.record_completed_step.call_args
    assert kwargs["payload"]["hit"] is False

@pytest.mark.asyncio
async def test_process_error_fail_open(mock_context):
    # Setup
    processor = SemanticCacheProcessor()
    
    mock_embed_model = MagicMock()
    mock_embed_model.get_text_embedding.return_value = [0.1, 0.2, 0.3]
    mock_context.vector_service.get_embedding_model.return_value = mock_embed_model
    
    # Mock Error in Cache Service
    mock_context.cache_service.get_cached_response.side_effect = Exception("Redis Down")

    # Execute
    chunks = []
    async for chunk in processor.process(mock_context):
        chunks.append(chunk)

    # Assertions
    assert mock_context.should_stop is False # Should fail open (continue)
    
    # Verify we didn't crash
    # Metrics might not be recorded depending on where error happened (inside try, before record step)
    # in code: record step is lines 76-81, execute cache is line 69. Exception at 69 jumps to 92.
    # So record_completed_step is SKIPPED in case of error. This is acceptable for P0 (no crash).
