"""
Dashboard Statistics API Endpoint.

Provides REST endpoint for dashboard stats and manages periodic WebSocket broadcasts.
"""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.dashboard_stats import DashboardStats
from app.services.dashboard_stats_service import DashboardStatsService

router = APIRouter()
logger = logging.getLogger(__name__)

# Global flag for background task control
_broadcast_task: asyncio.Task | None = None
_broadcast_running: bool = False


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(db: Annotated[AsyncSession, Depends(get_db)]) -> DashboardStats:
    """
    Get current dashboard statistics (REST endpoint).

    This provides a synchronous way to fetch stats without WebSocket.

    Args:
        db: Database session.

    Returns:
        DashboardStats: The current dashboard statistics.
    """
    service = DashboardStatsService(db)
    stats = await service.get_all_stats()
    return stats


async def broadcast_dashboard_stats_loop(interval_seconds: int = 5) -> None:
    """
    Background task that periodically broadcasts dashboard stats via WebSocket.

    Args:
        interval_seconds: Broadcast interval in seconds (default: 5).

    Returns:
        None
    """
    global _broadcast_running
    _broadcast_running = True

    logger.info("Starting dashboard stats broadcast loop (interval: %ds)", interval_seconds)

    # Import here to avoid circular dependency
    from app.core.connection_manager import manager
    from app.core.database import SessionLocal

    while _broadcast_running:
        try:
            # Create a new database session for this iteration
            async with SessionLocal() as db:
                service = DashboardStatsService(db)
                stats = await service.get_all_stats()

                # Broadcast via WebSocket
                await manager.emit_dashboard_stats(stats.model_dump(mode="json"))

        except Exception as e:
            logger.error("Error in dashboard stats broadcast: %s", e, exc_info=True)

        # Wait for next interval
        await asyncio.sleep(interval_seconds)

    logger.info("Dashboard stats broadcast loop stopped")


async def start_broadcast_task(interval_seconds: int = 5) -> None:
    """
    Start the periodic broadcast background task.

    Args:
        interval_seconds: Broadcast interval in seconds.

    Returns:
        None
    """
    global _broadcast_task, _broadcast_running

    if _broadcast_task is not None and not _broadcast_task.done():
        logger.warning("Dashboard broadcast task already running")
        return

    _broadcast_running = True
    _broadcast_task = asyncio.create_task(broadcast_dashboard_stats_loop(interval_seconds))
    logger.info("Dashboard broadcast task started")


async def stop_broadcast_task() -> None:
    """
    Stop the periodic broadcast background task.

    Returns:
        None
    """
    global _broadcast_task, _broadcast_running

    if _broadcast_task is None:
        return

    _broadcast_running = False

    # Wait for task to finish (should exit quickly after flag set)
    try:
        if _broadcast_task:
            await asyncio.wait_for(_broadcast_task, timeout=10.0)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        if _broadcast_task:
            logger.warning("Dashboard broadcast task did not stop gracefully, cancelling")
            _broadcast_task.cancel()

    _broadcast_task = None
    logger.info("Dashboard broadcast task stopped")
