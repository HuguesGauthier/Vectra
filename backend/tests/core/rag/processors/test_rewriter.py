from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.rag.processors.rewriter import QueryRewriterProcessor
from app.core.rag.types import PipelineContext


@pytest.fixture
def pipeline_context():
    return PipelineContext(
        user_message="current question",
        chat_history=[],
        language="en",
        assistant=MagicMock(),
        llm=MagicMock(),
        embed_model=MagicMock(),
        search_strategy=MagicMock(),
    )


@pytest.mark.asyncio
async def test_rewriter_no_history(pipeline_context):
    """Should skip generic rewrite if no chat history."""
    processor = QueryRewriterProcessor()
    pipeline_context.chat_history = []

    events = []
    async for event in processor.process(pipeline_context):
        events.append(event)

    assert len(events) == 0
    assert pipeline_context.rewritten_query == "current question"


@pytest.mark.asyncio
async def test_rewriter_with_history(pipeline_context):
    """Should rewrite query using LLM if history exists."""
    processor = QueryRewriterProcessor()

    # Mock History
    msg_mock = MagicMock()
    msg_mock.role = "user"
    msg_mock.content = "prev question"
    pipeline_context.chat_history = [msg_mock]

    # Mock LLM
    mock_response = MagicMock()
    mock_response.text = " rewritten question "
    pipeline_context.llm.acomplete = AsyncMock(return_value=mock_response)

    events = []
    async for event in processor.process(pipeline_context):
        events.append(event)

    assert len(events) == 2
    assert events[1].status == "completed"
    assert events[1].payload == "rewritten question"
    assert pipeline_context.rewritten_query == "rewritten question"

    pipeline_context.llm.acomplete.assert_awaited_once()


@pytest.mark.asyncio
async def test_rewriter_fallback_on_error(pipeline_context):
    """Should fallback to original question on LLM error."""
    processor = QueryRewriterProcessor()

    msg_mock = MagicMock()
    msg_mock.role = "user"
    msg_mock.content = "prev"
    pipeline_context.chat_history = [msg_mock]

    # Error Mock
    pipeline_context.llm.acomplete = AsyncMock(side_effect=Exception("LLM Down"))

    events = []
    async for event in processor.process(pipeline_context):
        events.append(event)

    assert len(events) == 2
    # Should NOT be error, but completed with fallback
    assert events[1].type == "step"
    assert events[1].status == "completed"
    assert events[1].payload == "current question"

    # Fallback check
    assert pipeline_context.rewritten_query == "current question"
