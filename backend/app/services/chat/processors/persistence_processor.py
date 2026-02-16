import logging
import time
from typing import Any, AsyncGenerator, Dict, Optional

from app.repositories.chat_history_repository import ChatPostgresRepository
from app.services.chat.processors.base_chat_processor import BaseChatProcessor
from app.services.chat.types import ChatContext, PipelineStepType, StepStatus
from app.services.chat.utils import EventFormatter

logger = logging.getLogger(__name__)

# Constants - Roles & Labels
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
LABEL_USER = "User Persistence"
LABEL_ASSISTANT = "Assistant Persistence"

# Constants - Cache Keys
KEY_RESPONSE = "response"
KEY_SOURCES = "sources"
KEY_SQL_RESULTS = "sql_results"
KEY_TIMESTAMP = "timestamp"

# Constants - Logs
LOG_HOT_FAIL = "❌ %s: Failed to save message to Hot Storage (Redis): %s"
LOG_COLD_FAIL = "❌ %s: Failed to save message to Cold Storage (Postgres): %s"
LOG_CACHE_FAIL = "⚠️ %s: Cache update failed: %s"
LOG_CACHE_SKIP = "ℹ️ %s: Skipping cache update (Cache Hit: %s, Embedding: %s)"
LOG_FINISH = "🏁 FINISH | Session: %s"

# Constants - Precision
ROUNDING_PRECISION = 3


class UserPersistenceProcessor(BaseChatProcessor):
    """
    Processor responsible for persisting the User's message.
    Writes to both Hot Storage (Redis) for context and Cold Storage (Postgres) for audit.
    """

    async def process(self, ctx: ChatContext) -> AsyncGenerator[str, None]:
        """
        Executes the user persistence step.
        """
        yield self._emit_start_event(ctx)
        start_time = time.time()

        # 1. Hot Storage (Context)
        await self._persist_to_hot_storage(ctx)

        # 2. Cold Storage (Audit)
        await self._persist_to_cold_storage(ctx)

        # 3. Metrics & Completion
        duration = self._calculate_duration(start_time)
        self._record_metrics(ctx, duration)

        yield self._emit_completion_event(ctx, duration)

    def _emit_start_event(self, ctx: ChatContext) -> str:
        return EventFormatter.format(PipelineStepType.USER_PERSISTENCE, StepStatus.RUNNING, ctx.language)

    async def _persist_to_hot_storage(self, ctx: ChatContext) -> None:
        """Saves message to Redis (Best Effort)."""
        try:
            await ctx.chat_history_service.add_message(ctx.session_id, ROLE_USER, ctx.message)
        except Exception as e:
            logger.error(LOG_HOT_FAIL, "UserProcessor", e)

    async def _persist_to_cold_storage(self, ctx: ChatContext) -> None:
        """Saves message to Postgres (Critical for History)."""
        try:
            audit_repo = ChatPostgresRepository(ctx.db)
            await audit_repo.add_message(
                ctx.session_id, ROLE_USER, ctx.message, assistant_id=ctx.assistant.id, user_id=ctx.user_id
            )
        except Exception as e:
            logger.error(LOG_COLD_FAIL, "UserProcessor", e)
            # We choose NOT to crash the chat if DB write fails, but log heavily.

    def _calculate_duration(self, start_time: float) -> float:
        return round(time.time() - start_time, ROUNDING_PRECISION)

    def _record_metrics(self, ctx: ChatContext, duration: float) -> None:
        if ctx.metrics:
            ctx.metrics.record_completed_step(
                step_type=PipelineStepType.USER_PERSISTENCE, label=LABEL_USER, duration=duration
            )

    def _emit_completion_event(self, ctx: ChatContext, duration: float) -> str:
        return EventFormatter.format(
            PipelineStepType.USER_PERSISTENCE, StepStatus.COMPLETED, ctx.language, duration=duration
        )


