from unittest.mock import AsyncMock, MagicMock

import pytest
from llama_index.core.schema import NodeWithScore, TextNode

from app.core.rag.processors.synthesis import SynthesisProcessor
from app.core.rag.types import PipelineContext


@pytest.fixture
def pipeline_context():
    ctx = PipelineContext(
        user_message="Explain quantum physics",
        chat_history=[],
        language="en",
        assistant=MagicMock(),
        llm=MagicMock(),
        embed_model=MagicMock(),
        search_strategy=MagicMock(),
    )
    ctx.assistant.instructions = "Be concise."

    # Setup some nodes
    ctx.retrieved_nodes = [
        NodeWithScore(node=TextNode(text="Quantum physics is hard."), score=0.9),
        NodeWithScore(node=TextNode(text="Particles behave like waves."), score=0.8),
    ]
    return ctx


@pytest.mark.asyncio
async def test_synthesis_prompt_construction(pipeline_context):
    """Verify context and instructions are passed to LLM."""
    processor = SynthesisProcessor()

    # Mock LLM stream
    mock_stream = AsyncMock()
    pipeline_context.llm.astream_complete = AsyncMock(return_value=mock_stream)

    events = []
    async for event in processor.process(pipeline_context):
        events.append(event)

    # Check that LLM was called
    pipeline_context.llm.astream_complete.assert_awaited_once()

    # Verify arguments passed to LLM (Prompt check)
    call_args = pipeline_context.llm.astream_complete.call_args[0][0]
    assert "Be concise." in call_args
    assert "Quantum physics is hard." in call_args
    assert "Explain quantum physics" in call_args


@pytest.mark.asyncio
async def test_synthesis_streams_response(pipeline_context):
    """Verify response stream is yielded."""
    processor = SynthesisProcessor()
    mock_stream = AsyncMock()
    pipeline_context.llm.astream_complete = AsyncMock(return_value=mock_stream)

    events = []
    async for event in processor.process(pipeline_context):
        events.append(event)

    assert len(events) == 2
    assert events[0].type == "step"
    assert events[1].type == "response_stream"
    assert events[1].payload is mock_stream


@pytest.mark.asyncio
async def test_synthesis_propagates_error(pipeline_context):
    """Should raise exception without yielding error event (pipeline job)."""
    processor = SynthesisProcessor()
    pipeline_context.llm.astream_complete = AsyncMock(side_effect=Exception("API Limit"))

    events = []
    # Assert it raises
    with pytest.raises(Exception, match="API Limit"):
        async for event in processor.process(pipeline_context):
            events.append(event)

    # Verify only initial event yielded
    assert len(events) == 1
    assert events[0].type == "step"
    assert events[0].step_type == "synthesis"
    assert events[0].status == "running"
    # Bubbles up to pipeline
