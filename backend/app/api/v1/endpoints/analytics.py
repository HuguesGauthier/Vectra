"""
Advanced Analytics API Endpoints.
"""

import asyncio
import logging
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.core.database import get_session_factory
from app.schemas.advanced_analytics import (
    AdvancedAnalyticsResponse,
    AssistantCost,
    DocumentFreshness,
    TrendingTopic,
    TTFTPercentiles,
    StepBreakdown,  # Added StepBreakdown import
)
from app.services.analytics_service import AnalyticsService, get_analytics_service
from app.services.settings_service import SettingsService

router = APIRouter()
logger = logging.getLogger(__name__)

# Global flag for background task control
_broadcast_task: Optional[asyncio.Task[None]] = None
_broadcast_running: bool = False


@router.get("/advanced", response_model=AdvancedAnalyticsResponse)
async def get_advanced_analytics(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    assistant_id: Optional[UUID] = Query(None, description="Filter by assistant ID"),
    ttft_hours: int = Query(24, ge=1, le=168, description="TTFT analysis period in hours"),
    step_days: int = Query(7, ge=1, le=90, description="Step breakdown period in days"),
    cache_hours: int = Query(24, ge=1, le=168, description="Cache metrics period in hours"),
    cost_hours: int = Query(24, ge=1, le=168, description="Cost analysis period in hours"),
    trending_limit: int = Query(10, ge=1, le=50, description="Number of trending topics"),
) -> AdvancedAnalyticsResponse:
    """
    Get comprehensive advanced analytics for the admin dashboard.

    Args:
        service: The analytics service instance.
        assistant_id: Optional filter by assistant ID.
        ttft_hours: TTFT analysis period in hours.
        step_days: Step breakdown period in days.
        cache_hours: Cache metrics period in hours.
        cost_hours: Cost analysis period in hours.
        trending_limit: Number of trending topics.

    Returns:
        AdvancedAnalyticsResponse: A comprehensive analytics response including
            TTFT percentiles, pipeline step breakdown, cache hit rate, trending topics,
            topic diversity score, assistant token costs, and document freshness.
    """
    return await service.get_all_advanced_analytics(
        ttft_hours=ttft_hours,
        step_days=step_days,
        cache_hours=cache_hours,
        cost_hours=cost_hours,
        trending_limit=trending_limit,
        assistant_id=assistant_id,
    )


@router.get("/ttft", response_model=TTFTPercentiles)
async def get_ttft_percentiles(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    hours: int = Query(24, ge=1, le=168, description="Analysis period in hours"),
) -> TTFTPercentiles:
    """
    Get Time-to-First-Token percentiles.

    Args:
        service: The analytics service instance.
        hours: Analysis period in hours.

    Returns:
        TTFTPercentiles: The calculated TTFT percentiles (p50, p95, p99).
    """
    result: Optional[TTFTPercentiles] = await service.get_ttft_percentiles(hours)

    if not result:
        return TTFTPercentiles(p50=0.0, p95=0.0, p99=0.0, period_hours=hours)

    return result


@router.get("/trending", response_model=List[TrendingTopic])
async def get_trending_topics(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    assistant_id: Optional[UUID] = Query(None, description="Filter by assistant ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of topics to return"),
) -> List[TrendingTopic]:
    """
    Get top trending questions/topics.

    Args:
        service: The analytics service instance.
        assistant_id: Optional filter by assistant ID.
        limit: Number of topics to return.

    Returns:
        list[TrendingTopic]: A list of trending topics.
    """
    return await service.get_trending_topics(assistant_id, limit)


@router.get("/costs", response_model=List[AssistantCost])
async def get_assistant_costs(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
    hours: int = Query(24, ge=1, le=168, description="Analysis period in hours"),
) -> List[AssistantCost]:
    """
    Get token costs by assistant.

    Args:
        service: The analytics service instance.
        hours: Analysis period in hours.

    Returns:
        list[AssistantCost]: A list of costs per assistant.
    """
    return await service.get_assistant_costs(hours)


@router.get("/freshness", response_model=List[DocumentFreshness])
async def get_document_freshness(
    service: Annotated[AnalyticsService, Depends(get_analytics_service)],
) -> List[DocumentFreshness]:
    """
    Get knowledge base document freshness distribution.

    Args:
        service: The analytics service instance.

    Returns:
        list[DocumentFreshness]: A list representing document freshness distribution.
    """
    return await service.get_document_freshness()


async def broadcast_analytics_loop(interval_seconds: int = 10) -> None:
    """
    Background task that periodically broadcasts advanced analytics stats via WebSocket.

    Args:
        interval_seconds: Broadcast interval in seconds (default: 10).
            Higher than dashboard stats due to query complexity.
    """
    global _broadcast_running
    _broadcast_running = True

    logger.info("Starting advanced analytics broadcast loop (interval: %ds)", interval_seconds)

    from app.core.websocket import manager

    while _broadcast_running:
        try:
            factory = get_session_factory()
            settings_service = SettingsService(db=None)
            service: AnalyticsService = AnalyticsService(session_factory=factory, settings_service=settings_service)

            stats: AdvancedAnalyticsResponse = await service.get_all_advanced_analytics(
                ttft_hours=24, step_days=7, cache_hours=24, cost_hours=24, trending_limit=10
            )

            await manager.emit_advanced_analytics_stats(stats.model_dump(mode="json"))

        except Exception as e:
            logger.error("Error in analytics broadcast: %s", e, exc_info=True)

        await asyncio.sleep(interval_seconds)

    logger.info("Advanced analytics broadcast loop stopped")


async def start_broadcast_task(interval_seconds: int = 10) -> None:
    """
    Start the periodic broadcast background task.

    Args:
        interval_seconds: Broadcast interval in seconds.
    """
    global _broadcast_task, _broadcast_running

    if _broadcast_task is not None and not _broadcast_task.done():
        logger.warning("Analytics broadcast task already running")
        return

    _broadcast_running = True
    _broadcast_task = asyncio.create_task(broadcast_analytics_loop(interval_seconds))
    logger.info("Analytics broadcast task started")


async def stop_broadcast_task() -> None:
    """
    Stop the periodic broadcast background task.
    """
    global _broadcast_task, _broadcast_running

    if _broadcast_task is None:
        return

    _broadcast_running = False

    try:
        await asyncio.wait_for(_broadcast_task, timeout=10.0)
    except asyncio.TimeoutError:
        logger.warning("Analytics broadcast task did not stop gracefully, cancelling")
        _broadcast_task.cancel()
    except Exception as e:
        logger.error("Error during stop_broadcast_task: %s", e)

    _broadcast_task = None
    logger.info("Analytics broadcast task stopped")
