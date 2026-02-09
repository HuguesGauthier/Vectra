from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.rag.processors.vectorization import VectorizationProcessor
from app.core.rag.types import PipelineContext


@pytest.fixture
def pipeline_context():
    return PipelineContext(
        user_message="user query",
        chat_history=[],
        language="en",
        assistant=MagicMock(),
        llm=MagicMock(),
        embed_model=MagicMock(),
        search_strategy=MagicMock(),
    )


@pytest.mark.asyncio
async def test_vectorization_success(pipeline_context):
    """Should vectorize query and update context."""
    processor = VectorizationProcessor()

    # Mock Embedding
    pipeline_context.embed_model.aget_query_embedding = AsyncMock(return_value=[0.1, 0.2, 0.3])
    pipeline_context.rewritten_query = "rewritten"

    events = []
    async for event in processor.process(pipeline_context):
        events.append(event)

    assert len(events) == 2
    assert events[1].status == "completed"
    assert events[1].payload["embedding"] == [0.1, 0.2, 0.3]

    # Verify Context Updated
    assert pipeline_context.query_bundle is not None
    assert pipeline_context.query_bundle.query_str == "rewritten"
    assert pipeline_context.query_bundle.embedding == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_vectorization_uses_user_message_if_no_rewrite(pipeline_context):
    """Should fallback to user_message if rewritten_query is None."""
    processor = VectorizationProcessor()
    pipeline_context.rewritten_query = None
    pipeline_context.embed_model.aget_query_embedding = AsyncMock(return_value=[0.1])

    async for _ in processor.process(pipeline_context):
        pass

    pipeline_context.embed_model.aget_query_embedding.assert_awaited_with("user query")


@pytest.mark.asyncio
async def test_vectorization_propagates_error(pipeline_context):
    """Should raise exception without yielding error event (pipeline job)."""
    processor = VectorizationProcessor()
    pipeline_context.embed_model.aget_query_embedding = AsyncMock(side_effect=ValueError("Embedding Service Down"))

    events = []
    # Assert it raises
    with pytest.raises(ValueError, match="Embedding Service Down"):
        async for event in processor.process(pipeline_context):
            events.append(event)

    # Verify only initial event yielded
    assert len(events) == 1
    assert events[0].type == "step"
    assert events[0].status == "running"
    # No "error" event here, bubbling up to pipeline
