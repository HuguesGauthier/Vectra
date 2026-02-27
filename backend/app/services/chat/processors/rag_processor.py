import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Set, Tuple, TypeVar

from app.core.rag.pipeline import RAGPipeline
from app.core.rag.processors import (
    QueryRewriterProcessor,
    RerankingProcessor,
    RetrievalProcessor,
    SynthesisProcessor,
    VectorizationProcessor,
)
from app.core.rag.types import PipelineContext, PipelineEvent
from app.repositories import ConnectorRepository, DocumentRepository, VectorRepository
from app.services.chat.chat_metrics_manager import ChatMetricsManager
from app.services.chat.processors.base_chat_processor import BaseChatProcessor
from app.services.chat.source_service import SourceService
from app.services.chat.types import ChatContext, PipelineStepType, StepStatus
from app.services.chat.utils import EventFormatter

logger = logging.getLogger(__name__)


# Constants - Pipeline Steps
STEP_CONNECTION = PipelineStepType.CONNECTION
STEP_RETRIEVAL = PipelineStepType.RETRIEVAL
STEP_VECTORIZATION = PipelineStepType.VECTORIZATION

# Constants - Keys
KEY_EMBEDDING = "embedding"
KEY_TOKENS = "tokens"
KEY_INPUT = "input"
KEY_OUTPUT = "output"
KEY_ERROR = "error"

# Constants - Timeouts (Circuit Breakers)
TIMEOUT_RETRIEVAL = 30.0  # Seconds
TIMEOUT_SYNTHESIS = 60.0  # Seconds


T = TypeVar("T")