class AssistantPersistenceProcessor(BaseChatProcessor):
    """
    Processor responsible for persisting the Assistant's response.
    Writes to Hot/Cold storage and conditionally updates Semantic Cache.
    """

    async def process(self, ctx: ChatContext) -> AsyncGenerator[str, None]:
        """
        Executes the assistant persistence and cache update steps.
        """
        if self._should_skip(ctx):
            return

        logger.info(LOG_FINISH, ctx.session_id)

        # 1. Prepare Metadata (Common for Hot & Cold)
        metadata = self._prepare_metadata(ctx)

        # 2. Persistence
        await self._persist_to_hot_storage(ctx, metadata)
        async for event in self._persist_to_cold_storage_with_events(ctx, metadata):
            yield event

        # 3. Semantic Cache Update
        async for event in self._update_semantic_cache_if_needed(ctx):
            yield event

    def _should_skip(self, ctx: ChatContext) -> bool:
        return not ctx.full_response_text

    def _prepare_metadata(self, ctx: ChatContext) -> Dict[str, Any]:
        """Constructs and sanitizes metadata for persistence."""
        # Extract steps from metrics if available
        # Filter out system/infrastructure steps that shouldn't persist
        # Streaming is ephemeral, but Initialization is useful for history
        EXCLUDED_STEPS = {"streaming"}

        steps = []
        if ctx.metrics:
            summary = ctx.metrics.get_summary()
            for s in summary.get("step_breakdown", []):
                # Skip system steps
                if s.get("step_type") in EXCLUDED_STEPS:
                    continue

                s["status"] = "completed"
                # Keep the label - it's needed for frontend display on reload
                steps.append(s)

        metadata = {
            "visualization": ctx.visualization,
            "sources": ctx.retrieved_sources,
            "steps": steps,
            "contentBlocks": ctx.metadata.get("content_blocks", []),
        }

        # P0 FEATURE: Structured Context Persistence (Up to 100 rows)
        if ctx.sql_results:
            limit_rows = 100
            metadata["sql_results"] = ctx.sql_results[:limit_rows]
            metadata["structured_context_type"] = "sql"

            if len(ctx.sql_results) > limit_rows:
                metadata["sql_results_truncated"] = True

            logger.info(
                f"💾 Persisting Structured Context: {len(metadata['sql_results'])} rows (Total: {len(ctx.sql_results)})"
            )

        return self._sanitize_metadata(metadata)

    async def _persist_to_hot_storage(self, ctx: ChatContext, metadata: Dict[str, Any]) -> None:
        try:
            await ctx.chat_history_service.add_message(
                ctx.session_id, ROLE_ASSISTANT, ctx.full_response_text, metadata=metadata
            )
        except Exception as e:
            logger.error(LOG_HOT_FAIL, "AssistantProcessor", e)

    async def _persist_to_cold_storage_with_events(
        self, ctx: ChatContext, metadata: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """Persists to Postgres and yields UI events."""
        yield EventFormatter.format(PipelineStepType.ASSISTANT_PERSISTENCE, StepStatus.RUNNING, ctx.language)

        start_time = time.time()

        try:
            audit_repo = ChatPostgresRepository(ctx.db)
            ctx.assistant_message_id = await audit_repo.add_message(
                ctx.session_id,
                ROLE_ASSISTANT,
                ctx.full_response_text,
                assistant_id=ctx.assistant.id,
                user_id=ctx.user_id,
                additional_kwargs=metadata,
            )
        except Exception as e:
            logger.error(LOG_COLD_FAIL, "AssistantProcessor", e)

        duration = round(time.time() - start_time, ROUNDING_PRECISION)
        self._record_metrics(ctx, duration)
        yield EventFormatter.format(
            PipelineStepType.ASSISTANT_PERSISTENCE, StepStatus.COMPLETED, ctx.language, duration=duration
        )

    def _record_metrics(self, ctx: ChatContext, duration: float) -> None:
        if ctx.metrics:
            ctx.metrics.record_completed_step(
                step_type=PipelineStepType.ASSISTANT_PERSISTENCE, label=LABEL_ASSISTANT, duration=duration
            )

    def _sanitize_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures metadata is strictly JSON serializable by dumping to str if necessary."""
        import json

        try:
            # Fast path: try dump
            json.dumps(data)
            return data
        except (TypeError, OverflowError):
            # Slow path: clean recursive
            try:
                return json.loads(json.dumps(data, default=str))
            except Exception as e:
                logger.error(f"METADATA_SANITIZE_FAIL | Error: {e}")
                return {}

    # --- Cache Update Logic ---

    async def _update_semantic_cache_if_needed(self, ctx: ChatContext) -> AsyncGenerator[str, None]:
        if not self._should_cache(ctx):
            return

        yield EventFormatter.format(PipelineStepType.CACHE_UPDATE, StepStatus.RUNNING, ctx.language)

        await self._perform_cache_update(ctx)

        yield EventFormatter.format(PipelineStepType.CACHE_UPDATE, StepStatus.COMPLETED, ctx.language, duration=0.1)

    def _should_cache(self, ctx: ChatContext) -> bool:
        """
        Determines if we should save this interaction to the semantic cache.
        Rules:
        1. Cache service exists and is enabled.
        2. Valid question embedding exists.
        3. Only cache if it wasn't a cache hit (avoid loops).
        """
        is_cache_hit = ctx.metrics.get("cache_hit", False) if ctx.metrics else False

        return (
            not is_cache_hit
            and ctx.cache_service is not None
            and ctx.assistant.use_semantic_cache
            and ctx.question_embedding is not None
        )

    async def _perform_cache_update(self, ctx: ChatContext) -> None:
        try:
            payload = self._build_cache_payload(ctx)

            await ctx.cache_service.set_cached_response(
                question=ctx.original_message,
                assistant_id=str(ctx.assistant.id),
                embedding=ctx.question_embedding,
                response=payload,
            )
        except Exception as e:
            logger.warning(LOG_CACHE_FAIL, "AssistantProcessor", e)

    def _build_cache_payload(self, ctx: ChatContext) -> Dict[str, Any]:
        return {
            KEY_RESPONSE: ctx.full_response_text,
            KEY_SOURCES: ctx.retrieved_sources,
            KEY_SQL_RESULTS: ctx.sql_results,
            "visualization": ctx.visualization,
            KEY_TIMESTAMP: time.time(),
        }
