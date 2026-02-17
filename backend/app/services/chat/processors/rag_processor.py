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
        if ctx.should_stop:
            return

        # Skip if CSV pipeline was already handled via Agentic Processor
        if ctx.metadata.get("csv_pipeline_executed"):
            logger.info("⏩ RAG Processor: Skipping (CSV pipeline executed)")
            return

        self._ensure_metrics(ctx)

        # 1. Initialize & Dependencies
        t0 = time.time()
        yield EventFormatter.format(STEP_CONNECTION, StepStatus.RUNNING, ctx.language)

        try:
            rag_ctx = await asyncio.wait_for(self._initialize_standard_rag(ctx), timeout=10.0)
        except asyncio.TimeoutError:
            yield EventFormatter.format(STEP_CONNECTION, StepStatus.FAILED, ctx.language, label="Connection Timeout")
            return

        dur = round(time.time() - t0, 3)
        yield EventFormatter.format(STEP_CONNECTION, StepStatus.COMPLETED, ctx.language, duration=dur)
        ctx.metrics.record_completed_step(STEP_CONNECTION, "Connection", dur)

        # 2. Retrieval Phase
        async for event in self._execute_retrieval_phase(rag_ctx, ctx):
            yield event

        # 3. Sources Processing
        if await self._process_and_yield_sources(rag_ctx, ctx):
            yield json.dumps({"type": "sources", "data": ctx.retrieved_sources}, default=str) + "\n"

        # 4. Synthesis Phase
        async for event in self._execute_synthesis_phase(rag_ctx, ctx):
            yield event

    # --- Standard RAG Helpers ---

    def _ensure_metrics(self, ctx: ChatContext) -> None:
        if not ctx.metrics:
            ctx.metrics = ChatMetricsManager()

    async def _initialize_standard_rag(self, ctx: ChatContext) -> PipelineContext:
        """Sets up the RAG context and dependencies."""
        components = await self._get_components(ctx)

        return PipelineContext(
            user_message=ctx.message,
            chat_history=ctx.history,
            language=ctx.language,
            assistant=ctx.assistant,
            llm=components["llm"],
            embed_model=components["embed_model"],
            search_strategy=components["search_strategy"],
            settings_service=ctx.settings_service,
            tools=[],  # Visualization tool moved to VisualizationProcessor
        )

    async def _execute_retrieval_phase(self, rag_ctx: PipelineContext, ctx: ChatContext) -> AsyncGenerator[str, None]:
        pipeline = RAGPipeline(
            context=rag_ctx,
            processors=[QueryRewriterProcessor(), VectorizationProcessor(), RetrievalProcessor(), RerankingProcessor()],
        )
        # Circuit Breaker around Retrieval Loop
        # Note: Since pipeline yields step-by-step, we wrap consumption
        try:
            async for event in self._consume_with_timeout(pipeline.run(ctx.message), TIMEOUT_RETRIEVAL):
                yield self._format_from_event(event, ctx)
                if self._is_embedding_event(event):
                    ctx.captured_source_embedding = event.payload[KEY_EMBEDDING]
        except asyncio.TimeoutError:
            logger.error(f"Retrieval Phase Timeout ({TIMEOUT_RETRIEVAL}s)")
            yield json.dumps({"type": KEY_ERROR, "message": "Retrieval timed out."}, default=str) + "\n"

    async def _execute_synthesis_phase(self, rag_ctx: PipelineContext, ctx: ChatContext) -> AsyncGenerator[str, None]:
        syn_pipeline = RAGPipeline(context=rag_ctx, processors=[SynthesisProcessor()])
        start_gen = time.time()
        ttft_recorded = False

        try:
            async for event in self._consume_with_timeout(syn_pipeline.run(ctx.message), TIMEOUT_SYNTHESIS):
                if event.type == "step":
                    yield self._format_from_event(event, ctx)

                elif event.type == "response_stream":
                    async for chunk in event.payload:
                        if not ttft_recorded:
                            ctx.metrics.ttft = round(time.time() - start_gen, 3)
                            ttft_recorded = True

                        # Capture Content
                        token = chunk.delta
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

    async def _get_components(self, ctx: ChatContext) -> Dict:
        """Fetches standard RAG dependencies."""
        settings = ctx.settings_service
        # Use centralized Factory to get the correctly configured Chat Engine
        from app.factories.chat_engine_factory import ChatEngineFactory

        llm = await ChatEngineFactory.create_from_assistant(
            ctx.assistant, ctx.settings_service, temperature=ctx.assistant.configuration.get("temperature", 0.7)
        )

        # Decouple Collection from Chat Provider.
        # Collection depends on the Embedding Provider (Global/Connector), not the Chat LLM.
        # Priority:
        # A. First Linked Connector's "ai_provider" (User Preference on Source)
        # B. Global Default (if None passed to VectorService)

        provider = None
        if ctx.assistant.linked_connectors:
            # Use the first connector's config to determine the embedding context.
            # In a single-collection system, all connectors for a query usually share the provider.
            first_conn = ctx.assistant.linked_connectors[0]
            provider = first_conn.configuration.get("ai_provider")
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

        from app.strategies import HybridStrategy, VectorOnlyStrategy

        vec_repo = VectorRepository(ctx.vector_service.get_async_qdrant_client())
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
            ctx.step_timers[event.step_type] = time.time()
            return EventFormatter.format(event.step_type, "running", ctx.language)

        elif event.status == "completed":
            start = ctx.step_timers.pop(event.step_type, time.time())
            dur = round(time.time() - start, 3)

            payload = event.payload if isinstance(event.payload, dict) else {}
            tokens = payload.get(KEY_TOKENS, {})

            ctx.metrics.record_completed_step(
                step_type=event.step_type,
                label=getattr(event, "label", None),
                duration=dur,
                input_tokens=int(tokens.get(KEY_INPUT, 0)),
                output_tokens=int(tokens.get(KEY_OUTPUT, 0)),
                payload=payload,
            )
            return EventFormatter.format(
                event.step_type, "completed", ctx.language, payload, dur, label=getattr(event, "label", None)
            )

        elif event.status == "failed":
            return EventFormatter.format(event.step_type, "failed", ctx.language, event.payload)

        return ""
