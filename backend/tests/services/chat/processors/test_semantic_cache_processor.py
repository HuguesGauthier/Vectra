import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.chat.processors.semantic_cache_processor import SemanticCacheProcessor
from app.services.chat.types import ChatContext, PipelineStepType


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=ChatContext)
    ctx.metadata = {}
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
async def test_process_cache_hit_exact(mock_context):
    """Stage 1: Exact Match (No Embedding)"""
    # Setup
    processor = SemanticCacheProcessor()

    # Mock Cache Hit on FIRST call (exact match)
    cached_response = {"response": "Cached Answer", "sources": [{"metadata": "source1"}], "sql_results": [{"id": 1}]}
    mock_context.cache_service.get_cached_response.return_value = cached_response

    # Execute
    chunks = []
    async for chunk in processor.process(mock_context):
        chunks.append(chunk)

    # Assertions
    assert mock_context.should_stop is True
    assert mock_context.full_response_text == "Cached Answer"

    # Verify exact match check was called with embedding=None
    mock_context.cache_service.get_cached_response.assert_called_once()
    args, kwargs = mock_context.cache_service.get_cached_response.call_args
    assert kwargs["embedding"] is None

    # Verify Embedding was NOT called
    mock_context.vector_service.get_embedding_model.assert_not_called()


@pytest.mark.asyncio
async def test_process_cache_hit_semantic(mock_context):
    """Stage 2: Semantic Match (Requires Embedding)"""
    # Setup
    processor = SemanticCacheProcessor()

    # Mock Stage 1 Miss, Stage 2 Hit
    cached_response = {"response": "Semantic Answer", "sources": [], "sql_results": []}
    mock_context.cache_service.get_cached_response.side_effect = [None, cached_response]

    # Mock Embedding
    mock_embed_model = MagicMock()
    mock_embed_model.get_text_embedding.return_value = [0.1, 0.2, 0.3]
    mock_context.vector_service.get_embedding_model.return_value = mock_embed_model

    # Execute
    async for _ in processor.process(mock_context):
        pass

    # Assertions
    assert mock_context.should_stop is True
    assert mock_context.full_response_text == "Semantic Answer"

    # Verify both stages called
    assert mock_context.cache_service.get_cached_response.call_count == 2
    # Verify Stage 2 used the embedding
    last_call_kwargs = mock_context.cache_service.get_cached_response.call_args_list[1].kwargs
    assert last_call_kwargs["embedding"] == [0.1, 0.2, 0.3]


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
    assert mock_context.should_stop is False  # Pipeline continues

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
    assert mock_context.should_stop is False  # Should fail open (continue)

    # Verify we didn't crash
    # Metrics might not be recorded depending on where error happened (inside try, before record step)
    # in code: record step is lines 76-81, execute cache is line 69. Exception at 69 jumps to 92.
    # So record_completed_step is SKIPPED in case of error. This is acceptable for P0 (no crash).
