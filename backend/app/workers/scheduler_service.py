"""
Scheduler Service - Manages background scheduled tasks.

Handles system monitoring, log maintenance, and periodic business logic execution.
Refactored for instance-based lifecycle management and improved testability.
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import psutil
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import delete

from app.core.websocket import Websocket
from app.core.database import SessionLocal
from app.models.error_log import ErrorLog
from app.repositories.chat_history_repository import ChatPostgresRepository

# from app.services.analytics_service import AnalyticsService

from app.core.settings import settings

# Initialize logger
logger = logging.getLogger(__name__)

# Constants (Legacy fallbacks, preferably use settings)
HEARTBEAT_INTERVAL_SECONDS = 30
LOG_CLEANUP_HOUR_UTC = 3  # 3 AM UTC
LOG_CLEANUP_DAY = "sun"


class SchedulerService:
    """
    Service responsible for managing background scheduled tasks.
    Encapsulates APScheduler logic with robust configuration.
    """

    def __init__(self):
        """Initialize scheduler with production config."""
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._process: psutil.Process = psutil.Process()
        self._is_running = False

    def start(self):
        """
        Starts the AsyncIO scheduler.
        """
        if self._is_running:
            logger.warning("Scheduler is already running.")
            return

        try:
            # Robust configuration
            job_defaults = {
                "coalesce": True,  # If multiple runs missed, run only once
                "max_instances": 1,  # Prevent concurrent execution of same job
                "misfire_grace_time": 3600,  # 1 hour grace time
            }

            self._scheduler = AsyncIOScheduler(job_defaults=job_defaults, timezone=timezone.utc)

            # 1. Cleanup Logs (Weekly)
            self._scheduler.add_job(
                self.cleanup_old_logs,
                CronTrigger(day_of_week=LOG_CLEANUP_DAY, hour=LOG_CLEANUP_HOUR_UTC, timezone=timezone.utc),
                id="cleanup_logs",
                replace_existing=True,
            )

            # 2. Purge History (Daily) - Keep 1 Year
            self._scheduler.add_job(
                self.purge_old_history,
                CronTrigger(hour=LOG_CLEANUP_HOUR_UTC, minute=30, timezone=timezone.utc),  # Run at 03:30 AM
                id="purge_history",
                replace_existing=True,
            )

            self._scheduler.start()
            self._is_running = True
            logger.info("✅ Scheduler started successfully (UTC).")

        except Exception as e:
            logger.critical(f"❌ FAIL | SchedulerService.start | Error: {e}", exc_info=True)
            # P1: We don't crash the app if scheduler fails, but we log it as critical

    def shutdown(self):
        """Gracefully shuts down the scheduler."""
        if self._scheduler:
            try:
                if self._scheduler.running:
                    logger.info("Stopping scheduler...")
                    self._scheduler.shutdown()
                self._is_running = False
            except Exception as e:
                logger.error(f"Error during scheduler shutdown: {e}")
            finally:
                self._scheduler = None

    async def cleanup_old_logs(self):
        """
        Deletes error logs older than configured retention period.
        """
        start_time = time.time()
        func_name = "cleanup_old_logs"
        logger.info(f"START | {func_name}")

        try:
            # P1: Standardize on aware datetimes for comparison
            retention_days = getattr(settings, "LOG_RETENTION_DAYS", 30)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

            async with SessionLocal() as db:
                # Use standard SQLAlchemy delete statement
                statement = delete(ErrorLog).where(ErrorLog.timestamp < cutoff_date)
                result = await db.execute(statement)
                await db.commit()

                elapsed = round((time.time() - start_time) * 1000, 2)
                if result.rowcount > 0:
                    logger.info(f"FINISH | {func_name} | Deleted {result.rowcount} logs | Duration: {elapsed}ms")
                else:
                    logger.debug(f"FINISH | {func_name} | No logs to delete | Duration: {elapsed}ms")

        except Exception as e:
            logger.error(f"❌ FAIL | {func_name} | Error: {e}", exc_info=True)

    async def purge_old_history(self):
        """
        Deletes chat history older than 365 days.
        """
        start_time = time.time()
        func_name = "purge_old_history"
        logger.info(f"START | {func_name}")

        try:
            async with SessionLocal() as db:
                repo = ChatPostgresRepository(db)
                count = await repo.purge_old_messages(retention_days=365)

                elapsed = round((time.time() - start_time) * 1000, 2)
                if count > 0:
                    logger.info(f"FINISH | {func_name} | Purged {count} old messages | Duration: {elapsed}ms")
                else:
                    logger.debug(f"FINISH | {func_name} | No history to purge | Duration: {elapsed}ms")

        except Exception as e:
            logger.error(f"❌ FAIL | {func_name} | Error: {e}", exc_info=True)


# Singleton instance for application usage
scheduler_service = SchedulerService()


def start_scheduler():
    """
    Legacy entry point wrapper.
    Deprecation Note: Use scheduler_service.start() directly.
    """
    scheduler_service.start()
