import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.connector_sync_log import ConnectorSyncLog

logger = logging.getLogger(__name__)


class ConnectorSyncLogRepository:
    """
    Repository for Connector Sync Logs.
    Tracks history of synchronization runs for analytics.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(self, connector_id: UUID) -> ConnectorSyncLog:
        """Creates a new sync log entry with 'STARTING' status."""
        log = ConnectorSyncLog(
            connector_id=connector_id,
            status="syncing",  # Initial status
            documents_synced=0,
            sync_time=datetime.now(),
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def update_log(
        self, log_id: UUID, status: str, documents_synced: int = 0, error_message: Optional[str] = None
    ) -> Optional[ConnectorSyncLog]:
        """Updates an existing sync log with final status and metrics."""
        log = await self.db.get(ConnectorSyncLog, log_id)
        if not log:
            return None

        log.status = status
        log.documents_synced = documents_synced
        log.error_message = error_message

        # Calculate duration if possible
        if log.sync_time:
            delta = datetime.now() - log.sync_time.replace(
                tzinfo=None
            )  # naive calculation for simplicity or ensure both are aware
            log.sync_duration = delta.total_seconds()

        await self.db.commit()
        await self.db.refresh(log)
        return log