class RAGGenerationProcessor(BaseChatProcessor):
    """
    Processor responsible for executing RAG pipelines.
    Supports both Standard RAG and specialized CSV pipelines.
    Hardened with Timeouts and Circuit Breakers.
    """

    async def process(self, ctx: ChatContext) -> AsyncGenerator[str, None]:
        """Orchestrates the RAG pipeline with SSE event streaming."""
        if ctx.should_stop:
            logger.debug("[RAGGenerationProcessor] Skipping: ctx.should_stop is True")
            return

        self._ensure_metrics(ctx)

        # 1. Initialize & Dependencies (Connection check)
        t0 = time.time()
        conn_id = ctx.metrics.start_span(STEP_CONNECTION)
        yield EventFormatter.format(STEP_CONNECTION, StepStatus.RUNNING, conn_id)

        try:
            # Build components for first connector to validate connectivity
            connectors = list(ctx.assistant.linked_connectors or [])
            first_provider = connectors[0].configuration.get("ai_provider") if connectors else None
            first_components = await asyncio.wait_for(
                self._get_components_for_provider(ctx, first_provider), timeout=10.0
            )
        except asyncio.TimeoutError:
            yield EventFormatter.format(STEP_CONNECTION, StepStatus.FAILED, conn_id, label="Connection Timeout")
            return

        dur = round(time.time() - t0, 3)
        ctx.metrics.end_span(conn_id)
        yield EventFormatter.format(STEP_CONNECTION, StepStatus.COMPLETED, conn_id, duration=dur)

        # 2. Query Rewrite + Vectorization (shared — done once on first connector)
        rag_ctx = self._build_rag_context(ctx, first_components)
        async for event in self._execute_query_rewrite_and_vectorize(rag_ctx, ctx):
            yield event

        # 3. Multi-Connector Retrieval Phase (parent step wrapping per-connector sub-steps)
        all_nodes: list = []
        async for event in self._execute_multi_connector_retrieval(ctx, rag_ctx, connectors, all_nodes):
            yield event

        # 4. Reranking (on merged nodes)
        rag_ctx.retrieved_nodes = all_nodes
        async for event in self._execute_reranking(rag_ctx, ctx):
            yield event

        # 5. Sources Processing
        if await self._process_and_yield_sources(rag_ctx, ctx):
            yield json.dumps({"type": "sources", "data": ctx.retrieved_sources}, default=str) + "\n"

        # 6. Synthesis Phase
        async for event in self._execute_synthesis_phase(rag_ctx, ctx):
            yield event

    # --- Standard RAG Helpers ---

    def _ensure_metrics(self, ctx: ChatContext) -> None:
        if not ctx.metrics:
            ctx.metrics = ChatMetricsManager()

    def _build_rag_context(self, ctx: ChatContext, components: Dict) -> PipelineContext:
        """Builds a PipelineContext from pre-fetched components."""
        return PipelineContext(
            user_message=ctx.message,
            chat_history=ctx.history,
            language=ctx.language,
            assistant=ctx.assistant,
            llm=components["llm"],
            embed_model=components["embed_model"],
            search_strategy=components["search_strategy"],
            settings_service=ctx.settings_service,
            tools=[],
        )

    async def _execute_query_rewrite_and_vectorize(
        self, rag_ctx: PipelineContext, ctx: ChatContext
    ) -> AsyncGenerator[str, None]:
        """Runs QueryRewriter + Vectorization once (shared across all connectors)."""
        pipeline = RAGPipeline(
            context=rag_ctx,
            processors=[QueryRewriterProcessor(), VectorizationProcessor()],
        )
        try:
            async for event in self._consume_with_timeout(pipeline.run(ctx.message), TIMEOUT_RETRIEVAL):
                chunk = self._format_from_event(event, ctx)
                if chunk:
                    yield chunk
                if self._is_embedding_event(event):
                    ctx.captured_source_embedding = event.payload[KEY_EMBEDDING]
        except asyncio.TimeoutError:
            logger.error(f"Vectorization Phase Timeout ({TIMEOUT_RETRIEVAL}s)")
            yield json.dumps({"type": KEY_ERROR, "message": "Vectorization timed out."}, default=str) + "\n"

    async def _execute_multi_connector_retrieval(
        self,
        ctx: ChatContext,
        base_rag_ctx: PipelineContext,
        connectors: list,
        all_nodes: list,
    ) -> AsyncGenerator[str, None]:
        """
        Emits a parent RETRIEVAL step, then one VECTORIZATION sub-step per connector.
        Merges retrieved nodes into all_nodes (deduplicating by node id).
        """
        # If no connectors, fall back to a single retrieval with default provider
        effective_connectors = connectors or [None]

        # --- Parent RETRIEVAL: RUNNING ---
        retrieval_t0 = time.time()
        retrieval_id = ctx.metrics.start_span(STEP_RETRIEVAL)
        yield EventFormatter.format(STEP_RETRIEVAL, StepStatus.RUNNING, retrieval_id)

        seen_ids: Set[str] = set()

        for connector in effective_connectors:
            provider = connector.configuration.get("ai_provider") if connector else None
            collection = await ctx.vector_service.get_collection_name(provider)

            # Label shown in the UI: "Ollama (documents_ollama)"
            provider_display = (provider or "local").capitalize()
            sub_label = f"{provider_display} ({collection})"
            sub_payload = {"is_substep": True}

            # --- Sub-step: RUNNING ---
            sub_t0 = time.time()
            sub_id = ctx.metrics.start_span(STEP_VECTORIZATION, parent_id=retrieval_id)
            yield EventFormatter.format(
                STEP_VECTORIZATION,
                StepStatus.RUNNING,
                sub_id,
                parent_id=retrieval_id,
                label=sub_label,
                payload=sub_payload,
            )

            try:
                # Build retrieval pipeline (reuses already-computed embedding from base_rag_ctx)
                components = await self._get_components_for_provider(ctx, provider)
                connector_rag_ctx = self._build_rag_context(ctx, components)
                # Transfer the already-computed embedding so we don't re-vectorize
                connector_rag_ctx.question_embedding = base_rag_ctx.question_embedding

                retrieval_pipeline = RAGPipeline(
                    context=connector_rag_ctx,
                    processors=[RetrievalProcessor()],
                )
                async for event in self._consume_with_timeout(retrieval_pipeline.run(ctx.message), TIMEOUT_RETRIEVAL):
                    pass  # consume events; nodes stored on connector_rag_ctx

                # Merge nodes (deduplicate)
                for node in connector_rag_ctx.retrieved_nodes or []:
                    node_id = getattr(node, "node_id", None) or id(node)
                    if node_id not in seen_ids:
                        seen_ids.add(node_id)
                        all_nodes.append(node)

                sub_dur = round(time.time() - sub_t0, 3)
                node_count = len(connector_rag_ctx.retrieved_nodes or [])
                sub_payload_done = {"is_substep": True, "source_count": node_count}

                # --- Sub-step: COMPLETED ---
                ctx.metrics.end_span(sub_id, payload=sub_payload_done)
                yield EventFormatter.format(
                    STEP_VECTORIZATION,
                    StepStatus.COMPLETED,
                    sub_id,
                    parent_id=retrieval_id,
                    payload=sub_payload_done,
                    duration=sub_dur,
                    label=sub_label,
                )

            except asyncio.TimeoutError:
                sub_dur = round(time.time() - sub_t0, 3)
                logger.error(f"Retrieval timeout for connector provider '{provider}'")
                ctx.metrics.end_span(sub_id, payload={"is_substep": True})
                yield EventFormatter.format(
                    STEP_VECTORIZATION,
                    StepStatus.FAILED,
                    sub_id,
                    parent_id=retrieval_id,
                    label=sub_label,
                )
            except Exception as e:
                logger.error(f"Retrieval error for connector provider '{provider}': {e}", exc_info=True)
                ctx.metrics.end_span(sub_id, payload={"is_substep": True})
                yield EventFormatter.format(
                    STEP_VECTORIZATION,
                    StepStatus.FAILED,
                    sub_id,
                    parent_id=retrieval_id,
                    label=sub_label,
                )

        # --- Parent RETRIEVAL: COMPLETED ---
        retrieval_dur = round(time.time() - retrieval_t0, 3)
        ctx.metrics.end_span(retrieval_id)
        yield EventFormatter.format(STEP_RETRIEVAL, StepStatus.COMPLETED, retrieval_id, duration=retrieval_dur)

    async def _execute_reranking(self, rag_ctx: PipelineContext, ctx: ChatContext) -> AsyncGenerator[str, None]:
        """Runs the reranking step on the merged nodes."""
        pipeline = RAGPipeline(
            context=rag_ctx,
            processors=[RerankingProcessor()],
        )
        try:
            async for event in self._consume_with_timeout(pipeline.run(ctx.message), TIMEOUT_RETRIEVAL):
                chunk = self._format_from_event(event, ctx)
                if chunk:
                    yield chunk
        except asyncio.TimeoutError:
            logger.error(f"Reranking Phase Timeout ({TIMEOUT_RETRIEVAL}s)")

    async def _execute_synthesis_phase(self, rag_ctx: PipelineContext, ctx: ChatContext) -> AsyncGenerator[str, None]:
        syn_pipeline = RAGPipeline(context=rag_ctx, processors=[SynthesisProcessor()])
        start_gen = time.time()
        ttft_recorded = False

        try:
            async for event in self._consume_with_timeout(syn_pipeline.run(ctx.message), TIMEOUT_SYNTHESIS):
                if event.type == "step":
                    yield self._format_from_event(event, ctx)

                elif event.type == "token":
                    if not ttft_recorded:
                        ctx.metrics.ttft = round(time.time() - start_gen, 3)
                        ttft_recorded = True

                    token = event.payload
                    ctx.full_response_text += token
                    ctx.metrics.total_output_tokens += 1
                    yield json.dumps({"type": "token", "content": token, "text": token}, default=str) + "\n"

                elif event.type == "content_block":
                    block_type = event.payload.get("block_type")
                    data = event.payload.get("data")
                    if "content_blocks" not in ctx.metadata:
                        ctx.metadata["content_blocks"] = []
                    ctx.metadata["content_blocks"].append({"type": block_type, "data": data})
                    yield json.dumps(
                        {"type": "content_block", "block_type": block_type, "data": data}, default=str
                    ) + "\n"

                elif event.type == "response_stream":
                    # Backward compatibility for any older synthesis yielding raw stream
                    async for chunk in event.payload:
                        if not ttft_recorded:
                            ctx.metrics.ttft = round(time.time() - start_gen, 3)
                            ttft_recorded = True

                        # Capture Content
                        token = getattr(chunk, "delta", None) or str(chunk)
                        if token:
                            ctx.full_response_text += token
                            ctx.metrics.total_output_tokens += 1
                            yield json.dumps({"type": "token", "content": token, "text": token}, default=str) + "\n"

                elif event.type == KEY_ERROR:
                    msg = str(event.payload)
                    logger.error(f"Synthesis failed: {msg}")

                    # P0: Friendly translation for connectivity issues
                    if "ConnectError" in msg or "Connection refused" in msg or "11434" in msg:
                        msg = "Failed to connect to Ollama. Ensure the service is running and accessible."

                    yield json.dumps({"type": KEY_ERROR, "message": msg}, default=str) + "\n"

        except asyncio.TimeoutError:
            logger.error(f"Synthesis Phase Timeout ({TIMEOUT_SYNTHESIS}s)")
            yield json.dumps(
                {
                    "type": KEY_ERROR,
                    "message": "Generation timed out. Ollama might be overloaded or model is too large.",
                },
                default=str,
            ) + "\n"
        except Exception as e:
            logger.error(f"Unexpected Synthesis Exception: {e}", exc_info=True)
            yield json.dumps({"type": KEY_ERROR, "message": f"Synthesis Error: {str(e)}"}, default=str) + "\n"

    async def _process_and_yield_sources(self, rag_ctx: PipelineContext, ctx: ChatContext) -> bool:
        ctx.retrieved_sources = await SourceService.process_sources(rag_ctx.retrieved_nodes, ctx.db)
        return bool(ctx.retrieved_sources)

    def _is_embedding_event(self, event: PipelineEvent) -> bool:
        return (
            event.status == StepStatus.COMPLETED and isinstance(event.payload, dict) and KEY_EMBEDDING in event.payload
        )

    # --- Common Helpers ---

    async def _consume_with_timeout(
        self, generator: AsyncGenerator[T, None], timeout: float
    ) -> AsyncGenerator[T, None]:
        """
        Consumes an async generator with a timeout for EACH yield.
        Prevents infinite hang if one step stalls.
        """
        iterator = generator.__aiter__()
        while True:
            try:
                # Wait for next item with timeout
                item = await asyncio.wait_for(anext(iterator), timeout=timeout)
                yield item
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                raise  # Re-raise to be handled by caller
            except Exception:
                raise

    async def _get_components_for_provider(self, ctx: ChatContext, provider: Optional[str]) -> Dict:
        """
        Fetches RAG dependencies for a specific embedding provider.
        Used both for the initial connection check and per-connector retrieval.
        """
        from app.factories.chat_engine_factory import ChatEngineFactory
        from app.strategies import HybridStrategy, VectorOnlyStrategy

        llm = await ChatEngineFactory.create_from_assistant(ctx.assistant, ctx.settings_service)

        if provider:
            logger.info(f"RAG Processor | Using Connector Embedding Provider: {provider}")

        col = await ctx.vector_service.get_collection_name(provider)
        await ctx.vector_service.ensure_collection_exists(col, provider)
        try:
            embed = await ctx.vector_service.get_embedding_model(provider=provider)
        except Exception as e:
            logger.warning(
                f"Failed to get embedding model for provider '{provider}'. Falling back to local. Error: {e}"
            )
            embed = await ctx.vector_service.get_embedding_model(
                model_kwargs={"local_files_only": True}, provider="local"
            )

        vec_repo = VectorRepository(await ctx.vector_service.get_async_qdrant_client())
        strat_type = getattr(ctx.assistant, "search_strategy", "hybrid")

        if strat_type == "vector":
            strategy = VectorOnlyStrategy(vec_repo)
        else:
            strategy = HybridStrategy(
                vec_repo, DocumentRepository(ctx.db), ConnectorRepository(ctx.db), ctx.vector_service
            )

        return {"llm": llm, "embed_model": embed, "search_strategy": strategy}

    def _format_from_event(self, event: PipelineEvent, ctx: ChatContext) -> str:
        if event.type != "step":
            return ""

        if event.status == "running":
            span_id = ctx.metrics.start_span(event.step_type)
            ctx.step_timers[event.step_type] = span_id
            return EventFormatter.format(event.step_type, "running", span_id)

        elif event.status == "completed":
            span_id = ctx.step_timers.pop(event.step_type, None)
            if not span_id:
                # Fallback: record a syncless step if we missed the start
                dur = 0.0
                sid = ctx.metrics.record_completed_step(
                    step_type=event.step_type,
                    label=getattr(event, "label", None),
                    duration=0.0,
                    payload=event.payload if isinstance(event.payload, dict) else {},
                )
                return EventFormatter.format(event.step_type, "completed", sid, duration=0.0)

            payload = event.payload if isinstance(event.payload, dict) else {}
            tokens = payload.get(KEY_TOKENS, {})
            step_metric = ctx.metrics.end_span(
                span_id,
                input_tokens=int(tokens.get(KEY_INPUT, 0)),
                output_tokens=int(tokens.get(KEY_OUTPUT, 0)),
                payload=payload,
            )

            return EventFormatter.format(
                event.step_type,
                "completed",
                span_id,
                payload=payload,
                duration=step_metric.duration,
                label=getattr(event, "label", None),
            )

        elif event.status == "failed":
            span_id = ctx.step_timers.pop(event.step_type, None)
            return EventFormatter.format(event.step_type, "failed", span_id or f"failed_{event.step_type}")

        return ""
