import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, List

import cohere
from llama_index.core.schema import NodeWithScore

from app.core.rag.processors.base import BaseProcessor
from app.core.rag.types import PipelineContext, PipelineEvent
from app.core.rag.utils import estimate_tokens
from app.core.settings import settings

# Configuration
TIMEOUT_SECONDS = 10.0  # P0: Avoid infinite hang
MAX_CANDIDATES = 50  # Increased for Cohere (it handles large batches well)
COHERE_MODEL = "rerank-v3.5"

logger = logging.getLogger(__name__)


class RerankingProcessor(BaseProcessor):
    """
    Processor responsible for re-ordering retrieved nodes using Cohere's Rerank API
    or a Local reranker (FastEmbed).
    Includes Fail-Open logic and Timeouts.
    """

    def __init__(self):
        super().__init__()
        self.cohere_client = None
        self._local_reranker = None

    async def _get_cohere_client(self, settings_service) -> Any:
        api_key = await settings_service.get_value("cohere_api_key")
        if api_key and not self.cohere_client:
            self.cohere_client = cohere.AsyncClient(api_key=api_key)
        return self.cohere_client

    def _get_local_reranker(self, model_name: str) -> Any:
        if not self._local_reranker:
            from fastembed import TextReranker

            logger.info(f"[RERANK] Initializing Local FastEmbed Reranker with model: {model_name}")
            self._local_reranker = TextReranker(model_name=model_name)
        return self._local_reranker

    async def process(self, ctx: PipelineContext) -> AsyncGenerator[PipelineEvent, None]:
        # 0. Fast Exit checks
        if not ctx.retrieved_nodes:
            logger.debug("[RERANK] No nodes retrieved, skipping.")
            return

        use_reranker = getattr(ctx.assistant, "use_reranker", False)
        if not use_reranker:
            logger.debug("[RERANK] Reranking disabled for this assistant.")
            yield PipelineEvent(type="step", step_type="reranking", status="completed", label="Skipped (Disabled)")
            yield PipelineEvent(type="sources", payload=self._format_payload(ctx.retrieved_nodes))
            return

        rerank_provider = getattr(ctx.assistant, "rerank_provider", "cohere")
        yield PipelineEvent(type="step", step_type="reranking", status="running")

        total_input_tokens = 0
        try:
            # Token estimation for analytics
            query_tokens = estimate_tokens(ctx.user_message)
            docs_tokens = sum(estimate_tokens(self._extract_text(n.node)) for n in ctx.retrieved_nodes[:MAX_CANDIDATES])
            total_input_tokens = query_tokens + docs_tokens

            nodes_to_rank = ctx.retrieved_nodes[:MAX_CANDIDATES]
            top_n_rerank = getattr(ctx.assistant, "top_n_rerank", 5)
            cutoff = getattr(ctx.assistant, "similarity_cutoff", 0.0)

            if rerank_provider == "cohere":
                reranked_nodes = await self._process_cohere(ctx, nodes_to_rank, top_n_rerank, cutoff)
            else:
                reranked_nodes = await self._process_local(ctx, nodes_to_rank, top_n_rerank, cutoff)

            # Update Context
            ctx.retrieved_nodes = reranked_nodes

            yield PipelineEvent(
                type="step",
                step_type="reranking",
                status="completed",
                payload={
                    "count": len(reranked_nodes),
                    "tokens": {"input": total_input_tokens, "output": 0},
                },
            )
            yield PipelineEvent(type="sources", payload=self._format_payload(reranked_nodes))

        except Exception as e:
            logger.exception(f"❌ [RERANK] Critical Failure: {e}")
            fallback_n = getattr(ctx.assistant, "top_n_rerank", 5)
            fallback_nodes = ctx.retrieved_nodes[:fallback_n]
            ctx.retrieved_nodes = fallback_nodes

            yield PipelineEvent(type="error", payload=f"Reranking failed (Fail Open): {str(e)}")
            yield PipelineEvent(
                type="step",
                step_type="reranking",
                status="completed",
                payload={
                    "count": len(fallback_nodes),
                    "fallback": True,
                    "tokens": {"input": total_input_tokens, "output": 0},
                },
            )
            yield PipelineEvent(type="sources", payload=self._format_payload(fallback_nodes))

    async def _process_cohere(
        self, ctx: PipelineContext, nodes: List[NodeWithScore], top_n: int, cutoff: float
    ) -> List[NodeWithScore]:
        client = await self._get_cohere_client(ctx.settings_service)
        if not client:
            raise Exception("Cohere API Key missing")

        documents = [{"text": self._extract_text(n.node)} for n in nodes]
        logger.info(f"[RERANK] Calling Cohere with {len(documents)} docs")

        try:
            results = await asyncio.wait_for(
                client.rerank(
                    model=COHERE_MODEL,
                    query=ctx.user_message,
                    documents=documents,
                    top_n=top_n,
                    return_documents=False,
                ),
                timeout=TIMEOUT_SECONDS,
            )

            reranked_nodes = []
            for result in results.results:
                idx = result.index
                if 0 <= idx < len(nodes):
                    node = nodes[idx]
                    node.score = result.relevance_score
                    if node.score >= cutoff:
                        reranked_nodes.append(node)
            return reranked_nodes
        except asyncio.TimeoutError:
            logger.warning(f"[RERANK] Cohere timeout after {TIMEOUT_SECONDS}s")
            raise Exception("Cohere Timeout")

    async def _process_local(
        self, ctx: PipelineContext, nodes: List[NodeWithScore], top_n: int, cutoff: float
    ) -> List[NodeWithScore]:
        model_name = await ctx.settings_service.get_value("local_rerank_model") or "BAAI/bge-reranker-base"
        reranker = self._get_local_reranker(model_name)

        documents = [self._extract_text(n.node) for n in nodes]
        logger.info(f"[RERANK] Calling Local Reranker ({model_name}) with {len(documents)} docs")

        # FastEmbed Rerank is synchronous, run in thread to avoid blocking event loop
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, lambda: list(reranker.rerank(query=ctx.user_message, documents=documents, top_n=top_n))
        )

        reranked_nodes = []
        for result in results:
            idx = result["index"]
            if 0 <= idx < len(nodes):
                node = nodes[idx]
                node.score = float(result["score"])
                if node.score >= cutoff:
                    reranked_nodes.append(node)
        return reranked_nodes

    def _format_payload(self, nodes: List[NodeWithScore]) -> List[Dict[str, Any]]:
        """Helper to format nodes for Frontend/API response."""
        return [
            {"id": str(n.node.node_id), "text": n.node.get_content(), "metadata": n.node.metadata, "score": n.score}
            for n in nodes
        ]

    def _extract_text(self, node: Any) -> str:
        """Helper to safely extract text from various node types."""
        if hasattr(node, "get_content"):
            return node.get_content()
        if hasattr(node, "text"):
            return node.text
        if isinstance(node, dict):
            return node.get("text", node.get("content", str(node)))
        return str(node)
