import asyncio
import logging
import os
import time
from typing import Annotated, Any, Dict, List, Optional, Set
from uuid import UUID

from fastapi import Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.connection_manager import manager
from app.core.database import SessionLocal, get_db
from app.core.exceptions import (EntityNotFound, FunctionalError,
                                 InternalDataCorruption, TechnicalError)
from app.models.connector import Connector
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.vector_repository import VectorRepository
from app.schemas.connector import (ConnectorCreate, ConnectorResponse,
                                   ConnectorUpdate)
from app.schemas.enums import ConnectorStatus, ConnectorType
from app.services.ingestion_service import IngestionService
from app.services.scanner_service import ScannerService
from app.services.settings_service import SettingsService, get_settings_service
from app.services.sql_discovery_service import (SQLDiscoveryService,
                                                get_sql_discovery_service)
from app.services.vector_service import VectorService, get_vector_service

logger = logging.getLogger(__name__)

# 🔵 P3: Extracted Magic Literals & Config
SCHEDULE_MAP = {
    "daily": "0 0 * * *",
    "weekly": "0 0 * * 0",
    "monthly": "0 0 1 * *",
    "5m": "*/5 * * * *",
    "manual": None,
}

# 🔴 P0: Security Constraint - Only allow deletion in managed directories
MANAGED_UPLOAD_DIR = "temp_uploads"


