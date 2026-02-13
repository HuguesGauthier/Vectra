import asyncio
import json
import logging
import logging
import time
from typing import Any, AsyncGenerator, Dict, Optional

from llama_index.core import PromptTemplate
from llama_index.core.base.response.schema import StreamingResponse
from llama_index.core.callbacks import CallbackManager

from app.core.prompts import REWRITE_QUESTION_PROMPT
from app.services.chat.callbacks import StreamingCallbackHandler
from app.services.chat.chat_metrics_manager import ChatMetricsManager
from app.services.chat.processors.base_chat_processor import BaseChatProcessor
from app.services.chat.source_service import SourceService

# Shared dependencies
from app.services.chat.types import ChatContext, PipelineStepType, StepStatus
from app.services.chat.utils import EventFormatter
from app.core.utils.stream_parser import StreamBlockParser

logger = logging.getLogger(__name__)

# --- Configuration Constants ---
TIMEOUT_LLM_REWRITE = 10.0  # Seconds
TIMEOUT_ROUTER_QUERY = 120.0  # Seconds (Long running SQL might take time)
HISTORY_WINDOW_SIZE = 3

# --- Defaults ---
DEFAULT_PROVIDER = "gemini"

# --- Keys & Labels ---
KEY_SQL_QUERY_RESULT = "sql_query_result"
KEY_RESULT = "result"
LABEL_CONTEXTUALIZING = "Contextualizing query..."
LABEL_ROUTER_WORKFLOW = "Agentic Workflow"
LABEL_ROUTER_PROCESSING = "Router Processing"
LABEL_ROUTER_RETRIEVAL = "Router Retrieval"
LABEL_ROUTER_ERROR = "Router Error: %s"
LOG_REWRITE = "🔄 Query Rewritten: '%s' -> '%s'"
LOG_CSV_ACTIVATED = "🔥 CSV MODE ACTIVATED via Agentic Processor"
LOG_STREAM_START = "📡 Router returned a streaming response, consuming..."
LOG_SQL_CAPTURED = "✅ Captured %d raw SQL rows. Visualization Eligible: %s"
LOG_EMBEDDING_FAIL = "Failed to compute embedding for analytics: %s"


