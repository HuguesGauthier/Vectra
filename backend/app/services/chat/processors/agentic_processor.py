import asyncio
import json
import logging
import logging
import time
from typing import Any, AsyncGenerator, Dict, Optional

from llama_index.core import PromptTemplate
from llama_index.core.base.response.schema import StreamingResponse
from llama_index.core.callbacks import CallbackManager
from llama_index.core.schema import QueryBundle

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
# (Removed hardcoded default provider)

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

        # 0. Resolve specific model name for UI (e.g., "gpt-4o" instead of just "openai")
        try:
            provider = ctx.assistant.model_provider
            # Handle special cases if any, but standard pattern is {provider}_chat_model
            config_key = f"{provider}_chat_model"
            specific_model = await ctx.settings_service.get_value(config_key)
            if specific_model:
                ctx.metadata["specific_model_name"] = specific_model
        except Exception as e:
            logger.warning(f"Failed to resolve specific model name: {e}")
        if self._should_skip(ctx):
            logger.warning("[AgenticProcessor] Skipping: ctx.should_stop or no factory")
            return

        self._ensure_metrics(ctx)

        try:
            # START SPAN: Agentic Workflow (Wraps Contextualization + Router)
            # We start it here so "Context Preparation" appears nested in the UI.
            agentic_span_id = ctx.metrics.start_span(PipelineStepType.ROUTER)
            yield EventFormatter.format(PipelineStepType.ROUTER, StepStatus.RUNNING, agentic_span_id)

            # 1. Contextual Rewriting (Fail Safe with Timeout)
            async for event in self._contextualize_query(ctx, agentic_span_id):
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

        finally:
            # Clean up ephemeral processing metadata to avoid serialization issues later
            if "_emitted_step_ids" in ctx.metadata:
                del ctx.metadata["_emitted_step_ids"]

            # Close the agentic span if not done (e.g. on error).
            # Use local flags; they are guaranteed to be bound since the try block
            # initialises them before any yield that could raise.
            _csv = locals().get("csv_handled", False)
            _viz = locals().get("viz_shortcut", False)
            if not _csv and not _viz:
                # We try to end it; MetricsManager will ignore if already ended
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
        sid = ctx.metrics.start_span(PipelineStepType.ROUTER_PROCESSING, parent_id=parent_span_id)
        ctx.metrics.end_span(sid, payload={"is_substep": True})
        yield EventFormatter.format(
            PipelineStepType.ROUTER_PROCESSING,
            StepStatus.COMPLETED,
            sid,
            parent_id=parent_span_id,
            duration=0.01,
            payload={"is_substep": True},
        )

        # 3. Simulate Router Completion
        ctx.metrics.end_span(parent_span_id)
        yield EventFormatter.format(PipelineStepType.ROUTER, StepStatus.COMPLETED, parent_span_id, duration=0.05)

        # 4. Trigger Visualization Service manually or let standard flow handle it?
        # Standard flow is: Agentic -> VisualizationProcessor
        # Agentic finishes, then VisualizationProcessor picks up.
        # Since we populated ctx.sql_results, VisualizationProcessor should handle it naturally!

        # P0 FIX: Ensure we have text so PersistenceProcessor saves this turn!
        # Without text, the turn is discarded, breaking the context chain for the NEXT question.
        if ctx.language == "fr":
            text = "Voici la visualisation basée sur les données précédentes."
        else:
            text = "Here is the visualization based on the previous data."

        ctx.full_response_text = text
        # P0 FIX: Yield tokens so the UI creates a new message bubble instead of merging with the previous one
        for word in text.split(" "):
            yield self._format_token(word + " ")
            await asyncio.sleep(0.02)  # Subtle delay for UX

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

    async def _contextualize_query(self, ctx: ChatContext, parent_id: str) -> AsyncGenerator[str, None]:
        """Rewrites the user query based on chat history to preserve context."""
        if not ctx.history:
            logger.debug("[AgenticProcessor:Rewrite] No history. Skipping.")
            return

        logger.info("[AgenticProcessor:Rewrite] Starting contextualization...")

        try:
            # P0 FEATURE: Context Rehydration (Smart Caching)
            if ctx.history and len(ctx.history) > 0:
                last_msg = ctx.history[-1]
                if last_msg.role == "assistant" and last_msg.metadata:
                    structured_ctx = last_msg.metadata.get("sql_results")
                    if structured_ctx:
                        ctx.metadata["cached_sql_results"] = structured_ctx
                        logger.info(f"💾 [Rehydration] Found reusable SQL context ({len(structured_ctx)} rows)")

            sid = ctx.metrics.start_span(PipelineStepType.QUERY_REWRITE, parent_id=parent_id)
            yield EventFormatter.format(
                PipelineStepType.QUERY_REWRITE, StepStatus.RUNNING, sid, parent_id=parent_id, payload={"is_substep": True}
            )

            start_time = time.time()
            rewrite_tokens = None

            try:
                result = await asyncio.wait_for(self._perform_rewrite_call(ctx), timeout=TIMEOUT_LLM_REWRITE)
                new_query, rewrite_tokens = result if isinstance(result, tuple) else (result, None)

                if new_query and new_query != ctx.message:
                    logger.info(LOG_REWRITE, ctx.message, new_query)
                    ctx.message = new_query

            except asyncio.TimeoutError:
                logger.warning(f"Rewrite Latency Exceeded ({TIMEOUT_LLM_REWRITE}s). Skipping rewrite.")

            duration = round(time.time() - start_time, 3)

            # Build payload — include token counts if captured
            payload: Dict = {"is_substep": True}
            if rewrite_tokens:
                payload["tokens"] = rewrite_tokens
            try:
                model_val = ctx.metadata.get("specific_model_name") or (
                    ctx.assistant.model.value if hasattr(ctx.assistant.model, "value") else str(ctx.assistant.model)
                )
                payload["model_name"] = model_val
                payload["model_provider"] = ctx.assistant.model_provider
            except Exception:
                pass

            ctx.metrics.end_span(sid, payload=payload)
            ctx.metadata["_manual_rewrite_done"] = True

            yield EventFormatter.format(
                PipelineStepType.QUERY_REWRITE,
                StepStatus.COMPLETED,
                sid,
                parent_id=parent_id,
                duration=duration,
                payload=payload,
            )
            # NOTE: end_span already called above — do NOT call again here.

        except Exception as e:
            logger.warning(f"Failed to condense question: {e}")
            yield EventFormatter.format(
                PipelineStepType.QUERY_REWRITE, StepStatus.FAILED, ctx.language, payload={"is_substep": True}
            )

    async def _perform_rewrite_call(self, ctx: ChatContext) -> tuple:
        """Calls the LLM to rewrite the question. Returns (rewritten_text, token_dict)."""
        relevant_history = ctx.history[-HISTORY_WINDOW_SIZE:]
        history_str = "\n".join([f"{msg.role}: {msg.content}" for msg in relevant_history])

        prompt = PromptTemplate(REWRITE_QUESTION_PROMPT)

        from app.factories.chat_engine_factory import ChatEngineFactory

        llm = await ChatEngineFactory.create_from_assistant(ctx.assistant, ctx.settings_service)
        # Use astream_complete to capture token usage after generation
        full_text = ""
        input_tokens = 0
        output_tokens = 0
        try:
            async for chunk in await llm.astream_complete(
                prompt.format(chat_history=history_str, question=ctx.message)
            ):
                full_text = chunk.text  # astream_complete gives cumulative text
                # Capture usage from last chunk
                raw = getattr(chunk, "raw", None) or {}
                meta = (
                    (raw.get("usage_metadata") if isinstance(raw, dict) else getattr(raw, "usage_metadata", None))
                    if raw
                    else None
                )
                if meta:
                    input_tokens = (
                        meta.get("prompt_token_count")
                        if isinstance(meta, dict)
                        else getattr(meta, "prompt_token_count", 0)
                    ) or 0
                    output_tokens = (
                        meta.get("candidates_token_count")
                        if isinstance(meta, dict)
                        else getattr(meta, "candidates_token_count", 0)
                    ) or 0
        except Exception:
            # Fallback to simple apredict if streaming not supported
            full_text = await llm.apredict(prompt, chat_history=history_str, question=ctx.message)

        tokens = {"input": input_tokens, "output": output_tokens} if (input_tokens or output_tokens) else None
        return full_text.strip(), tokens

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
                yield EventFormatter.format(PipelineStepType.ROUTER, "completed", agentic_span_id)

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
            sid_init = ctx.metrics.start_span(PipelineStepType.ROUTER_PROCESSING, parent_id=parent_span_id)
            yield EventFormatter.format(
                PipelineStepType.ROUTER_PROCESSING,
                StepStatus.RUNNING,
                sid_init,
                parent_id=parent_span_id,
                payload={"is_substep": True},
            )
            start_init = time.time()
            engine = await self._initialize_engine(ctx, stream_handler)
            dur_init = round(time.time() - start_init, 3)
            ctx.metrics.end_span(sid_init, payload={"is_substep": True})
            yield EventFormatter.format(
                PipelineStepType.ROUTER_PROCESSING,
                StepStatus.COMPLETED,
                sid_init,
                parent_id=parent_span_id,
                duration=dur_init,
                payload={"is_substep": True},
            )
            # NOTE: _record_router_metric removed here — end_span above already records
            # the completed step in ChatMetricsManager, preventing double entries.

            logger.info(f"[AgenticProcessor:Router] Engine ready in {dur_init}s. Launching query...")

            # B. Launch Query & Background Tasks
            # CRITICAL FIX: RouterQueryEngine doesn't have astream_query()
            # We need to call the synchronous query() method, which returns a StreamingResponse
            # if the underlying SQL engine has streaming=True
            # STREAMING FIX: Use aquery (native async) instead of wrapping sync query() in a thread.
            # asyncio.to_thread() forces the entire response to be buffered before tokens arrive,
            # which is why the response appeared "all at once". aquery() lets the event loop
            # yield tokens as they are generated.
            logger.info("[AgenticProcessor] Calling aquery() for Router (async streaming)...")

            # Emit step to show user we're executing the query
            sid_query = ctx.metrics.start_span(PipelineStepType.QUERY_EXECUTION, parent_id=parent_span_id)
            yield EventFormatter.format(
                PipelineStepType.QUERY_EXECUTION, StepStatus.RUNNING, sid_query, parent_id=parent_span_id, payload={"is_substep": True}
            )
            start_query = time.time()

            embedding_task = asyncio.create_task(self._compute_background_embedding(ctx))

            # Execute query natively async — no thread wrapping needed.
            # We still apply the circuit-breaker timeout for safety.
            try:
                response = await asyncio.wait_for(
                    engine.aquery(ctx.message),
                    timeout=TIMEOUT_ROUTER_QUERY,
                )
            except asyncio.TimeoutError:
                logger.warning(f"Router Query Timed Out ({TIMEOUT_ROUTER_QUERY}s).")
                raise TimeoutError(f"Query timed out after {TIMEOUT_ROUTER_QUERY}s")

            # C. Flush any callback events produced during aquery
            while not event_queue.empty():
                try:
                    event = event_queue.get_nowait()
                    yield self._process_router_event(ctx, event, parent_id=sid_query)
                except asyncio.QueueEmpty:
                    break

            # Mark query as completed
            dur_query = round(time.time() - start_query, 3)
            ctx.metrics.end_span(sid_query, payload={"is_substep": True})
            yield EventFormatter.format(
                PipelineStepType.QUERY_EXECUTION,
                StepStatus.COMPLETED,
                sid_query,
                parent_id=parent_span_id,
                duration=dur_query,
                payload={"is_substep": True},
            )

            # D. Handle Results
            self._capture_sql_results(ctx, response)

            # Update the stream handler with the parent_id for callback events
            stream_handler.parent_id = parent_span_id

            async for source_event in self._process_response_sources(ctx, response):
                yield source_event

            # E. Stream Content — wrapped in ROUTER_SYNTHESIS for accurate timing.
            # The LLM callbacks fire at ~0ms with streaming (they get a handle, not the full response).
            # The REAL generation time lives here, in the token stream consumption.
            synthesis_start = time.time()
            sid_synth = ctx.metrics.start_span(PipelineStepType.ROUTER_SYNTHESIS, parent_id=parent_span_id)
            yield EventFormatter.format(
                PipelineStepType.ROUTER_SYNTHESIS, StepStatus.RUNNING, sid_synth, parent_id=parent_span_id, payload={"is_substep": True}
            )

            async for token_event in self._stream_response_content(ctx, response, stream_handler, event_queue):
                yield token_event

            synthesis_dur = round(time.time() - synthesis_start, 3)
            # Get the final cumulative token counts from the handler
            synth_input = getattr(stream_handler, "total_input_tokens", 0)
            synth_output = getattr(stream_handler, "total_output_tokens", 0)
            synth_payload: Dict = {"is_substep": True}
            if synth_input or synth_output:
                synth_payload["tokens"] = {"input": synth_input, "output": synth_output}
            try:
                model_val = ctx.metadata.get("specific_model_name") or (
                    ctx.assistant.model.value if hasattr(ctx.assistant.model, "value") else str(ctx.assistant.model)
                )
                synth_payload["model_name"] = model_val
                synth_payload["model_provider"] = ctx.assistant.model_provider
            except Exception:
                pass
            yield EventFormatter.format(
                PipelineStepType.ROUTER_SYNTHESIS,
                StepStatus.COMPLETED,
                sid_synth,
                parent_id=parent_span_id,
                duration=synthesis_dur,
                payload=synth_payload,
            )
            ctx.metrics.end_span(sid_synth, payload=synth_payload)

            # F. Finalize
            step_metric = ctx.metrics.end_span(parent_span_id)
            yield EventFormatter.format(
                PipelineStepType.ROUTER, StepStatus.COMPLETED, parent_span_id, duration=step_metric.duration
            )

            await embedding_task
            ctx.should_stop = True
            # Note: event_queue is not consumed after synthesis because aquery() is
            # synchronous from the caller perspective once the response object is returned.

        except Exception as e:
            logger.error(f"Agentic Router Critical Failure: {e}", exc_info=True)
            yield EventFormatter.format(
                PipelineStepType.ROUTER, StepStatus.FAILED, parent_span_id, label=LABEL_ROUTER_ERROR % str(e)
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
        """Computes query embedding in background for analytics/cache (if not already present)."""
        if ctx.question_embedding:
            logger.debug("[AgenticProcessor] Skipping background embedding: already present.")
            return

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
        # USER_REQUEST: Removing this redundant generic event to avoid "plain" label in UI.
        # Sub-steps already provide the necessary info.
        if ctx.retrieved_sources:
            yield self._format_json_event({"type": "sources", "data": ctx.retrieved_sources})

    async def _stream_response_content(
        self, ctx: ChatContext, response: Any, stream_handler: Any, event_queue: Optional[asyncio.Queue] = None
    ) -> AsyncGenerator[str, None]:
        """Handles streaming the text tokens to the client using Robust Stream Parser."""
        # Streaming is technically a background child of the synthesis process in the UI
        stream_id = ctx.metrics.start_span(PipelineStepType.STREAMING)

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

        # Fallback for input tokens if 0 (common with some streams like OpenAI if not configured perfectly)
        if llm_input_tokens == 0:
            # Rough estimate: 1 token ~ 4 chars. This ensures cost is not 0.
            llm_input_tokens = len(ctx.message) // 4

        # Pass to metrics system
        ctx.metrics.end_span(
            stream_id,
            input_tokens=llm_input_tokens,
            output_tokens=llm_output_tokens or output_tokens,
            increment_total=True,
        )

    # --- Metrics & Formatter Helpers ---

    def _process_router_event(self, ctx: ChatContext, event: Any, parent_id: Optional[str] = None) -> str:
        """Helper to format router/agentic events for SSE."""
        # Extract fields from the router/callback event
        # (This handles both EventObject and dict-like objects)
        if isinstance(event, dict):
            step_type = event.get("step_type")
            status = event.get("status", "running")
            payload = SourceService._sanitize_data(event.get("payload", {}))
            label = event.get("label")
            duration = event.get("duration")
        else:
            step_type = event.step_type if hasattr(event, "step_type") else getattr(event, "event_type", "unknown")
            status = event.status if hasattr(event, "status") else "running"
            payload = event.payload if hasattr(event, "payload") else {}
            label = getattr(event, "label", None)
            duration = getattr(event, "duration", None)

        if step_type == "unknown" or not step_type:
            return ""

        if step_type == PipelineStepType.RETRIEVAL:
            is_sql_meta = payload.get("is_sql", False)
            step_type = PipelineStepType.SQL_SCHEMA_RETRIEVAL if is_sql_meta else PipelineStepType.ROUTER_RETRIEVAL

        # Inject model info for display
        if step_type in (
            PipelineStepType.ROUTER_REASONING,
            PipelineStepType.ROUTER_SYNTHESIS,
            PipelineStepType.ROUTER_SELECTION,
            PipelineStepType.QUERY_REWRITE,
            PipelineStepType.SQL_GENERATION,
        ):
            try:
                model_val = ctx.metadata.get("specific_model_name") or (
                    ctx.assistant.model.value if hasattr(ctx.assistant.model, "value") else str(ctx.assistant.model)
                )
                payload["model_name"] = model_val
                payload["model_provider"] = ctx.assistant.model_provider
            except Exception:
                pass

        if "is_substep" not in payload:
            payload["is_substep"] = True

        if step_type == PipelineStepType.ROUTER_RETRIEVAL and "source_count" in payload:
            del payload["source_count"]

        # 1. Resolve IDs for this event
        if isinstance(event, dict):
            step_id = event.get("step_id")
            incoming_parent_id = event.get("parent_id")
        else:
            step_id = getattr(event, "step_id", None)
            incoming_parent_id = getattr(event, "parent_id", None)

        # Point 1: Parent Normalization
        # Force orphans to be children of the main router span if their parent is unknown/not emitted
        emitted_ids = ctx.metadata.get("_emitted_step_ids", set())
        if incoming_parent_id and incoming_parent_id != parent_id and incoming_parent_id not in emitted_ids:
            logger.debug(f"Hiearchy: Normalizing orphaned parent {incoming_parent_id} -> {parent_id}")
            final_parent_id = parent_id
        else:
            final_parent_id = incoming_parent_id or parent_id

        if not step_id:
            # Fallback to stable ID for events without explicit ID (like manual spans)
            step_val = step_type.value if hasattr(step_type, "value") else str(step_type)
            step_id = f"router_{step_val}_{parent_id or 'global'}"

        # Track this ID as emitted for future children
        if "_emitted_step_ids" not in ctx.metadata:
            ctx.metadata["_emitted_step_ids"] = set()
        ctx.metadata["_emitted_step_ids"].add(step_id)

        # 2. Record completion metric if finished
        if status == StepStatus.COMPLETED:
            if duration is None:
                duration = 0.0

            # Double-Recording Prevention: If we handled this manually (e.g. QUERY_REWRITE),
            # don't record the internal LlamaIndex callback event as a separate step.
            if step_type == PipelineStepType.QUERY_REWRITE and ctx.metadata.get("_manual_rewrite_done"):
                return ""

            self._record_router_metric(ctx, step_type, label, duration, payload, parent_id=final_parent_id, step_id=step_id)

        # 3. Clean up payload
        if "is_substep" not in payload:
            payload["is_substep"] = True # Still hint for simple renderers

        if step_type == PipelineStepType.ROUTER_RETRIEVAL and "source_count" in payload:
            del payload["source_count"]

        return EventFormatter.format(
            step_type, 
            status, 
            step_id, 
            parent_id=final_parent_id, 
            payload=payload, 
            label=label, 
            duration=duration
        )

    def _record_router_metric(
        self, 
        ctx: ChatContext, 
        step_type: Any, 
        label: Optional[str], 
        duration: float, 
        payload: Dict,
        parent_id: Optional[str] = None,
        step_id: Optional[str] = None
    ):
        tokens = payload.get("tokens", {})
        ctx.metrics.record_completed_step(
            step_type=step_type,
            label=label,
            duration=duration,
            input_tokens=int(tokens.get("input", 0)),
            output_tokens=int(tokens.get("output", 0)),
            payload=payload,
            parent_id=parent_id,
            step_id=step_id
        )

    def _format_token(self, content: str) -> str:
        return json.dumps({"type": "token", "content": content, "text": content}, default=str) + "\n"

    def _format_json_event(self, data: Dict) -> str:
        return json.dumps(data, default=str) + "\n"
