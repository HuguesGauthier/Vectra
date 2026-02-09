from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode

from app.core.rag.processors.reranking import (FlashRankRerank,
                                               RerankingProcessor)
from app.core.rag.types import PipelineContext, PipelineEvent


@pytest.fixture
def mock_flashrank_package():
    with patch.dict("sys.modules", {"flashrank": MagicMock()}):
        mock_ranker_cls = MagicMock()
        mock_ranker_instance = MagicMock()
        mock_ranker_cls.return_value = mock_ranker_instance

        # Mock rerank return format
        mock_ranker_instance.rerank.return_value = [
            {"id": "node1", "score": 0.95, "meta": {}},
            {"id": "node2", "score": 0.85, "meta": {}},
        ]

        with patch("flashrank.Ranker", mock_ranker_cls), patch("flashrank.RerankRequest", MagicMock()):
            yield mock_ranker_instance


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
    ctx.assistant.reranker_provider = "flashrank"
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

    assert len(events) == 1
    assert events[0].type == "sources"


@pytest.mark.asyncio
async def test_reranking_processor_skips_if_no_nodes(pipeline_context):
    pipeline_context.retrieved_nodes = []
    processor = RerankingProcessor()

    events = []
    async for event in processor.process(pipeline_context):
        events.append(event)

    assert len(events) == 0


@pytest.mark.asyncio
async def test_reranking_flow_integration(pipeline_context, mock_flashrank_package):
    """Test full flow with mocked FlashRank."""
    processor = RerankingProcessor()

    # Clean cache to ensure Ranker is created
    FlashRankRerank._loaded_rankers.clear()

    events = []
    async for event in processor.process(pipeline_context):
        events.append(event)

    assert len(events) == 3
    assert events[0].type == "step"
    assert events[0].status == "running"

    # Verify nodes are updated
    # Similarity Cutoff (0.7) usually filters out verify logic,
    # BUT here we are mocking FlashRank or using context.
    # Actually wait -> The RerankingProcessor applies SimilarityPostprocessor(0.70) first!
    # Our dummy nodes have score=0.5/0.4. They'll be filtered OUT by strict cutoff!
    # We must update initial scores or mock cutoff behavior.

    # Reset nodes that were filtered out in previous run
    node1 = NodeWithScore(node=TextNode(id_="node1", text="text1"), score=0.8)
    node2 = NodeWithScore(node=TextNode(id_="node2", text="text2"), score=0.9)
    pipeline_context.retrieved_nodes = [node1, node2]

    # Re-run
    events = []
    async for event in processor.process(pipeline_context):
        events.append(event)

    assert len(events) >= 3
    assert events[1].status == "completed"
    assert "count" in events[1].payload


def test_flashrank_caching(mock_flashrank_package):
    """Verify singleton caching behavior."""
    FlashRankRerank._loaded_rankers.clear()

    # First init
    fr1 = FlashRankRerank(model="test-model")
    assert "test-model" in FlashRankRerank._loaded_rankers

    # Second init (should use cache)
    with patch("flashrank.Ranker") as mock_cls:
        fr2 = FlashRankRerank(model="test-model")
        mock_cls.assert_not_called()
        assert fr1._ranker is fr2._ranker


@pytest.mark.asyncio
async def test_reranking_fallback_on_error(pipeline_context):
    """Should fallback to original nodes on reranker or cutoff failure."""
    processor = RerankingProcessor()

    # Mock cutoff or reranker to raise
    # Since we can't easily mock inner FlashRank import failure here without patching sys.modules again,
    # let's mock SimilarityPostprocessor to raise, which is the first step.

    with patch(
        "app.core.rag.processors.reranking.SimilarityPostprocessor", side_effect=ValueError("Sim Cutoff Exploded")
    ):
        events = []
        async for event in processor.process(pipeline_context):
            events.append(event)

        assert len(events) == 4
        # 1. Step Running
        # 2. Error
        # 3. Sources (fallback)
        # 4. Step Completed (fallback)

        assert events[3].type == "step"
        assert events[3].status == "completed"
        assert events[3].payload["fallback"] is True

        # Verify nodes untouched (still has 2 nodes)
        assert len(pipeline_context.retrieved_nodes) == 2


@pytest.mark.asyncio
async def test_reranking_supports_local_alias(pipeline_context, mock_flashrank_package):
    """Verify that 'local' provider triggers FlashRank logic."""
    pipeline_context.assistant.reranker_provider = "local"

    # Ensure scores pass similarity cutoff (0.5 default in assistant model, but test fixture might set differently?)
    # pipeline_context fixture uses MagicMock for assistant. defaults?
    # RerankingProcessor uses getattr(ctx.assistant, "similarity_cutoff", 0.50).
    # Nodes in fixture have 0.5 and 0.4.
    # So 0.5 >= 0.50 (pass), 0.4 < 0.50 (fail).
    # Reranker keeps top N.

    # Let's bump scores to be safe and ensure they pass cutoff
    pipeline_context.retrieved_nodes[0].score = 0.8
    pipeline_context.retrieved_nodes[1].score = 0.7

    processor = RerankingProcessor()

    FlashRankRerank._loaded_rankers.clear()

    events = []
    async for event in processor.process(pipeline_context):
        events.append(event)

    # Should run reranking step
    step_events = [e for e in events if e.type == "step" and e.step_type == "reranking"]
    assert len(step_events) >= 1
    assert step_events[0].status == "running"

    # And completed
    assert step_events[-1].status == "completed"
    assert "fallback" not in step_events[-1].payload