class AgenticProcessor(BaseChatProcessor):
    """
    Processor dedicated to the Agentic Workflow (Router, Planning, Tools).
    Handles query contextualization, CSV pipeline delegation, and intelligent routing.
    Resilient design with Timeouts and Circuit Breakers.
    """

    async def process(self, ctx: ChatContext) -> AsyncGenerator[str, None]:
        """
        Main execution flow for the Agentic Processor.
        """
        logger.info(f"--- [AgenticProcessor] New Request: '{ctx.message}' ---")
        if self._should_skip(ctx):
            logger.warning("[AgenticProcessor] Skipping: ctx.should_stop or no factory")
            return

        self._ensure_metrics(ctx)

        # START SPAN: Agentic Workflow (Wraps Contextualization + Router)
        # We start it here so "Context Preparation" appears nested in the UI.
        agentic_span_id = ctx.metrics.start_span(PipelineStepType.ROUTER)
        yield EventFormatter.format(PipelineStepType.ROUTER, StepStatus.RUNNING, ctx.language)

        # 1. Contextual Rewriting (Fail Safe with Timeout)
        async for event in self._contextualize_query(ctx):
            yield event

        # 2. CSV Pipeline (Strategy Pattern Delegation)
        csv_handled = False
        async for event in self._handle_csv_mode_strategy(ctx, agentic_span_id):
            if isinstance(event, bool):
                csv_handled = event
            else:
                yield event

        # 2b. Visualization Shortcut (P0 Feature)
        # If we have cached structured data AND the user just wants to visualize it, SKIP the expensive router.
        viz_shortcut = False
        if not csv_handled and ctx.metadata.get("cached_sql_results"):
            # Check intent with fast LLM
            if await self._detect_visualization_intent(ctx):
                viz_shortcut = True
                async for event in self._execute_cached_visualization_workflow(ctx, agentic_span_id):
                    yield event

        # 3. Router Execution (only if CSV/Viz didn't handle the request)
        if not csv_handled and not viz_shortcut:
            async for event in self._execute_router_workflow(ctx, agentic_span_id):
                yield event
        else:
            # CSV handled the request, close the agentic span
            ctx.metrics.end_span(agentic_span_id)

    # --- Pre-conditions ---

    def _should_skip(self, ctx: ChatContext) -> bool:
        return ctx.should_stop or not ctx.query_engine_factory

    def _ensure_metrics(self, ctx: ChatContext) -> None:
        if not ctx.metrics:
            ctx.metrics = ChatMetricsManager()

    async def _execute_cached_visualization_workflow(
        self, ctx: ChatContext, parent_span_id: str
    ) -> AsyncGenerator[str, None]:
        """SHORTCUT: Generates visualization directly from cached SQL results."""
        logger.info("⚡ [AgenticProcessor] Visualization Shortcut Activated (Skipping SQL/Router)")

        # 1. Populate ctx.sql_results from cache
        ctx.sql_results = ctx.metadata.get("cached_sql_results")

        # 2. Yield standard events to simulate progress (for UI consistency)
        yield EventFormatter.format(
            PipelineStepType.ROUTER_PROCESSING,
            StepStatus.COMPLETED,
            ctx.language,
            duration=0.01,
            payload={"is_substep": True},
        )

        # 3. Simulate Router Completion
        yield EventFormatter.format(PipelineStepType.ROUTER, StepStatus.COMPLETED, ctx.language, duration=0.05)

        # 4. Trigger Visualization Service manually or let standard flow handle it?
        # Standard flow is: Agentic -> VisualizationProcessor
        # Agentic finishes, then VisualizationProcessor picks up.
        # Since we populated ctx.sql_results, VisualizationProcessor should handle it naturally!

        # P0 FIX: Ensure we have text so PersistenceProcessor saves this turn!
        # Without text, the turn is discarded, breaking the context chain for the NEXT question.
        if ctx.language == "fr":
            ctx.full_response_text = "Voici la visualisation basée sur les données précédentes."
        else:
            ctx.full_response_text = "Here is the visualization based on the previous data."

        ctx.metrics.end_span(parent_span_id)
        ctx.should_stop = True  # Ensure we don't run the actual router

    async def _detect_visualization_intent(self, ctx: ChatContext) -> bool:
        """Uses a Fast LLM to detect if the user wants to visualize the previous data."""
        try:
            from app.factories.chat_engine_factory import ChatEngineFactory

            # Use fast model (e.g. Gemini 1.5 Flash)
            settings_service = ctx.settings_service

            # Simple Prompt
            prompt = (
                f"User Question: {ctx.message}\n"
                "Context: The user previously asked for data which is now available.\n"
                "Task: Return TRUE if the user is asking to visualize, plot, graph, or format this data (e.g. 'show me a pie chart', 'plot this'). "
                "Return FALSE if they are asking a new question or modifying the data query (e.g. 'what about 2024?', 'filter by country').\n"
                "Output: boolean values only (true/false)"
            )

            # Use Factory but ideally we want a cheap model, not the main one
            # But Factory gives us the configured one. Optimization: force a cheaper model if possible?
            # For now, stick to standard consistency.
            llm = await ChatEngineFactory.create_from_assistant(ctx.assistant, settings_service, temperature=0.0)
            response = await llm.acomplete(prompt)

            answer = str(response).strip().lower()
            logger.info(f"🧠 [Intent Detection] Result: {answer}")
            return "true" in answer

        except Exception as e:
            logger.warning(f"Intent Detection failed: {e}")
            return False

    # --- 1. Contextual Rewriting ---

    async def _contextualize_query(self, ctx: ChatContext) -> AsyncGenerator[str, None]:
        """Rewrites the user query based on chat history to preserve context."""
        if not ctx.history:
            logger.debug("[AgenticProcessor:Rewrite] No history. Skipping.")
            return

        logger.info("[AgenticProcessor:Rewrite] Starting contextualization...")

        try:
            # P0 FEATURE: Context Rehydration (Smart Caching)
            # Check if previous turn has reusable structured data (e.g. SQL results from 10s ago)
            if ctx.history and len(ctx.history) > 0:
                last_msg = ctx.history[-1]
                if last_msg.role == "assistant" and last_msg.metadata:
                    structured_ctx = last_msg.metadata.get("sql_results")
                    if structured_ctx:
                        ctx.metadata["cached_sql_results"] = structured_ctx
                        logger.info(f"💾 [Rehydration] Found reusable SQL context ({len(structured_ctx)} rows)")

            yield EventFormatter.format(
                PipelineStepType.ROUTER_PROCESSING, StepStatus.RUNNING, ctx.language, payload={"is_substep": True}
            )

            start_time = time.time()

            # CIRCUIT BREAKER: Timeout protection
            try:
                new_query = await asyncio.wait_for(self._perform_rewrite_call(ctx), timeout=TIMEOUT_LLM_REWRITE)

                if new_query and new_query != ctx.message:
                    logger.info(LOG_REWRITE, ctx.message, new_query)
                    ctx.message = new_query

            except asyncio.TimeoutError:
                logger.warning(f"Rewrite Latency Exceeded ({TIMEOUT_LLM_REWRITE}s). Skipping rewrite.")

            duration = round(time.time() - start_time, 3)
            yield EventFormatter.format(
                PipelineStepType.ROUTER_PROCESSING,
                StepStatus.COMPLETED,
                ctx.language,
                duration=duration,
                payload={"is_substep": True},
            )

        except Exception as e:
            logger.warning(f"Failed to condense question: {e}")
            # Yield failures to ensure UI cleanup
            yield EventFormatter.format(
                PipelineStepType.ROUTER_PROCESSING, StepStatus.FAILED, ctx.language, payload={"is_substep": True}
            )

    async def _perform_rewrite_call(self, ctx: ChatContext) -> str:
        """Calls the LLM to rewrite the question."""
        relevant_history = ctx.history[-HISTORY_WINDOW_SIZE:]
        history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in relevant_history])

        prompt = PromptTemplate(REWRITE_QUESTION_PROMPT)

        # Use centralized Factory to get the correctly configured Chat Engine
        # based on Assistant settings (provider, model version, API keys)
        from app.factories.chat_engine_factory import ChatEngineFactory

        llm = await ChatEngineFactory.create_from_assistant(ctx.assistant, ctx.settings_service)
        response = await llm.apredict(prompt, chat_history=history_str, question=ctx.message)
        return response.strip()

    # --- 2. CSV Strategy ---

    async def _handle_csv_mode_strategy(self, ctx: ChatContext, agentic_span_id: str) -> AsyncGenerator[Any, None]:
        """Checks and delegates to CSV mode safely."""
        try:
            # Lazy Import for circular dependency management (and now separation)
            # We instantiate the dedicated CSVRAGProcessor
            from app.services.chat.processors.csv_rag_processor import CSVRAGProcessor

            csv_proc = CSVRAGProcessor()
            logger.info("[AgenticProcessor:CSV] Checking if CSV pipeline should be used...")
            should_use, _ = await csv_proc.should_use_csv_pipeline(ctx)

            if should_use:
                logger.info(LOG_CSV_ACTIVATED)

                # We yield the CSV events as sub-steps of the ROUTER
                async for event in csv_proc.process(ctx):
                    yield event

                # NOW we close the Router span and yield completion
                ctx.metrics.end_span(agentic_span_id)
                yield EventFormatter.format(PipelineStepType.ROUTER, "completed", ctx.language)

                ctx.should_stop = True
                yield True  # Handled
                return

        except Exception as e:
            logger.error(f"CSV Pipeline Check Failed: {e}", exc_info=True)
            yield self._format_json_event(
                {
                    "type": "step",
                    "step_type": "initialization",
                    "status": "completed",
                    "label": f"CSV Error: {str(e)[:50]}",
                }
            )

        yield False  # Not handled

    # --- 3. Router Workflow ---

    async def _execute_router_workflow(self, ctx: ChatContext, parent_span_id: str) -> AsyncGenerator[str, None]:
        """Executes the main LlamaIndex router workflow with robustness checks."""
        try:
            event_queue = asyncio.Queue()
            stream_handler = StreamingCallbackHandler(event_queue, ctx.language)

            # A. Initialize Engine
            logger.info("[AgenticProcessor:Router] Initializing Query Engine...")
            # Use ROUTER_PROCESSING type to avoid confusion with global INITIALIZATION step
            yield EventFormatter.format(
                PipelineStepType.ROUTER_PROCESSING,
                StepStatus.RUNNING,
                ctx.language,
                label="Engine Initialization",
                payload={"is_substep": True},
            )
            start_init = time.time()
            engine = await self._initialize_engine(ctx, stream_handler)
            dur_init = round(time.time() - start_init, 3)
            yield EventFormatter.format(
                PipelineStepType.ROUTER_PROCESSING,
                StepStatus.COMPLETED,
                ctx.language,
                duration=dur_init,
                label="Engine Initialization",
                payload={"is_substep": True},
            )

            logger.info(f"[AgenticProcessor:Router] Engine ready in {dur_init}s. Launching query...")

            self._record_router_metric(ctx, PipelineStepType.ROUTER_PROCESSING, None, dur_init, {"is_substep": True})

            # B. Launch Query & Background Tasks
            # CRITICAL FIX: RouterQueryEngine doesn't have astream_query()
            # We need to call the synchronous query() method, which returns a StreamingResponse
            # if the underlying SQL engine has streaming=True
            logger.info("[AgenticProcessor] Calling query() for Router...")

            # Emit step to show user we're executing the query
            yield EventFormatter.format(
                PipelineStepType.QUERY_EXECUTION, StepStatus.RUNNING, ctx.language, payload={"is_substep": True}
            )
            start_query = time.time()

            # Run the blocking query() call in a thread to avoid blocking the event loop
            router_task = asyncio.create_task(asyncio.to_thread(engine.query, ctx.message))
            embedding_task = asyncio.create_task(self._compute_background_embedding(ctx))

            # C. Consume Events
            async for event in self._consume_event_queue(event_queue, router_task):
                yield self._process_router_event(event, ctx)

            # Wait for result with Circuit Breaker
            try:
                response = await asyncio.wait_for(router_task, timeout=TIMEOUT_ROUTER_QUERY)
            except asyncio.TimeoutError:
                logger.warning(f"Router Query Timed Out ({TIMEOUT_ROUTER_QUERY}s). Cancelling task...")
                router_task.cancel()
                try:
                    await router_task
                except asyncio.CancelledError:
                    logger.info("Router task cancelled successfully.")
                raise TimeoutError(f"Query timed out after {TIMEOUT_ROUTER_QUERY}s")

            # Mark query as completed
            dur_query = round(time.time() - start_query, 3)
            yield EventFormatter.format(
                PipelineStepType.QUERY_EXECUTION,
                StepStatus.COMPLETED,
                ctx.language,
                duration=dur_query,
                payload={"is_substep": True},
            )

            # D. Handle Results
            self._capture_sql_results(ctx, response)

            async for source_event in self._process_response_sources(ctx, response):
                yield source_event

            # E. Stream Content
            async for token_event in self._stream_response_content(ctx, response, stream_handler, event_queue):
                yield token_event

            # F. Finalize
            step_metric = ctx.metrics.end_span(parent_span_id)
            yield EventFormatter.format(
                PipelineStepType.ROUTER, StepStatus.COMPLETED, ctx.language, duration=step_metric.duration
            )

            await embedding_task
            ctx.should_stop = True

        except Exception as e:
            logger.error(f"Agentic Router Critical Failure: {e}", exc_info=True)
            yield EventFormatter.format(
                PipelineStepType.ROUTER, StepStatus.FAILED, ctx.language, label=LABEL_ROUTER_ERROR % str(e)
            )

    async def _initialize_engine(self, ctx: ChatContext, handler: StreamingCallbackHandler):
        """Creates and configures the query engine."""
        engine = await ctx.query_engine_factory.create_engine(ctx.assistant, language=ctx.language)

        if hasattr(engine, "callback_manager"):
            engine.callback_manager.add_handler(handler)
        else:
            engine.callback_manager = CallbackManager([handler])

        return engine

    async def _consume_event_queue(self, queue: asyncio.Queue, task: asyncio.Task) -> AsyncGenerator[Dict, None]:
        """Yields events from the queue until the task is done."""
        while not task.done():
            try:
                # Wait briefly for new events
                event = await asyncio.wait_for(queue.get(), timeout=0.1)
                yield event
            except asyncio.TimeoutError:
                continue

        # Flush remaining
        while not queue.empty():
            yield queue.get_nowait()

    async def _compute_background_embedding(self, ctx: ChatContext) -> None:
        """Computes query embedding in background for analytics/cache."""
        try:
            # CRITICAL FIX: Use the embedding provider from the connector, not global default
            # The assistant's connectors determine which embedding provider to use
            provider = None
            if hasattr(ctx.assistant, "linked_connectors") and ctx.assistant.linked_connectors:
                for conn in ctx.assistant.linked_connectors:
                    if hasattr(conn, "configuration") and conn.configuration:
                        provider = conn.configuration.get("ai_provider")
                        if provider:
                            break

            embed_model = await ctx.vector_service.get_embedding_model(provider=provider)
            # Run in thread pool
            embedding = await asyncio.to_thread(embed_model.get_text_embedding, ctx.message)
            ctx.question_embedding = embedding
        except Exception as e:
            logger.warning(LOG_EMBEDDING_FAIL, e)

    def _capture_sql_results(self, ctx: ChatContext, response: Any) -> None:
        """Robust extraction of SQL results."""
        if not (hasattr(response, "metadata") and isinstance(response.metadata, dict)):
            return

        # Attempt to find results using known keys
        sql_data = response.metadata.get(KEY_SQL_QUERY_RESULT) or response.metadata.get(KEY_RESULT)

        if isinstance(sql_data, list):
            ctx.sql_results = sql_data
            has_rows = len(sql_data) > 0
            ctx.metadata["visualization_eligible"] = has_rows
            logger.info(LOG_SQL_CAPTURED, len(sql_data), has_rows)

    async def _process_response_sources(self, ctx: ChatContext, response: Any) -> AsyncGenerator[str, None]:
        """Extracts and formats sources."""
        if not hasattr(response, "source_nodes"):
            return

        ctx.retrieved_sources = await SourceService.process_sources(response.source_nodes, ctx.db)

        # Emit final accurate source count. The frontend will merge this with previous timing info.
        num_sources = len(ctx.retrieved_sources) if ctx.retrieved_sources else 0
        yield EventFormatter.format(
            PipelineStepType.ROUTER_RETRIEVAL,
            StepStatus.COMPLETED,
            ctx.language,
            payload={"is_substep": True, "source_count": num_sources},
        )

        if ctx.retrieved_sources:
            yield self._format_json_event({"type": "sources", "data": ctx.retrieved_sources})

    async def _stream_response_content(
        self, ctx: ChatContext, response: Any, stream_handler: Any, event_queue: Optional[asyncio.Queue] = None
    ) -> AsyncGenerator[str, None]:
        """Handles streaming the text tokens to the client using Robust Stream Parser."""
        stream_span = ctx.metrics.start_span(PipelineStepType.STREAMING)

        full_text = ""
        output_tokens = 0
        parser = StreamBlockParser()

        async def process_token_stream(token_gen):
            nonlocal full_text, output_tokens
            async for token in token_gen:
                token_str = str(token)

                # feed parser
                for event in parser.feed(token_str):
                    if event.type == "token":
                        full_text += event.content
                        output_tokens += 1
                        yield self._format_token(event.content)
                    elif event.type == "block":
                        # We found a table block!
                        table_data = event.content
                        if "content_blocks" not in ctx.metadata:
                            ctx.metadata["content_blocks"] = []
                        ctx.metadata["content_blocks"].append({"type": "table", "data": table_data})
                        logger.info("[AgenticProcessor] Stream: extracted table block")
                        yield json.dumps({"type": "content_block", "block_type": "table", "data": table_data}) + "\n"

                # Polling for events during streaming
                if event_queue:
                    while not event_queue.empty():
                        try:
                            event = event_queue.get_nowait()
                            yield self._process_router_event(event, ctx)
                        except asyncio.QueueEmpty:
                            break

        try:
            if isinstance(response, StreamingResponse):
                logger.info(LOG_STREAM_START)
                if hasattr(response, "async_response_gen"):
                    async for event in process_token_stream(response.async_response_gen):
                        yield event
                else:
                    # synchronous generator wrapper
                    async def sync_gen_wrapper():
                        for t in response.response_gen:
                            yield t

                    async for event in process_token_stream(sync_gen_wrapper()):
                        yield event

                # Exhaust the event queue after stream ends
                if event_queue:
                    while not event_queue.empty():
                        try:
                            event = event_queue.get_nowait()
                            yield self._process_router_event(event, ctx)
                        except asyncio.QueueEmpty:
                            break
            else:
                # Non-streaming fallback
                full_text_raw = str(response)
                # Feed the whole text to the parser
                for event in parser.feed(full_text_raw):
                    if event.type == "token":
                        full_text += event.content
                        output_tokens += 1
                        yield self._format_token(event.content)
                    elif event.type == "block":
                        table_data = event.content
                        if "content_blocks" not in ctx.metadata:
                            ctx.metadata["content_blocks"] = []
                        ctx.metadata["content_blocks"].append({"type": "table", "data": table_data})
                        yield json.dumps({"type": "content_block", "block_type": "table", "data": table_data}) + "\n"

        except Exception as e:
            logger.error(f"Stream Error: {e}")

        # Flush parser buffer
        for event in parser.flush():
            if event.type == "token":
                full_text += event.content
                output_tokens += 1
                yield self._format_token(event.content)

        ctx.full_response_text = full_text

        # Extract token counts
        llm_input_tokens = getattr(stream_handler, "total_input_tokens", 0)
        llm_output_tokens = getattr(stream_handler, "total_output_tokens", 0)

        # Pass to metrics system
        ctx.metrics.end_span(
            stream_span,
            input_tokens=llm_input_tokens,
            output_tokens=llm_output_tokens or output_tokens,
        )

    # --- Metrics & Formatter Helpers ---

    def _process_router_event(self, event_data: Dict, ctx: ChatContext) -> str:
        step_type = event_data.get("step_type")
        status = event_data.get("status")
        payload = SourceService._sanitize_data(event_data.get("payload", {}))
        duration = event_data.get("duration")
        label = event_data.get("label")

        if step_type == PipelineStepType.RETRIEVAL:
            # P0 FIX: Use the 'is_sql' hint from callbacks for consistent start/end mapping.
            # This prevents the "Zombie" line issue where start/end have different types.
            is_sql_meta = payload.get("is_sql", False)

            # Fallback for very old traces is risky for Folder Connectors (small count != SQL)
            # We strictly rely on the hint now.

            step_type = PipelineStepType.SQL_SCHEMA_RETRIEVAL if is_sql_meta else PipelineStepType.ROUTER_RETRIEVAL

        # FIX: Ensure completed events ALWAYS have duration (even if 0.0) so they appear in UI
        if status == StepStatus.COMPLETED:
            if duration is None:
                duration = 0.0
            self._record_router_metric(ctx, step_type, label, duration, payload)

        if "is_substep" not in payload:
            payload["is_substep"] = True

        # Hide intermediate counts (likely schema retrieval) to avoid confusing the user
        # The final accurate count will be sent by _process_response_sources
        if step_type == PipelineStepType.ROUTER_RETRIEVAL and "source_count" in payload:
            del payload["source_count"]

        return EventFormatter.format(step_type, status, ctx.language, payload, duration, label)

    def _record_router_metric(self, ctx: ChatContext, step_type, label, duration, payload):
        tokens = payload.get("tokens", {})
        ctx.metrics.record_completed_step(
            step_type=step_type,
            label=label,
            duration=duration,
            input_tokens=int(tokens.get("input", 0)),
            output_tokens=int(tokens.get("output", 0)),
            payload=payload,
        )

    def _format_token(self, content: str) -> str:
        return json.dumps({"type": "token", "content": content, "text": content}, default=str) + "\n"

    def _format_json_event(self, data: Dict) -> str:
        return json.dumps(data, default=str) + "\n"
