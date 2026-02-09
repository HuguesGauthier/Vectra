import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connection_manager import manager
from app.core.database import get_db
from app.core.time import SystemClock, TimeProvider
from app.models.enums import ConnectorStatus, DocStatus
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.document_repository import DocumentRepository
from app.schemas.connector import ConnectorResponse

logger = logging.getLogger(__name__)


class ConnectorStateService:
    """
    Centralized service for managing connector and document states.

    Responsibilities:
    - Update DB status and timestamps
    - Emit WebSocket events
    - Calculate final stats (completion)

    Resolves circular dependency between ConnectorService and IngestionService.
    """

    def __init__(self, db: AsyncSession, clock: TimeProvider | None = None):
        self.db = db
        self.clock = clock or SystemClock()
        self.connector_repo = ConnectorRepository(db)
        self.doc_repo = DocumentRepository(db)

    async def update_connector_status(self, connector_id: UUID, status: ConnectorStatus) -> None:
        """Update and emit connector status."""
        await self.connector_repo.update(connector_id, {"status": status})
        await manager.emit_connector_status(connector_id, status)

    async def update_document_status(self, doc_id: UUID, status: DocStatus, message: str = "") -> None:
        """Update and emit document status."""
        await self.doc_repo.update(doc_id, {"status": status})
        await manager.emit_document_update(str(doc_id), status, message)

    async def mark_connector_failed(self, connector_id: UUID, error: str) -> None:
        """Mark connector as failed with error message."""
        await self.connector_repo.update(connector_id, {"status": ConnectorStatus.ERROR, "last_error": error})
        await manager.emit_connector_status(connector_id, ConnectorStatus.ERROR)

    async def mark_document_failed(self, doc_id: UUID, error: str) -> None:
        """Mark document as failed with error message."""
        await self.doc_repo.update(doc_id, {"status": DocStatus.FAILED, "error_message": error})
        await manager.emit_document_update(str(doc_id), DocStatus.FAILED, error)

    async def finalize_connector(self, connector_id: UUID) -> None:
        """
        Set connector to IDLE and emit final status.
        Calculates total doc counts.
        """
        total_count = await self.doc_repo.count_by_connector(connector_id)
        updated = await self.connector_repo.update(
            connector_id,
            {
                "status": ConnectorStatus.IDLE,
                "last_vectorized_at": self.clock.utcnow(),
                "total_docs_count": total_count,
                "last_error": None,
            },
        )
        await manager.emit_connector_status(connector_id, ConnectorStatus.IDLE)

        # Emit full state (Pydantic prevents data leaks)
        resp = ConnectorResponse.model_validate(updated)
        await manager.emit_connector_updated(resp.model_dump(mode="json"))


# Dependency Injection
async def get_connector_state_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ConnectorStateService:
    return ConnectorStateService(db, clock=SystemClock())
