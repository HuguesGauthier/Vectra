import asyncio
import logging
import os
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
    Processor responsible for re-ordering retrieved nodes using Cohere's Rerank API.
    Includes Fail-Open logic and Timeouts.
    """

    def __init__(self):
        super().__init__()
        self.api_key = settings.COHERE_API_KEY
        if not self.api_key:
            logger.warning("⚠️ COHERE_API_KEY not found in settings. Reranking will be skipped.")

        # Initialize client only if key exists
        self.client = cohere.AsyncClient(api_key=self.api_key) if self.api_key else None

    async def process(self, ctx: PipelineContext) -> AsyncGenerator[PipelineEvent, None]:
        # 0. Fast Exit checks
        if not ctx.retrieved_nodes:
            logger.debug("[RERANK] No nodes retrieved, skipping.")
            return

        use_reranker = getattr(ctx.assistant, "use_reranker", False)

        if not use_reranker:
            # Fast pass-through
            logger.debug("[RERANK] Reranking disabled for this assistant.")
            yield PipelineEvent(type="step", step_type="reranking", status="completed", label="Skipped (Disabled)")
            yield PipelineEvent(type="sources", payload=self._format_payload(ctx.retrieved_nodes))
            return

        # Check for API Key validity
        if not self.client:
            logger.error(
                f"❌ [RERANK] Cohere API Key missing. Skipping Rerank. (API Key Present? {bool(self.api_key)})"
            )
            yield PipelineEvent(
                type="step", step_type="reranking", status="completed", label="Skipped (Missing API Key)"
            )
            yield PipelineEvent(type="sources", payload=self._format_payload(ctx.retrieved_nodes))
            return

        yield PipelineEvent(type="step", step_type="reranking", status="running")

        # Initialize token variables to prevent UnboundLocalError in finally/except blocks
        query_tokens = 0
        docs_tokens = 0
        total_input_tokens = 0

        try:
            # Prepare estimates early for usage tracking (inside try for safety)
            query_tokens = estimate_tokens(ctx.user_message)
            docs_tokens = 0
            if ctx.retrieved_nodes:
                docs_tokens = sum(
                    estimate_tokens(self._extract_text(n.node)) for n in ctx.retrieved_nodes[:MAX_CANDIDATES]
                )
            total_input_tokens = query_tokens + docs_tokens

            # 1. Prepare Candidates
            nodes_to_rank = ctx.retrieved_nodes[:MAX_CANDIDATES]
            query = ctx.user_message
            top_n_rerank = getattr(ctx.assistant, "top_n_rerank", 5)

            # 2. Cohere API Call
            documents_to_rank = [{"text": self._extract_text(n.node)} for n in ctx.retrieved_nodes]
            logger.info(f"[RERANK] Sending {len(documents_to_rank)} docs to Cohere for reranking")

            # Store original scores for analytics
            original_scores = [n.score for n in ctx.retrieved_nodes]

            # Call Cohere with Timeout
            try:
                results = await asyncio.wait_for(
                    self.client.rerank(
                        model=COHERE_MODEL,
                        query=ctx.user_message,
                        documents=documents_to_rank,
                        top_n=top_n_rerank,
                        return_documents=False,
                    ),
                    timeout=TIMEOUT_SECONDS,
                )

                logger.info(f"[RERANK] Cohere returned {len(results.results)} results")

                # Map results back to nodes
                reranked_nodes = []
                reranked_scores = []
                cutoff = getattr(ctx.assistant, "similarity_cutoff", 0.0)

                for result in results.results:
                    idx = result.index
                    if 0 <= idx < len(ctx.retrieved_nodes):
                        node = ctx.retrieved_nodes[idx]
                        node.score = result.relevance_score

                        # Apply Similarity Cutoff (Reranking)
                        if node.score >= cutoff:
                            reranked_nodes.append(node)
                            reranked_scores.append(result.relevance_score)
                        else:
                            logger.debug(f"[RERANK] Dropping node {node.node.node_id} (Score: {node.score} < {cutoff})")

                kept_count = len(reranked_nodes)
                cutoff_count = len(ctx.retrieved_nodes) - kept_count

                yield PipelineEvent(
                    type="step",
                    step_type="reranking",
                    status="completed",
                    label=f"Reranking (Kept {kept_count}, Cutoff {cutoff_count})",
                )

                # Store for analytics: pre/post scores
                ctx.metadata["original_scores"] = original_scores[:top_n_rerank]
                ctx.metadata["reranked_scores"] = reranked_scores

                # Calculate impact
                if reranked_scores and original_scores:
                    avg_improvement = sum(reranked_scores) / len(reranked_scores) - sum(
                        original_scores[: len(reranked_scores)]
                    ) / len(reranked_scores)
                    ctx.metadata["reranking_impact"] = round(avg_improvement, 3)

                # Update Context
                ctx.retrieved_nodes = reranked_nodes
                logger.info(
                    f"[RERANK] ✅ Reranking successful. Top score: {reranked_nodes[0].score if reranked_nodes else 'N/A'}"
                )

            except asyncio.TimeoutError:
                logger.warning(f"⚠️ [RERANK] Timeout after {TIMEOUT_SECONDS}s. Falling back to original order.")
                raise Exception("Cohere Rerank Timeout")

            logger.info(f"✅ [RERANK] Complete. Kept {len(reranked_nodes)}/{len(nodes_to_rank)}")

            # 5. Emit Events
            yield PipelineEvent(
                type="step",
                step_type="reranking",
                status="completed",
                payload={
                    "count": len(reranked_nodes),
                    "tokens": {"input": total_input_tokens, "output": 0},  # Reranking doesn't generate text
                },
            )
            yield PipelineEvent(type="sources", payload=self._format_payload(reranked_nodes))

        except Exception as e:
            logger.exception(f"❌ [RERANK] Critical Failure: {e}")

            # P0: Ultimate Fail Open
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
