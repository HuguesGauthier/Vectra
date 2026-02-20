import asyncio
import logging
import time
from typing import AsyncGenerator, List

from app.schemas.chat import Message
from app.services.chat.processors.base_chat_processor import BaseChatProcessor
from app.services.chat.types import ChatContext, PipelineStepType, StepStatus
from app.services.chat.utils import EventFormatter

logger = logging.getLogger(__name__)

# Constants
ROUNDING_PRECISION = 3
METRIC_LABEL = "History Loading"
TIMEOUT_HISTORY_LOAD = 2.0  # Seconds - Fail fast if Redis is lethargic
LOG_START = "⏳ HistoryProcessor: Loading chat history for session %s..."
LOG_SUCCESS = "✅ HistoryProcessor: Loaded %d messages for session %s in %ss"
LOG_ERROR = "❌ HistoryProcessor: Failed to load history for session %s: %s"
LOG_TIMEOUT = "⚠️ HistoryProcessor: Loading timed out for session %s. Starting with empty context."


class HistoryLoaderProcessor(BaseChatProcessor):
    """
    Processor responsible for loading chat history into the context.
    Protected with timeouts to prevent stalling the pipeline.
    """

    async def process(self, ctx: ChatContext) -> AsyncGenerator[str, None]:
        if not ctx.session_id:
            logger.warning("HistoryProcessor skipped: No session_id.")
            return

        start_time = time.time()
        yield self._emit_start_event(ctx)

        try:
            # 1. Load Data with Timeout (Circuit Breaker)
            history = await asyncio.wait_for(self._load_history(ctx), timeout=TIMEOUT_HISTORY_LOAD)
            ctx.history = history

            # 2. Metrics & Logs
            duration = self._calculate_duration(start_time)
            self._log_success(ctx.session_id, len(history), duration)
            self._record_metrics(ctx, duration)

            yield self._emit_completion_event(ctx, duration)

        except asyncio.TimeoutError:
            logger.warning(LOG_TIMEOUT, ctx.session_id)
            ctx.history = []  # Fallback to empty
            yield self._emit_completion_event(ctx, 0.0)  # Unblock UI

        except asyncio.CancelledError:
            # Re-raise to allow server shutdown/cancellation
            raise

        except Exception as e:
            # Fail Open: Don't crash the chat if history fails
            self._handle_error(ctx.session_id, e)
            ctx.history = []
            yield self._emit_completion_event(ctx, 0.0)  # Unblock UI

    def _emit_start_event(self, ctx: ChatContext) -> str:
        ctx.metadata["_history_step_id"] = ctx.metrics.start_span(PipelineStepType.HISTORY_LOADING)
        return EventFormatter.format(
            PipelineStepType.HISTORY_LOADING, StepStatus.RUNNING, ctx.metadata["_history_step_id"]
        )

    async def _load_history(self, ctx: ChatContext) -> List[Message]:
        return await ctx.chat_history_service.get_history(ctx.session_id)

    def _calculate_duration(self, start_time: float) -> float:
        return round(time.time() - start_time, ROUNDING_PRECISION)

    def _emit_completion_event(self, ctx: ChatContext, duration: float) -> str:
        sid = ctx.metadata.get("_history_step_id", "history_step")
        return EventFormatter.format(PipelineStepType.HISTORY_LOADING, StepStatus.COMPLETED, sid, duration=duration)

    def _record_metrics(self, ctx: ChatContext, duration: float) -> None:
        if ctx.metrics:
            ctx.metrics.record_completed_step(
                step_type=PipelineStepType.HISTORY_LOADING, label=METRIC_LABEL, duration=duration
            )

    def _log_success(self, session_id: str, count: int, duration: float) -> None:
        # Only log info if it took significant time, else debug
        if duration > 0.1:
            logger.info(LOG_SUCCESS, count, session_id, duration)
        else:
            logger.debug(LOG_SUCCESS, count, session_id, duration)

    def _handle_error(self, session_id: str, error: Exception) -> None:
        logger.error(LOG_ERROR, session_id, error, exc_info=True)
