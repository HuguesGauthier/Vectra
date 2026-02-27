import pytest
import json
from unittest.mock import AsyncMock, MagicMock
from app.core.rag.processors.synthesis import SynthesisProcessor
from app.core.rag.types import PipelineContext, PipelineEvent
from llama_index.core.schema import NodeWithScore, TextNode


@pytest.fixture
def mock_ctx():
    assistant = MagicMock()
    assistant.instructions = "Instructions"

    node = NodeWithScore(node=TextNode(text="Context"), score=0.8)

    return PipelineContext(
        user_message="test query",
        chat_history=[],
        language="en",
        assistant=assistant,
        llm=AsyncMock(),
        embed_model=None,
        search_strategy=None,
        retrieved_nodes=[node],
    )


@pytest.mark.asyncio
async def test_synthesis_happy_path(mock_ctx):
    processor = SynthesisProcessor()

    # Mock LLM streaming response
    mock_chunk = MagicMock()
    mock_chunk.delta = "Hello"
    mock_stream = AsyncMock()
    mock_stream.__aiter__.return_value = [mock_chunk]
    mock_ctx.llm.astream_chat.return_value = mock_stream

    events = []
    async for event in processor.process(mock_ctx):
        events.append(event)

    assert events[0].type == "step"
    assert events[0].status == "running"

    # Synthesis now yields tokens char-by-char through StreamBlockParser
    tokens = [e.payload for e in events if e.type == "token"]
    assert "".join(tokens) == "Hello"

    assert events[-1].type == "step"
    assert events[-1].status == "completed"
    assert "tokens" in events[-1].payload


@pytest.mark.asyncio
async def test_synthesis_json_cleaning(mock_ctx):
    # Test JSON cleaning logic
    json_node = NodeWithScore(node=TextNode(text=json.dumps({"text": "Real content", "junk": "data"})), score=0.9)
    mock_ctx.retrieved_nodes = [json_node]

    processor = SynthesisProcessor()

    async for _ in processor.process(mock_ctx):
        pass

    # Verify that the content passed to format prompt was cleaned
    call_args = mock_ctx.llm.astream_chat.call_args[0][0]
    user_msg = call_args[-1].content
    assert "Real content" in user_msg
    assert "junk" not in user_msg


@pytest.mark.asyncio
async def test_synthesis_json_node_content_cleaning(mock_ctx):
    # Test complex node cleaning (LlamaIndex style)
    content = {"text": "Cleaned text"}
    json_node = NodeWithScore(node=TextNode(text=json.dumps({"_node_content": json.dumps(content)})), score=0.9)
    mock_ctx.retrieved_nodes = [json_node]

    processor = SynthesisProcessor()

    async for _ in processor.process(mock_ctx):
        pass

    call_args = mock_ctx.llm.astream_chat.call_args[0][0]
    user_msg = call_args[-1].content
    assert "Cleaned text" in user_msg


@pytest.mark.asyncio
async def test_synthesis_error_handling(mock_ctx):
    processor = SynthesisProcessor()
    mock_ctx.llm.astream_chat.side_effect = Exception("LLM Error")

    with pytest.raises(Exception):
        async for _ in processor.process(mock_ctx):
            pass
