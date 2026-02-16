import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.core.rag.processors.reranking import RerankingProcessor
from app.core.rag.types import PipelineContext, PipelineEvent
from llama_index.core.schema import NodeWithScore, TextNode


@pytest.fixture
def mock_ctx():
    assistant = MagicMock()
    assistant.use_reranker = True
    assistant.rerank_provider = "cohere"
    assistant.top_k_retrieval = 3
    assistant.top_n_rerank = 2
    assistant.similarity_cutoff = 0.5

    nodes = [
        NodeWithScore(node=TextNode(text="doc1", id_="1"), score=0.8),
        NodeWithScore(node=TextNode(text="doc2", id_="2"), score=0.7),
        NodeWithScore(node=TextNode(text="doc3", id_="3"), score=0.6),
    ]

    return PipelineContext(
        user_message="test query",
        chat_history=[],
        language="en",
        assistant=assistant,
        llm=None,
        embed_model=None,
        search_strategy=None,
        settings_service=AsyncMock(),
        retrieved_nodes=nodes,
    )


@pytest.mark.asyncio
async def test_reranking_happy_path(mock_ctx):
    processor = RerankingProcessor()
    
    # Mock Cohere client
    mock_cohere = AsyncMock()
    mock_result = MagicMock()
    mock_result.results = [
        MagicMock(index=1, relevance_score=0.9),  # doc2
        MagicMock(index=0, relevance_score=0.85),  # doc1
    ]
    mock_cohere.rerank.return_value = mock_result

    with patch("app.factories.rerank_factory.RerankProviderFactory.create_reranker", return_value=mock_cohere):
        events = []
        async for event in processor.process(mock_ctx):
            events.append(event)

    assert len(mock_ctx.retrieved_nodes) == 2
    assert mock_ctx.retrieved_nodes[0].node.text == "doc2"
    assert mock_ctx.retrieved_nodes[0].score == 0.9

    # Check events
    assert events[0].type == "step"
    assert events[0].status == "running"

    # Last events should be stats and sources
    assert events[-1].type == "sources"
    assert len(events[-1].payload) == 2


@pytest.mark.asyncio
async def test_reranking_disabled(mock_ctx):
    mock_ctx.assistant.use_reranker = False
    processor = RerankingProcessor()

    events = []
    async for event in processor.process(mock_ctx):
        events.append(event)

    assert len(mock_ctx.retrieved_nodes) == 3  # Untouched
    assert events[0].type == "step"
    assert "Skipped" in events[0].label


@pytest.mark.asyncio
async def test_reranking_fail_open_on_timeout(mock_ctx):
    processor = RerankingProcessor()
    mock_cohere = AsyncMock()
    mock_cohere.rerank.side_effect = asyncio.TimeoutError()

    with patch("app.factories.rerank_factory.RerankProviderFactory.create_reranker", return_value=mock_cohere):
        events = []
        async for event in processor.process(mock_ctx):
            events.append(event)

    # Should fallback to top_n_rerank original nodes
    assert len(mock_ctx.retrieved_nodes) == 2
    assert mock_ctx.retrieved_nodes[0].node.text == "doc1"
    assert any(e.type == "error" for e in events)


@pytest.mark.asyncio
async def test_reranking_cutoff_filtering(mock_ctx):
    processor = RerankingProcessor()
    mock_cohere = AsyncMock()

    # Mock Cohere response: one above cutoff, one below
    mock_result = MagicMock()
    mock_result.results = [
        MagicMock(index=0, relevance_score=0.9),  # Above (0.5)
        MagicMock(index=1, relevance_score=0.3),  # Below (0.5)
    ]
    mock_cohere.rerank.return_value = mock_result

    with patch("app.factories.rerank_factory.RerankProviderFactory.create_reranker", return_value=mock_cohere):
        async for _ in processor.process(mock_ctx):
            pass

    assert len(mock_ctx.retrieved_nodes) == 1
    assert mock_ctx.retrieved_nodes[0].node.text == "doc1"
