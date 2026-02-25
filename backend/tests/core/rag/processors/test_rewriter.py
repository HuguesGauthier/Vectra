import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.rag.processors.rewriter import QueryRewriterProcessor
from app.core.rag.types import PipelineContext, PipelineEvent


@pytest.fixture
def mock_ctx():
    assistant = MagicMock()
    # history < 3 messages should skip
    history = [MagicMock(role="user", content="hi"), MagicMock(role="assistant", content="hello")]

    return PipelineContext(
        user_message="test query",
        chat_history=history,
        language="en",
        assistant=assistant,
        llm=AsyncMock(),
        embed_model=None,
        search_strategy=None,
    )


@pytest.mark.asyncio
async def test_rewriter_skip_insufficient_history(mock_ctx):
    processor = QueryRewriterProcessor()

    events = []
    async for event in processor.process(mock_ctx):
        events.append(event)

    assert mock_ctx.rewritten_query == "test query"
    assert len(events) == 0  # No events yielded when skipped


@pytest.mark.asyncio
async def test_rewriter_happy_path(mock_ctx):
    # Add enough history to trigger rewrite
    mock_ctx.chat_history.append(MagicMock(role="user", content="how are you?"))

    processor = QueryRewriterProcessor()

    # Mock LLM response
    mock_resp = MagicMock()
    mock_resp.text = "Standalone question"
    mock_ctx.llm.acomplete.return_value = mock_resp

    events = []
    async for event in processor.process(mock_ctx):
        events.append(event)

    assert mock_ctx.rewritten_query == "Standalone question"
    assert events[0].type == "step"
    assert events[0].status == "running"
    assert events[1].type == "step"
    assert events[1].status == "completed"
    assert events[1].payload["query"] == "Standalone question"


@pytest.mark.asyncio
async def test_rewriter_fallback_on_error(mock_ctx):
    # Add enough history to trigger rewrite
    mock_ctx.chat_history.append(MagicMock(role="user", content="how are you?"))

    processor = QueryRewriterProcessor()
    mock_ctx.llm.acomplete.side_effect = Exception("LLM Error")

    events = []
    async for event in processor.process(mock_ctx):
        events.append(event)

    # Should fallback to original message
    assert mock_ctx.rewritten_query == "test query"
    assert events[1].status == "completed"
    assert events[1].payload["query"] == "test query"
