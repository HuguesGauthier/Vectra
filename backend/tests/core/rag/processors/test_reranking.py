import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode

from app.core.rag.processors.reranking import RerankingProcessor
from app.core.rag.types import PipelineContext, PipelineEvent


@pytest.fixture
def mock_cohere_client():
    with patch("cohere.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance

        # Mock rerank return format
        mock_results = MagicMock()
        mock_results.results = [
            MagicMock(index=0, relevance_score=0.95),
            MagicMock(index=1, relevance_score=0.85),
        ]
        mock_instance.rerank.return_value = mock_results
        yield mock_instance


@pytest.fixture
def pipeline_context():
    ctx = PipelineContext(
        user_message="test query",
        chat_history=[],
        language="en",
        assistant=MagicMock(),
        llm=MagicMock(),
        embed_model=MagicMock(),
        search_strategy=MagicMock(),
    )
    # Default settings
    ctx.assistant.use_reranker = True
    ctx.assistant.top_n_rerank = 5

    # Setup nodes
    node1 = NodeWithScore(node=TextNode(id_="node1", text="text1"), score=0.5)
    node2 = NodeWithScore(node=TextNode(id_="node2", text="text2"), score=0.4)
    ctx.retrieved_nodes = [node1, node2]
    ctx.query_bundle = QueryBundle("test query")
    return ctx


@pytest.mark.asyncio
async def test_reranking_processor_skips_if_disabled(pipeline_context):
    pipeline_context.assistant.use_reranker = False
    processor = RerankingProcessor()

    events = []
    async for event in processor.process(pipeline_context):
        events.append(event)

    # Note: sources event is always emitted
    assert any(e.type == "sources" for e in events)
    assert any(e.label == "Skipped (Disabled)" for e in events if e.type == "step")


@pytest.mark.asyncio
async def test_reranking_processor_skips_if_no_nodes(pipeline_context):
    pipeline_context.retrieved_nodes = []
    processor = RerankingProcessor()

    events = []
    async for event in processor.process(pipeline_context):
        events.append(event)

    assert len(events) == 0


@pytest.mark.asyncio
async def test_reranking_flow_integration(pipeline_context, mock_cohere_client):
    """Test full flow with mocked Cohere."""
    with patch("app.core.rag.processors.reranking.settings") as mock_settings:
        mock_settings.COHERE_API_KEY = "fake-key"
        processor = RerankingProcessor()

        events = []
        async for event in processor.process(pipeline_context):
            events.append(event)

        assert len(events) >= 3
        assert any(e.type == "step" and e.status == "running" for e in events)
        assert any(e.status == "completed" for e in events if e.type == "step")


@pytest.mark.asyncio
async def test_reranking_fallback_on_error(pipeline_context):
    """Should fallback to original nodes on reranker or cutoff failure."""
    with patch("app.core.rag.processors.reranking.settings") as mock_settings:
        mock_settings.COHERE_API_KEY = "fake-key"
        processor = RerankingProcessor()
        
        # Mock rerank failure
        # We need to ensure the client exists because of our mock_settings
        with patch("cohere.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_cls.return_value = mock_instance
            mock_instance.rerank.side_effect = Exception("Exploded")
            
            # Re-init processor with mocked class
            processor = RerankingProcessor()
            
            events = []
            async for event in processor.process(pipeline_context):
                events.append(event)

            assert any(e.type == "error" for e in events)
            assert len(pipeline_context.retrieved_nodes) > 0


@pytest.mark.asyncio
async def test_reranking_skips_missing_key(pipeline_context):
    """Verify that reranking is skipped if API key is missing."""
    with patch("app.core.rag.processors.reranking.settings") as mock_settings:
        mock_settings.COHERE_API_KEY = None
        processor = RerankingProcessor()

        events = []
        async for event in processor.process(pipeline_context):
            events.append(event)

    assert any("Skipped (Missing API Key)" in (e.label or "") for e in events if e.type == "step")


@pytest.mark.asyncio
async def test_reranking_timeout_fallback(pipeline_context):
    """❌ Failure Case: LLM hangs -> Timeout Fallback."""
    from app.core.rag.processors.reranking import TIMEOUT_SECONDS
    
    with patch("app.core.rag.processors.reranking.settings") as mock_settings:
        mock_settings.COHERE_API_KEY = "fake-key"
        processor = RerankingProcessor()
        
        # Mock Cohere Hang
        async def infinite_sleep(*args, **kwargs):
            await asyncio.sleep(TIMEOUT_SECONDS + 0.1)
            raise asyncio.TimeoutError()

        if processor.client:
            processor.client.rerank = AsyncMock(side_effect=infinite_sleep)

        # Execute
        events = []
        async for event in processor.process(pipeline_context):
            events.append(event)

        # Assert
        assert len(pipeline_context.retrieved_nodes) == 2
        assert any(e.status == "completed" and e.payload.get("fallback") for e in events if e.type == "step")
