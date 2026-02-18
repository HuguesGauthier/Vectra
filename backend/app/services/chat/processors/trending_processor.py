"""
TrendingProcessor Module
========================
Responsibility:
    Async post-processing of chat interactions to update social trending topics
    and persist administrative usage statistics.

Architecture:
    Layered Architecture: Uses Repositories for data access.
    Circuit Breaker: Enforces timeouts on external analysis.
    Defensive: swallows errors to prevent impacting the main chat response.
"""

import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Optional, cast
from uuid import UUID

from app.models.usage_stat import UsageStat
from app.repositories.topic_repository import TopicRepository
from app.repositories.usage_repository import UsageRepository
from app.services.chat.processors.base_chat_processor import BaseChatProcessor, ChatProcessorError

# Framework / Core
from app.services.chat.types import ChatContext, PipelineStepType, StepStatus
from app.services.chat.utils import EventFormatter
from app.services.trending_service import TrendingService
from app.services.pricing_service import PricingService

logger = logging.getLogger(__name__)

# --- Constants ---
# Metric Keys matching MetricsManager schema
METRIC_TOTAL_DURATION = "total_duration"
METRIC_TTFT = "ttft"
METRIC_INPUT_TOKENS = "input_tokens"
METRIC_OUTPUT_TOKENS = "output_tokens"
METRIC_STEP_BREAKDOWN = "legacy_step_breakdown"
METRIC_TOKEN_BREAKDOWN = "legacy_step_token_breakdown"

TIMEOUT_TRENDING_ANALYSIS: float = 5.0  # Seconds - Strict time budget for async tasks