class ConnectorService:
    """
    Architect Refactor of ConnectorService.
    Ensures Pydantic returns (P0), non-blocking IO (P0), and modular DI (P1).
    Security Hardened: Prevents arbitrary file deletion.
    """

    # 🟠 P1: Prevent GC of fire-and-forget tasks
    _background_tasks: Set[asyncio.Task] = set()

    def __init__(
        self,
        connector_repo: ConnectorRepository,
        scanner_service: ScannerService,
        vector_service: Optional[VectorService] = None,
        settings_service: Optional[SettingsService] = None,
        sql_discovery_service: Optional[SQLDiscoveryService] = None,
    ):
        self.connector_repo = connector_repo
        self.scanner_service = scanner_service
        self.db = connector_repo.db
        self.settings_service = settings_service or SettingsService(self.db)
        self.vector_service = vector_service or VectorService(self.settings_service)
        self.sql_discovery_service = sql_discovery_service or SQLDiscoveryService(self.db, self.settings_service)

    @staticmethod
    async def _run_blocking_io(func, *args):
        """Wrapper for safe non-blocking IO operations. Fixes P0 Blocking IO."""
        return await asyncio.to_thread(func, *args)

    def _track_task(self, coro) -> asyncio.Task:
        """
        🟠 P1: Robust Background Task Execution.
        Creates a task and keeps a strong reference to prevent GC during execution.
        """
        task = asyncio.create_task(coro)
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
        return task

    async def get_connectors(self) -> List[ConnectorResponse]:
        """
        Retrieves all connectors with computed last_vectorized_at.
        Fixes P0: Returns ConnectorResponse.
        """
        start_time = time.time()
        func_name = "ConnectorService.get_connectors"

        try:
            # 🟠 P1: Potential N+1 / Large Payload.
            # Ideally should accept pagination params (skip, limit).
            # Assuming Repo handles efficient fetching.
            connectors = await self.connector_repo.get_all_with_stats()

            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.info(f"FETCH | {func_name} | Count: {len(connectors)} | {elapsed}ms")

            # 🔴 P0: Convert ORM to Pydantic
            return [ConnectorResponse.model_validate(c) for c in connectors]

        except Exception as e:
            logger.error(f"❌ FAIL | {func_name} | {e}", exc_info=True)
            raise TechnicalError(f"Failed to fetch connectors: {e}", error_code="FETCH_ERROR")

    async def get_connector(self, connector_id: UUID) -> Optional[ConnectorResponse]:
        """
        Fetch single connector.
        Fixes P0: Returns ConnectorResponse.
        """
        try:
            connector = await self.connector_repo.get_by_id(connector_id)
            if not connector:
                return None
            return ConnectorResponse.model_validate(connector)
        except Exception as e:
            logger.error(f"❌ FAIL | Connector retrieval {connector_id} | {e}")
            raise TechnicalError(f"Fetch failed", error_code="FETCH_ERROR")

    async def create_connector(self, connector_data: ConnectorCreate) -> ConnectorResponse:
        """
        Create new connector and trigger initial background scan.
        Fixes P0: Returns ConnectorResponse.
        """
        start_time = time.time()
        func_name = "ConnectorService.create_connector"

        try:
            # 1. Validation Logic
            # ARCHITECT FIX: Prioritize explicit cron from frontend
            if connector_data.schedule_cron:
                schedule_cron = connector_data.schedule_cron
            else:
                schedule_cron = self._resolve_schedule(connector_data.schedule_type)

            # 🟡 P2: Use Enum instead of Magic String
            if connector_data.connector_type == ConnectorType.LOCAL_FILE:
                await self._validate_file_path(connector_data.configuration)
            elif connector_data.connector_type == ConnectorType.LOCAL_FOLDER:
                await self._validate_folder_path(connector_data.configuration)

            # 2. DB Creation
            data = connector_data.model_dump()
            data["schedule_cron"] = schedule_cron
            data["status"] = ConnectorStatus.IDLE

            new_connector = await self.connector_repo.create(data)

            # 3. Side Effects (Backgrounded)
            if new_connector.connector_type in [ConnectorType.LOCAL_FILE, ConnectorType.LOCAL_FOLDER]:
                # 🟠 P1: Supervised background task
                self._track_task(self._safe_background_scan(new_connector.id, new_connector.configuration))
            elif new_connector.connector_type == ConnectorType.SQL:
                # 🔵 Automatic Discovery for SQL
                self._track_task(self.scan_connector(new_connector.id))

            resp = ConnectorResponse.model_validate(new_connector)
            await manager.emit_connector_created(resp.model_dump(mode="json"))

            elapsed = round((time.time() - start_time) * 1000, 2)
            logger.info(f"CREATED | {func_name} | {new_connector.id} | {elapsed}ms")

            return ConnectorResponse.model_validate(new_connector)

        except (FunctionalError, IntegrityError):
            raise
        except Exception as e:
            logger.error(f"❌ FAIL | {func_name} | {e}", exc_info=True)
            raise TechnicalError("Creation failed", error_code="CREATION_ERROR") from e

    async def update_connector(self, connector_id: UUID, connector_update: ConnectorUpdate) -> ConnectorResponse:
        """
        Partial update of connector with configuration change handling.
        Fixes P0: Returns ConnectorResponse.
        """
        try:
            db_connector = await self.connector_repo.get_by_id(connector_id)
            if not db_connector:
                raise EntityNotFound(f"Connector {connector_id} not found")

            old_config = db_connector.configuration or {}
            update_data = connector_update.model_dump(exclude_unset=True)

            # ARCHITECT FIX: Prioritize explicit cron from frontend
            if connector_update.schedule_cron is not None:
                update_data["schedule_cron"] = connector_update.schedule_cron
            elif connector_update.schedule_type:
                # Only resolve if no explicit cron provided (Backward compat)
                resolved = self._resolve_schedule(connector_update.schedule_type)
                # FIX: Apply resolved schedule if type is known (even if resolved is None, e.g. manual)
                if connector_update.schedule_type in SCHEDULE_MAP:
                    update_data["schedule_cron"] = resolved

            if connector_update.configuration:
                # Type-specific validation
                if db_connector.connector_type == ConnectorType.LOCAL_FILE:
                    await self._validate_file_path(connector_update.configuration)
                elif db_connector.connector_type == ConnectorType.LOCAL_FOLDER:
                    await self._validate_folder_path(connector_update.configuration)

                    new_path = connector_update.configuration.get("path")
                    old_path = old_config.get("path")

                    new_recursive = connector_update.configuration.get("recursive")
                    old_recursive = old_config.get("recursive")

                    # ARCHITECT FIX: Automatic Stop on Critical Change
                    critical_change = (old_path and new_path != old_path) or (
                        new_recursive is not None and new_recursive != old_recursive
                    )

                    if critical_change:
                        if db_connector.status in [
                            ConnectorStatus.STARTING,
                            ConnectorStatus.SYNCING,
                            ConnectorStatus.VECTORIZING,
                        ]:
                            logger.info(f"🛑 Auto-Stopping connector {connector_id} due to config change.")
                            update_data["status"] = ConnectorStatus.IDLE

                    # 🔴 P0 SECURITY FIX: Only delete file if it was a MANAGED FILE and path changed.
                    # NEVER delete local folders or arbitrary user paths.
                    # For FOLDERS, we generally don't delete content on update, just path change.

                # Handle file deletion for LOCAL_FILE if path changed
                if db_connector.connector_type == ConnectorType.LOCAL_FILE and connector_update.configuration:
                    new_path = connector_update.configuration.get("path")
                    old_path = old_config.get("path")

                    if old_path and new_path != old_path:
                        # Only delete if it appears to be in our managed upload dir (Security Guard)
                        if self._is_managed_path(old_path):
                            self._track_task(self._safe_delete_file(old_path))
                        else:
                            logger.warning(f"SKIPPING DELETION | path '{old_path}' is outside managed area.")

                # Update ACLs if changed (P1 backgrounded)
                new_acl = connector_update.configuration.get("connector_acl")
                if new_acl:
                    self._track_task(self._safe_update_acl(connector_id, new_acl, connector_update.configuration))

            # Apply via Repository
            updated_connector = await self.connector_repo.update(connector_id, update_data)

            # Invalidate SQL engine cache when connector configuration changes
            if self.sql_discovery_service and self.sql_discovery_service.engine_cache:
                if connector_update.configuration:
                    invalidated = self.sql_discovery_service.engine_cache.invalidate_connector(connector_id)
                    if invalidated > 0:
                        logger.info(
                            f"SQL_ENGINE_CACHE | Invalidated {invalidated} cached engines due to connector update"
                        )

            # Post-Update Side Effects
            if (
                updated_connector.connector_type in [ConnectorType.LOCAL_FILE, ConnectorType.LOCAL_FOLDER]
                and connector_update.configuration
            ):
                if updated_connector.status == ConnectorStatus.IDLE:
                    self._track_task(self._safe_background_scan(updated_connector.id, updated_connector.configuration))
            elif updated_connector.connector_type == ConnectorType.SQL and connector_update.configuration:
                # Trigger re-discovery on SQL config change
                self._track_task(self.scan_connector(updated_connector.id))

            resp = ConnectorResponse.model_validate(updated_connector)
            await manager.emit_connector_updated(resp.model_dump(mode="json"))
            return resp

        except Exception as e:
            if isinstance(e, (EntityNotFound, FunctionalError)):
                raise
            logger.error(f"❌ UPDATE FAIL | {connector_id} | {e}", exc_info=True)
            raise TechnicalError("Update failed", error_code="UPDATE_ERROR")

    async def delete_connector(self, connector_id: UUID) -> bool:
        """
        Delete connector and clean up external resources.
        Fixes P0: Uses non-blocking cleanup.
        """
        try:
            db_connector = await self.connector_repo.get_by_id(connector_id)
            if not db_connector:
                raise EntityNotFound(f"Connector {connector_id} not found")

            # 1. Async Cleanup External Resources
            if db_connector.configuration:
                # 🔴 P0 SECURITY FIX: Guarded Deletion
                if db_connector.connector_type == ConnectorType.LOCAL_FILE:
                    path = db_connector.configuration.get("path")
                    if path and self._is_managed_path(path):
                        self._track_task(self._safe_delete_file(path))

                # Vector DB cleanup
                self._track_task(self._safe_delete_vectors(connector_id, db_connector.configuration))

            # 2. DB Cleanup
            await self.connector_repo.delete_with_relations(connector_id)

            # Invalidate SQL engine cache when connector is deleted
            if self.sql_discovery_service and self.sql_discovery_service.engine_cache:
                invalidated = self.sql_discovery_service.engine_cache.invalidate_connector(connector_id)
                if invalidated > 0:
                    logger.info(
                        f"SQL_ENGINE_CACHE | Invalidated {invalidated} cached engines due to connector deletion"
                    )

            await manager.emit_connector_deleted(connector_id)
            return True

        except Exception as e:
            if isinstance(e, EntityNotFound):
                raise
            logger.error(f"❌ DELETE FAIL | {connector_id} | {e}", exc_info=True)
            raise TechnicalError("Delete failed", error_code="DELETE_ERROR")

    async def stop_connector(self, connector_id: UUID) -> ConnectorResponse:
        """Gracefully stop a running connector."""
        try:
            connector = await self.connector_repo.get_by_id(connector_id)
            if not connector:
                raise EntityNotFound(f"Connector {connector_id} not found")

            if connector.status in [ConnectorStatus.STARTING, ConnectorStatus.SYNCING, ConnectorStatus.VECTORIZING]:
                updated = await self.connector_repo.update(connector_id, {"status": ConnectorStatus.PAUSED})
                resp = ConnectorResponse.model_validate(updated)
                await manager.emit_connector_updated(resp.model_dump(mode="json"))
                return resp

            return ConnectorResponse.model_validate(connector)
        except Exception as e:
            if isinstance(e, EntityNotFound):
                raise
            logger.error(f"Stop connector failed: {e}")
            raise TechnicalError("Failed to stop connector", error_code="STOP_ERROR")

    async def trigger_sync(self, connector_id: UUID, force: bool = False) -> ConnectorResponse:
        """Queue a connector for synchronization."""
        try:
            connector = await self.connector_repo.get_by_id(connector_id)
            if not connector:
                raise EntityNotFound(f"Connector {connector_id} not found")

            if connector.status == ConnectorStatus.VECTORIZING:
                return ConnectorResponse.model_validate(connector)

            update_data = {"status": ConnectorStatus.QUEUED, "last_error": None}

            if force:
                new_conf = dict(connector.configuration or {})
                new_conf["force_sync"] = True
                update_data["configuration"] = new_conf

            updated = await self.connector_repo.update(connector_id, update_data)
            resp = ConnectorResponse.model_validate(updated)
            await manager.emit_connector_updated(resp.model_dump(mode="json"))
            return resp
        except Exception as e:
            if isinstance(e, EntityNotFound):
                raise
            logger.error(f"Trigger sync failed: {e}")
            raise TechnicalError("Trigger sync failed", error_code="SYNC_ERROR")

    async def scan_connector(self, connector_id: UUID) -> ConnectorResponse:
        """Triggers a MANUAL foreground scan."""
        try:
            connector = await self.connector_repo.get_by_id(connector_id)
            if not connector:
                raise EntityNotFound(f"Connector {connector_id} not found")

            # 🟡 P2: Enum Usage
            # Supported types for manual scan
            supported_types = [
                ConnectorType.LOCAL_FILE,
                ConnectorType.LOCAL_FOLDER,
                ConnectorType.SQL,  # Added support
                ConnectorType.VANNA_SQL,  # Added support for Vanna SQL
                "vanna_sql",  # String fallback
            ]

            logger.info(
                f"SCAN START | Connector: {connector.id} | Type: {connector.connector_type} (Expected SQL: {ConnectorType.SQL})"
            )

            if connector.connector_type not in supported_types:
                raise FunctionalError(
                    f"Connector type '{connector.connector_type}' cannot be scanned manually", error_code="INVALID_TYPE"
                )

            # Branching Logic
            # Branching Logic
            if connector.connector_type in [ConnectorType.SQL, ConnectorType.VANNA_SQL, "vanna_sql"]:
                # SQL Scan (including Vanna SQL)
                logger.info("SCAN ROUTE | SQL PATH SELECTED")
                await self.sql_discovery_service.scan_and_persist_views(connector.id)

            elif connector.connector_type == ConnectorType.LOCAL_FILE:
                # File Scan
                logger.info("SCAN ROUTE | FILE PATH SELECTED")
                path = connector.configuration.get("path")
                if not path:
                    raise FunctionalError("Invalid config: path missing", error_code="INVALID_CONFIG")
                await self.scanner_service.scan_folder(connector.id, path, recursive=False)

            elif connector.connector_type == ConnectorType.LOCAL_FOLDER:
                # Folder Scan
                logger.info("SCAN ROUTE | FOLDER PATH SELECTED")
                path = connector.configuration.get("path")
                if not path:
                    raise FunctionalError("Invalid config: path missing", error_code="INVALID_CONFIG")
                recursive = connector.configuration.get("recursive", False)
                await self.scanner_service.scan_folder(connector.id, path, recursive=recursive)

            else:
                raise FunctionalError("Invalid config: unknown connector type", error_code="INVALID_CONFIG")

            # Fetch fresh record after scan side-effects
            fresh = await self.connector_repo.get_by_id(connector_id)
            return ConnectorResponse.model_validate(fresh)

        except Exception as e:
            if isinstance(e, (EntityNotFound, FunctionalError)):
                raise
            logger.error(f"Manual scan failed: {e}", exc_info=True)
            raise TechnicalError("Scan failed", error_code="SCAN_ERROR")

    # --- Helpers ---
    @staticmethod
    def _resolve_schedule(schedule_type: str) -> Optional[str]:
        """Maps simplified schedule types to cron expressions."""
        return SCHEDULE_MAP.get(schedule_type, None)

    @staticmethod
    def _is_managed_path(path: str) -> bool:
        """
        🔴 P0 SECURITY: Guardrail.
        Returns True if the path lies within the managed 'uploads' directory.
        Used to prevent accidental deletion of user system files.
        """
        if not path:
            return False
        try:
            # Normalize path
            abs_path = os.path.abspath(path)
            # We assume the uploads dir is relative to current working dir or configured root.
            # Ideally this should come from SettingsService, but strict relative check is a good start.
            managed_root = os.path.abspath(MANAGED_UPLOAD_DIR)
            return abs_path.startswith(managed_root)
        except Exception:
            return False

    @classmethod
    async def _validate_file_path(cls, config: dict):
        """Non-blocking validation of file existence."""
        if not config or "path" not in config:
            raise FunctionalError("Invalid config: path missing", error_code="INVALID_CONFIG", status_code=400)

        path = config["path"]
        exists = await cls._run_blocking_io(os.path.isfile, path)
        if not exists:
            raise FunctionalError(f"File not found: {path}", error_code="FILE_NOT_FOUND", status_code=400)

    @classmethod
    async def _validate_folder_path(cls, config: dict):
        """Non-blocking validation of directory existence."""
        if not config or "path" not in config:
            return
        path = config["path"]
        exists = await cls._run_blocking_io(os.path.isdir, path)
        if not exists:
            raise FunctionalError(f"Path not found: {path}", error_code="PATH_NOT_FOUND", status_code=400)

    @classmethod
    async def _safe_delete_file(cls, path: str):
        """P0: Safe non-blocking file deletion."""
        try:
            exists = await cls._run_blocking_io(os.path.exists, path)
            if exists:
                await cls._run_blocking_io(os.remove, path)
                logger.debug(f"Deleted file: {path}")
        except Exception as e:
            logger.warning(f"Failed to delete file {path}: {e}")

    async def _safe_update_acl(self, connector_id: UUID, acl: list, config: dict):
        """Supervised background ACL update."""
        try:
            ai_provider = config.get("ai_provider")
            collection = await self.vector_service.get_collection_name(provider=ai_provider)

            client = self.vector_service.get_async_qdrant_client()
            repo = VectorRepository(client)
            await repo.update_acl(collection, "connector_id", str(connector_id), acl)

            logger.info(f"BACKGROUND ACL UPDATED | Connector: {connector_id}")
        except Exception as e:
            logger.error(f"BACKGROUND ACL FAIL | Connector: {connector_id} | Error: {e}")

    async def _safe_delete_vectors(self, connector_id: UUID, config: dict):
        """Supervised background vector deletion."""
        try:
            ai_provider = config.get("ai_provider")
            collection = await self.vector_service.get_collection_name(provider=ai_provider)

            client = self.vector_service.get_async_qdrant_client()
            repo = VectorRepository(client)
            await repo.delete_by_connector_id(collection, connector_id)

            logger.info(f"BACKGROUND VECTOR CLEANUP SUCCESS | Connector: {connector_id}")
        except Exception as e:
            logger.error(f"BACKGROUND VECTOR CLEANUP FAIL | Connector: {connector_id} | Error: {e}")

    async def _safe_background_scan(self, connector_id: UUID, config: dict):
        """Supervised background scan with fresh DB session."""
        try:
            async with SessionLocal() as db:
                recursive = config.get("recursive", False)

                path = config.get("path")
                if not path:
                    logger.warning(f"BACKGROUND SCAN | No path found for {connector_id}")
                    return

                scanner = ScannerService(db)
                await scanner.scan_folder(connector_id, path, recursive=recursive)
                logger.info(f"BACKGROUND SCAN SUCCESS | Connector: {connector_id}")
        except Exception as e:
            logger.error(f"BACKGROUND SCAN FAIL | Connector: {connector_id} | Error: {e}")


# 🟠 P1: Modern FastAPI dependency injection
async def get_connector_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    vector_service: Annotated[VectorService, Depends(get_vector_service)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
) -> ConnectorService:
    """Dependency provider for ConnectorService."""
    return ConnectorService(
        connector_repo=ConnectorRepository(db),
        scanner_service=ScannerService(db),
        vector_service=vector_service,
        settings_service=settings_service,
    )
