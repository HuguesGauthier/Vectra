"""
Unit tests for SchedulerService.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import psutil
import pytest

from app.workers.scheduler_service import SchedulerService, scheduler_service


@pytest.fixture
def mock_scheduler():
    service = SchedulerService()
    # Mock internal APScheduler
    service._scheduler = MagicMock()
    service._scheduler.running = False
    return service


def test_start_scheduler(mock_scheduler):
    """✅ SUCCESS: Scheduler starts correctly."""
    with patch("app.workers.scheduler_service.AsyncIOScheduler") as mock_cls:
        mock_instance = mock_cls.return_value

        mock_scheduler.start()

        assert mock_scheduler._is_running is True
        mock_instance.start.assert_called_once()
        # Verify jobs added
        assert mock_instance.add_job.call_count >= 2


def test_start_scheduler_idempotent(mock_scheduler):
    """✅ SUCCESS: Scheduler start is idempotent."""
    mock_scheduler._scheduler.running = True
    mock_scheduler._is_running = True

    with patch("app.workers.scheduler_service.AsyncIOScheduler") as mock_cls:
        mock_scheduler.start()
        # Should not start again
        mock_cls.return_value.start.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_system_status():
    """✅ SUCCESS: System metrics broadcast uses non-blocking calls."""
    service = SchedulerService()

    # Mock psutil
    with (
        patch("psutil.cpu_percent", return_value=50.0),
        patch("psutil.virtual_memory") as mock_mem,
        patch("app.core.connection_manager.manager.emit_system_metrics", new_callable=AsyncMock) as mock_emit,
    ):

        mock_mem.return_value.percent = 60.0
        service._process.cpu_percent = MagicMock(return_value=10.0)
        service._process.memory_percent = MagicMock(return_value=5.0)

        await service.broadcast_system_status()

        mock_emit.assert_awaited_once_with(
            cpu=50.0, memory=60.0, cpu_process=pytest.approx(10.0 / psutil.cpu_count(), 0.1), memory_process=5.0
        )


@pytest.mark.asyncio
async def test_cleanup_logs_db_interaction():
    """✅ SUCCESS: Log cleanup uses correct DB query."""
    service = SchedulerService()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 5
    mock_db.execute.return_value = mock_result

    # Mock context manager: SessionLocal() returns an object whose __aenter__ returns mock_db
    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_db

    with patch("app.workers.scheduler_service.SessionLocal", mock_session_factory):
        await service.cleanup_old_logs()

        mock_db.execute.assert_awaited_once()
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_logs_error_handling():
    """❌ FAILURE: Cleanup logs handles DB errors gracefully."""
    service = SchedulerService()

    mock_db = AsyncMock()
    # Ensure execute raises generic exception
    mock_db.execute.side_effect = Exception("DB Down")

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_db

    with (
        patch("app.workers.scheduler_service.SessionLocal", mock_session_factory),
        patch("app.workers.scheduler_service.logger") as mock_logger,
    ):

        await service.cleanup_old_logs()

        # Should catch and log error
        mock_logger.error.assert_called_once()
        assert "FAIL" in mock_logger.error.call_args[0][0]