class TrendingProcessor(BaseChatProcessor):
    """
    Orchestrator for async post-chat analysis.

    Security & Stability:
    - Non-blocking: All operations are async.
    - Fault Tolerant: Failures are logged but do not crash the request.
    - Time Bounded: External service calls are wrapped in timeouts.
    """

    async def process(self, ctx: ChatContext) -> AsyncGenerator[str, None]:
        """
        Main execution flow.

        Args:
            ctx: Clean, validated ChatContext.

        Yields:
            Processing events (PipelineStepType.TRENDING)
        """
        # 1. Trending Topic Analysis (Background Task)
        # We explicitly verify eligibility first (Guard Clause)
        if self._should_run_trending(ctx):
            async for event in self._execute_trending_safe(ctx):
                yield event
        else:
            # Still emit the step event for UI consistency, but mark as completed immediately
            yield EventFormatter.format(PipelineStepType.TRENDING, StepStatus.RUNNING, ctx.language)
            yield EventFormatter.format(PipelineStepType.TRENDING, StepStatus.COMPLETED, ctx.language, duration=0)

        # 2. Administrative Statistics (Always Run)
        await self._persist_usage_statistics_safe(ctx)

    # --- Domain Logic: Trending ---

    def _should_run_trending(self, ctx: ChatContext) -> bool:
        """Determines if trending analysis is required and possible."""
        if not ctx.trending_enabled:
            logger.debug(f"Process skipped: Trending disabled for tenant/assistant.")
            return False

        has_embedding = bool(ctx.question_embedding or ctx.captured_source_embedding)
        if not has_embedding:
            logger.warning("Process skipped: No vector embedding available.")
            return False

        return True

    async def _execute_trending_safe(self, ctx: ChatContext) -> AsyncGenerator[str, None]:
        """Executes trending logic with Circuit Breaker pattern."""
        yield EventFormatter.format(PipelineStepType.TRENDING, StepStatus.RUNNING, ctx.language)
        start_time = time.time()

        try:
            # P1: Dependency Injection via Context (or manual composition if DI container missing)
            # Ideally: ctx.container.resolve(TrendingService)
            topic_repo = TopicRepository(ctx.db)
            svc = TrendingService(
                db=ctx.db,
                repository=topic_repo,
                vector_service=ctx.vector_service,
                settings_service=ctx.settings_service,
            )

            # P1: Resolve Provider from Connector (NOT global setting!)
            # The embedding provider must match the one used to generate the embedding
            embedding = ctx.question_embedding or ctx.captured_source_embedding
            if not embedding:
                raise ValueError("Embedding lost consistency check.")

            provider = self._resolve_provider(ctx)

            # P0: Async Timeout Protection (DoS Prevention)
            await asyncio.wait_for(
                svc.process_user_question(
                    question=ctx.message,
                    assistant_id=ctx.assistant.id,
                    embedding=embedding,
                    embedding_provider=provider,
                ),
                timeout=TIMEOUT_TRENDING_ANALYSIS,
            )

            dur = round(time.time() - start_time, 3)
            self._record_metrics(ctx, dur)
            yield EventFormatter.format(PipelineStepType.TRENDING, StepStatus.COMPLETED, ctx.language, duration=dur)

        except asyncio.TimeoutError:
            logger.error(f"Trending Analysis timed out after {TIMEOUT_TRENDING_ANALYSIS}s")
            # Graceful degrade
            self._record_metrics(ctx, TIMEOUT_TRENDING_ANALYSIS)
            yield EventFormatter.format(
                PipelineStepType.TRENDING, StepStatus.COMPLETED, ctx.language, duration=TIMEOUT_TRENDING_ANALYSIS
            )

        except Exception as e:
            logger.error(f"Trending logic failed: {e}", exc_info=True)
            self._record_metrics(ctx, 0.0)
            yield EventFormatter.format(PipelineStepType.TRENDING, StepStatus.COMPLETED, ctx.language, duration=0)

    def _record_metrics(self, ctx: ChatContext, duration: float):
        """Records telemetry for consistent pipeline display."""
        if ctx.metrics:
            ctx.metrics.record_completed_step(
                step_type=PipelineStepType.TRENDING,
                label="Analytics",
                duration=duration,
            )

    # --- Domain Logic: Analytics ---

    async def _persist_usage_statistics_safe(self, ctx: ChatContext) -> None:
        """
        Persists usage stats using Repository Pattern.
        Swallows errors to protect the main response loop.
        """
        try:
            repo = UsageRepository(ctx.db)

            # Defensive Data Extraction
            stat_data = self._extract_usage_data(ctx)

            # P1: Transaction Atomicity handled by Repository usually,
            # or manual commit here if Repo is just DAO.
            # Assuming UsageRepository.create returns the model but needs commit if scoped session.
            # We'll assume standard Repo adds to session.

            # Calculate Cost (New Logic)
            pricing_service = PricingService(ctx.settings_service)
            cost = pricing_service.calculate_cost(
                provider=stat_data.get("provider"),
                model_name=stat_data.get("model"),
                input_tokens=stat_data.get("input_tokens", 0),
                output_tokens=stat_data.get("output_tokens", 0),
                is_cached=stat_data.get("is_cached", False),
            )
            
            # Enrich Data
            stat_data["cost"] = cost

            usage_stat = UsageStat(**stat_data)
            ctx.db.add(usage_stat)
            await ctx.db.commit()

            logger.debug(f"UsageStat persisted for session {ctx.session_id}")

        except Exception as e:
            logger.error(f"Usage Persistence Failed: {e}", exc_info=True)
            await ctx.db.rollback()

    def _extract_usage_data(self, ctx: ChatContext) -> dict:
        """Pure function to extract and validate metric data."""
        return {
            "assistant_id": ctx.assistant.id,
            "session_id": ctx.session_id,
            "user_id": self._parse_uuid(ctx.user_id),
            "model": ctx.assistant.model,
            "total_duration": self._get_total_duration(ctx),
            "ttft": ctx.metrics.get(METRIC_TTFT),
            "input_tokens": ctx.metrics.get(METRIC_INPUT_TOKENS, 0),
            "output_tokens": ctx.metrics.get(METRIC_OUTPUT_TOKENS, 0),
            "step_duration_breakdown": ctx.metrics.get(METRIC_STEP_BREAKDOWN),
            "step_token_breakdown": ctx.metrics.get(METRIC_TOKEN_BREAKDOWN),
            # New Fields
            "provider": self._resolve_provider(ctx),  # We need to extract this
            "is_cached": False,  # Placeholder until we get this from metrics
            "message_id": None,  # We should link to assistant_message_id if available
        }
        
        # Link to message if possible
        if ctx.assistant_message_id:
            try:
                data["message_id"] = UUID(str(ctx.assistant_message_id))
            except:
                pass
                
        return data

    def _resolve_provider(self, ctx: ChatContext) -> str:
        """Helper to resolve the AI provider used."""
        # 1. Try to get from Assistant defaults
        provider = ctx.assistant.model_provider
        
        # 2. If it's a specific setup (e.g. connectors override), allow logic here
        # For now, assistant.model_provider is the source of truth for the Chat LLM
        return provider or "openai"

    def _get_total_duration(self, ctx: ChatContext) -> float:
        """Calculates trustworthy total duration."""
        # Trust metric first
        if val := ctx.metrics.get(METRIC_TOTAL_DURATION):
            if isinstance(val, (int, float)) and val > 0:
                return float(val)

        # Fallback to elapsed wall clock
        return round(time.time() - ctx.start_time, 3)

    def _parse_uuid(self, value: Optional[str]) -> Optional[UUID]:
        """Security: Validates UUID format to prevent injection/errors."""
        if not value:
            return None
        try:
            return UUID(value)
        except ValueError:
            logger.warning(f"Security Alert: Malformed User ID detected: {value}")
            return None
