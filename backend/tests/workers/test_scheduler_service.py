import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
import sys

# Mock dependencies globally
sys.modules["psutil"] = MagicMock()
sys.modules["apscheduler"] = MagicMock()
sys.modules["apscheduler.schedulers.asyncio"] = MagicMock()
sys.modules["apscheduler.triggers.cron"] = MagicMock()
sys.modules["apscheduler.triggers.interval"] = MagicMock()

from app.workers.scheduler_service import SchedulerService


def test_scheduler_lifecycle():
    """Happy Path: Verify start and shutdown."""
    with patch("app.workers.scheduler_service.AsyncIOScheduler") as mock_sched_class:
        mock_sched = mock_sched_class.return_value
        service = SchedulerService()

        # Start
        service.start()
        assert service._is_running is True
        mock_sched.start.assert_called_once()
        assert mock_sched.add_job.call_count >= 2

        # Shutdown
        mock_sched.running = True
        service.shutdown()
        assert service._is_running is False
        mock_sched.shutdown.assert_called_once()
        assert service._scheduler is None


@pytest.mark.asyncio
async def test_cleanup_old_logs():
    """Happy Path: Verify cleanup logic."""
    service = SchedulerService()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 5
    mock_db.execute.return_value = mock_result

    with patch(
        "app.workers.scheduler_service.SessionLocal", return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_db))
    ):
        await service.cleanup_old_logs()

        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_purge_old_history():
    """Happy Path: Verify history purge logic."""
    service = SchedulerService()

    mock_db = AsyncMock()

    with patch(
        "app.workers.scheduler_service.SessionLocal", return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_db))
    ):
        with patch("app.workers.scheduler_service.ChatPostgresRepository") as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.purge_old_messages = AsyncMock(return_value=10)

            await service.purge_old_history()

            mock_repo.purge_old_messages.assert_called_once_with(retention_days=365)
