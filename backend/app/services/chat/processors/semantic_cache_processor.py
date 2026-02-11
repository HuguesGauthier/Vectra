import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.services.chat.chat_metrics_manager import ChatMetricsManager
from app.services.chat.processors.base_chat_processor import BaseChatProcessor
from app.services.chat.types import ChatContext, PipelineStepType, StepStatus
from app.services.chat.utils import EventFormatter

logger = logging.getLogger(__name__)

# Constants - Dictionary Keys
KEY_SOURCES = "sources"
KEY_METADATA = "metadata"
KEY_TEXT = "text"
KEY_ID = "id"
KEY_ID_CACHED = "cached"
KEY_SQL_RESULTS = "sql_results"
KEY_RESPONSE = "response"

# Constants - Event Types
TYPE_SOURCES = "sources"
TYPE_ERROR = "error"
TYPE_TOKEN = "token"

# Constants - Metrics & Logging
LOG_CACHE_HIT = "💨 CACHE HIT | Session: %s"
LOG_SQL_RESTORED = "✅ Restored %d SQL rows from cache for visualization"
LOG_CACHE_FAIL = "⚠️ Cache lookup failed for session %s: %s"
ROUNDING_PRECISION = 3


class SemanticCacheProcessor(BaseChatProcessor):
    """
    Processor responsible for checking semantic cache for existing answers.

    If a cache hit occurs, this processor will:
    1. Stream the cached sources and response.
    2. Restore validation data (SQL results).
    3. Short-circuit the pipeline (stop further processing).
    """

    async def process(self, ctx: ChatContext) -> AsyncGenerator[str, None]:
        """
        Executes the semantic cache lookup step.

        Args:
            ctx (ChatContext): The current chat execution context.

        Yields:
            str: JSON-formatted strings for events or content chunks.
        """
        if self._should_skip(ctx):
            return

        self._ensure_metrics_initialized(ctx)

        start_time = time.time()
        yield self._emit_start_event(ctx)

        try:
            # 1. Generate Input Embedding (Async Safe)
            embedding = await self._generate_query_embedding(ctx)
            ctx.question_embedding = embedding

            # 2. Perform Cache Lookup
            cached_res = await self._execute_cache_lookup(ctx, embedding)
            is_hit = bool(cached_res) and self._is_valid_cache_entry(cached_res)

            # 3. Handle Hit/Miss Logic
            if is_hit:
                # Update Context for Short-Circuit
                ctx.should_stop = True
                
                # Restore Context Data
                self._restore_context_data(ctx, cached_res)
                
                # Stream Response
                async for chunk in self._stream_cache_hit_response(ctx, cached_res):
                    yield chunk
            else:
                 # Miss implies no action needed on stream or context
                 pass

            # 4. Record Metrics & Emit Completion
            duration = self._calculate_duration(start_time)
            
            # Record step with hit status
            ctx.metrics.record_completed_step(
                step_type=PipelineStepType.CACHE_LOOKUP,
                label="Cache Lookup",
                duration=duration,
                payload={"hit": is_hit},
            )

            yield self._emit_completion_event(ctx, duration, is_hit)

        except Exception as e:
            self._handle_lookup_error(ctx, e)

    # --- Private Helpers: Preconditions & Setup ---

    def _should_skip(self, ctx: ChatContext) -> bool:
        """Checks if caching is enabled and available."""
        return not (ctx.cache_service and ctx.assistant.use_semantic_cache)

    def _ensure_metrics_initialized(self, ctx: ChatContext) -> None:
        """Ensures metrics manager exists to prevent AttributeErrors."""
        if not ctx.metrics:
            ctx.metrics = ChatMetricsManager()

    def _emit_start_event(self, ctx: ChatContext) -> str:
        return EventFormatter.format(PipelineStepType.CACHE_LOOKUP, StepStatus.RUNNING, ctx.language)

    # --- Private Helpers: Core Logic ---

    async def _generate_query_embedding(self, ctx: ChatContext) -> List[float]:
        """Retrieves the embedding for the user's message in a non-blocking way."""
        embed_model = await ctx.vector_service.get_embedding_model()
        
        # P0 FIX: Offload blocking IO/CPU to thread pool
        return await asyncio.to_thread(
            embed_model.get_text_embedding, 
            ctx.original_message
        )

    async def _execute_cache_lookup(self, ctx: ChatContext, embedding: List[float]) -> Optional[Dict[str, Any]]:
        """Queries the semantic cache service."""
        return await ctx.cache_service.get_cached_response(
            question=ctx.original_message,
            assistant_id=str(ctx.assistant.id),
            embedding=embedding,
            min_score=ctx.assistant.cache_similarity_threshold,
        )

    # --- Private Helpers: Hit/Miss Processing ---

    def _restore_context_data(self, ctx: ChatContext, cached_res: Dict[str, Any]) -> None:
        """Restores SQL results and other context data from cache."""
        logger.info(LOG_CACHE_HIT, ctx.session_id)
        
        # Restore SQL
        sql_results = cached_res.get(KEY_SQL_RESULTS)
        if sql_results:
            ctx.sql_results = sql_results
            logger.info(LOG_SQL_RESTORED, len(sql_results))
            
        # Restore Answer Text in Context
        content = cached_res.get(KEY_RESPONSE, "")
        ctx.full_response_text = content

    async def _stream_cache_hit_response(self, ctx: ChatContext, cached_res: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Streams the cached sources and content."""
        
        # 1. Sources
        if KEY_SOURCES in cached_res:
            raw_sources = cached_res[KEY_SOURCES]
            normalized_sources = self._normalize_sources(raw_sources)
            ctx.retrieved_sources = normalized_sources
            
            # Using manual json dump for now as EventFormatter might not handle specific source payloads
            # Review: Consider moving Source payload formatting to EventFormatter in future
            yield json.dumps({"type": TYPE_SOURCES, "data": normalized_sources}, default=str) + "\n"

        # 2. Content
        content = cached_res.get(KEY_RESPONSE, "")
        yield self._format_token_chunk(content)

    def _normalize_sources(self, raw_sources: List[Any]) -> List[Dict[str, Any]]:
        """Ensures all sources have a consistent structure."""
        normalized = []
        for s in raw_sources:
            if isinstance(s, dict) and KEY_METADATA in s:
                normalized.append(s)
            else:
                # Helper to wrap raw string/obj in a proper structure
                normalized.append({KEY_METADATA: s, KEY_TEXT: "", KEY_ID: KEY_ID_CACHED})
        return normalized

    # --- Private Helpers: Formatting & Utils ---

    def _calculate_duration(self, start_time: float) -> float:
        return round(time.time() - start_time, ROUNDING_PRECISION)

    def _emit_completion_event(self, ctx: ChatContext, duration: float, is_hit: bool) -> str:
        return EventFormatter.format(
            PipelineStepType.CACHE_LOOKUP,
            StepStatus.COMPLETED,
            ctx.language,
            duration=duration,
            payload={"hit": is_hit},
        )

    def _format_token_chunk(self, content: str) -> str:
        return json.dumps({"type": TYPE_TOKEN, "content": content}, default=str) + "\n"

    def _is_valid_cache_entry(self, cached: Dict[str, Any]) -> bool:
        """
        Validates the structure of the cached entry.
        """
        # Minimal validation: Must have a response to be useful
        return KEY_RESPONSE in cached

    def _handle_lookup_error(self, ctx: ChatContext, error: Exception) -> None:
        """Logs errors without crashing the pipeline (FAIL OPEN)."""
        logger.warning(LOG_CACHE_FAIL, ctx.session_id, error)
        # We don't yield anything here, just log and continue. 
        # The pipeline will proceed to the next step since should_stop is False.
