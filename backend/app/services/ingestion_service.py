import asyncio
import logging
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket import manager
from app.core.database import get_db
from app.core.exceptions import ConfigurationError, EntityNotFound, FileSystemError
from app.core.interfaces.base_connector import get_full_path_from_connector
from app.core.time import SystemClock, TimeProvider
from app.factories.connector_factory import ConnectorFactory
from app.models.enums import ConnectorStatus, DocStatus
from app.repositories.connector_repository import ConnectorRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.vector_repository import VectorRepository
from app.schemas.enums import ConnectorType
from app.services.connector_state_service import ConnectorStateService, get_connector_state_service
from app.services.ingestion.ingestion_orchestrator import IngestionOrchestrator
from app.services.schema_discovery_service import SchemaDiscoveryService, get_schema_discovery_service
from app.services.settings_service import SettingsService, get_settings_service
from app.services.sql_discovery_service import SQLDiscoveryService, get_sql_discovery_service
from app.services.vector_service import VectorService, get_vector_service

# ============================================================================
# TIME PROVIDER (P0 Fix: Testable Time Abstraction)
# ============================================================================


logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


class IngestionConfig(BaseModel):
    """Centralized configuration for ingestion pipeline."""

    # Only ingestion operational configs remain
    csv_max_size_mb: int = Field(10, ge=1, description="Max CSV file size in MB")


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================


class IngestionStoppedError(Exception):
    """Raised when ingestion is manually stopped by user."""

    pass


class TransientIngestionError(Exception):
    """Temporary failures (network, timeouts) that should trigger retry."""

    pass


# ============================================================================
# MAIN SERVICE
# ============================================================================


class IngestionService:
    """
    Production-grade ingestion orchestrator.
    SRP Compliant: Delegates Schema Discovery and Vector Mgmt.
    """

    def __init__(
        self,
        db: AsyncSession,
        vector_service: VectorService | None = None,
        settings_service: SettingsService | None = None,
        state_service: ConnectorStateService | None = None,
        schema_service: SchemaDiscoveryService | None = None,
        sql_service: SQLDiscoveryService | None = None,
        clock: TimeProvider | None = None,
        config: IngestionConfig | None = None,
    ):
        """
        Initialize service with explicit dependencies.
        """
        self.db = db
        self.settings_service = settings_service or SettingsService(db)
        self.vector_service = vector_service or VectorService(self.settings_service)
        self.clock = clock or SystemClock()
        self.config = config or IngestionConfig()

        self.state_service = state_service or ConnectorStateService(db, self.clock)
        self.schema_service = schema_service or SchemaDiscoveryService(
            db, self.settings_service, self.state_service, self.clock
        )
        self.sql_service = sql_service

        # Repositories (safe to construct - no I/O)
        self.connector_repo = ConnectorRepository(db)
        self.doc_repo = DocumentRepository(db)

        # Cached orchestrator
        self._orchestrator: IngestionOrchestrator | None = None

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    async def process_connector(self, connector_id: UUID, force: bool = False) -> None:
        """
        Orchestrates full connector ingestion using Factory pattern.
        """
        start_time = asyncio.get_event_loop().time()
        logger.info(f"START | Connector {connector_id} | Force: {force}")

        try:
            await self.settings_service.load_cache()

            connector = await self.connector_repo.get_by_id(connector_id)
            if not connector:
                logger.warning(f"CONNECTOR_NOT_FOUND | {connector_id}")
                return

            # Handle force_sync flag from config
            force = self._resolve_force_flag(connector, force)

            # Set processing status
            await self.state_service.update_connector_status(connector_id, ConnectorStatus.VECTORIZING)

            # Execute factory flow with transaction
            await self._execute_connector_flow(connector, force)

            elapsed_ms = round((asyncio.get_event_loop().time() - start_time) * 1000, 2)
            logger.info(f"SUCCESS | Connector {connector_id} | {elapsed_ms}ms")

        except IngestionStoppedError:
            logger.warning(f"STOPPED | {connector_id}")
            await self._cleanup_on_stop(connector_id)

        except (EntityNotFound, ConfigurationError, FileSystemError) as e:
            # Expected business errors
            logger.warning(f"USER_ERROR | {connector_id} | {e}")
            await self.state_service.mark_connector_failed(connector_id, str(e))

        except (asyncio.TimeoutError, ConnectionError, TransientIngestionError) as e:
            # Transient errors - should retry
            logger.error(f"TRANSIENT_ERROR | {connector_id} | {e}")
            await self.db.rollback()
            await self.state_service.mark_connector_failed(connector_id, f"Temporary error: {e}")
            raise  # Let task queue retry

        except Exception as e:
            # Unexpected errors - alert ops
            logger.critical(
                f"UNEXPECTED_ERROR | {connector_id} | {e}",
                exc_info=True,
                extra={"connector_id": str(connector_id)},
            )
            await self.db.rollback()
            await self.state_service.mark_connector_failed(connector_id, "Internal error - support notified")
            raise

    async def process_single_document(self, document_id: UUID, force: bool = False) -> None:
        """
        Reprocess a single document.
        """
        start_time = asyncio.get_event_loop().time()
        logger.info(f"START | Document {document_id}")

        try:
            await self.settings_service.load_cache()

            doc = await self.doc_repo.get_by_id(document_id)
            if not doc:
                raise EntityNotFound(f"Document {document_id} not found")

            connector = await self.connector_repo.get_by_id(doc.connector_id)
            if not connector:
                raise EntityNotFound(f"Connector {doc.connector_id} not found")

            connector_id = connector.id
            document_id = doc.id

            # Get orchestrator
            orchestrator = await self._get_or_create_orchestrator()

            # SQL SPECIALIZED PATH (includes Vanna SQL)
            if self._is_sql_connector(connector):
                await self.state_service.update_connector_status(connector.id, ConnectorStatus.VECTORIZING)
                try:
                    await self.db.begin_nested()
                    await orchestrator.ingest_sql_view(doc.id, connector)
                    await self.db.commit()
                except Exception:
                    await self.db.rollback()
                    raise

                # Finalize
                await self.state_service.finalize_connector(connector.id)
                # Ensure UI is updated for the document specifically
                await self.state_service.update_document_status(doc.id, DocStatus.INDEXED, "Schema Vectorized")
                elapsed_ms = round((asyncio.get_event_loop().time() - start_time) * 1000, 2)
                logger.info(f"SUCCESS | SQL View {document_id} | {elapsed_ms}ms")
                return

            # Validate file exists
            full_path = get_full_path_from_connector(connector, doc.file_path)
            if not await self._file_exists(full_path):
                await self.state_service.mark_document_failed(document_id, "File not found on disk")
                return

            pipeline, vector_store, batch_size, num_workers, text_splitter, docstore = (
                await orchestrator.setup_pipeline(connector)
            )

            # Update statuses
            await self.state_service.update_connector_status(connector.id, ConnectorStatus.VECTORIZING)
            await self.state_service.update_document_status(doc.id, DocStatus.PROCESSING, "Reprocessing...")

            # AI Discovery (P0)
            if doc.file_path.lower().strip().endswith(".csv"):
                metadata = doc.file_metadata or {}
                if not metadata.get("ai_schema"):
                    logger.info(f"🧠 Discovery | Triggering AI Schema Analysis for {doc.id}")
                    try:
                        await self.schema_service.analyze_and_map_csv(doc.id)
                        # Reload doc to get new metadata
                        doc = await self.doc_repo.get_by_id(doc.id)
                    except Exception as e:
                        logger.warning(f"Discovery Failed: {e}")

            # Ingest with transaction boundary
            connector_acl = connector.configuration.get("connector_acl", [])
            doc_id = doc.id

            try:
                await self.db.begin_nested()  # Savepoint

                if doc.file_path.lower().endswith(".csv"):
                    await orchestrator.ingest_csv_document(doc_id)
                else:
                    await orchestrator.ingest_files(
                        file_paths=[(full_path, doc.file_path)],
                        pipeline=pipeline,
                        vector_store=vector_store,
                        connector_id=connector_id,
                        connector_acl=connector_acl,
                        batch_size=batch_size,
                        num_workers=num_workers,
                        docs_map={doc.file_path: doc},
                        force_reingest=True,
                        text_splitter=text_splitter,
                        docstore=docstore,
                        ignore_connector_status=True,
                        overall_total_files=1,
                    )

                await self.db.commit()

            except Exception as e:
                await self.db.rollback()
                # Cleanup orphaned vectors
                await self.delete_document_vectors(doc_id)
                raise

            # Finalize
            await self.state_service.finalize_connector(connector.id)
            # FORCE EMIT of Indexed status after commit to clear UI progress bars
            await self.state_service.update_document_status(doc_id, DocStatus.INDEXED, "Indexing Complete")
            elapsed_ms = round((asyncio.get_event_loop().time() - start_time) * 1000, 2)
            logger.info(f"SUCCESS | Document {document_id} | {elapsed_ms}ms")

        except (EntityNotFound, FileSystemError) as e:
            logger.warning(f"USER_ERROR | {document_id} | {e}")
            await self.state_service.mark_document_failed(document_id, str(e))

        except Exception as e:
            logger.error(f"FAILURE | Document {document_id} | {e}", exc_info=True)
            await self.db.rollback()
            await self.state_service.mark_document_failed(document_id, str(e))
            if "connector_id" in locals():
                await self.state_service.update_connector_status(connector_id, ConnectorStatus.IDLE)

    async def analyze_and_map_csv(self, doc_id: UUID) -> None:
        """
        Delegates AI-powered CSV schema discovery to SchemaDiscoveryService.
        """
        await self.schema_service.analyze_and_map_csv(doc_id)

    # ========================================================================
    # VECTOR CLEANUP (Delegates to VectorService)
    # ========================================================================

    async def delete_connector_vectors(self, connector_id: UUID) -> None:
        """Delete all vectors for a connector."""
        # Clean delegation with no logic
        await self.vector_service.delete_connector_vectors(str(connector_id))

    async def delete_document_vectors(self, document_id: UUID) -> None:
        """Delete all vectors for a document."""
        await self.vector_service.delete_document_vectors(str(document_id))

    async def update_connector_acl(self, connector_id: UUID, new_acl: str | list[str]) -> None:
        """Update ACLs for all connector vectors."""
        await self.vector_service.update_connector_acl(str(connector_id), new_acl)

    # ========================================================================
    # PRIVATE: ORCHESTRATION
    # ========================================================================

    async def _execute_connector_flow(self, connector, force: bool) -> None:
        """
        Pure orchestration with transaction boundary.
        """
        connector_id = connector.id
        logger.info(f"START | Connector Flow | {connector_id}")

        try:
            # Start transaction
            await self.db.begin_nested()

            # P0 FIX: Detect File Bucket Connectors
            # For local_file connectors used as buckets (no file_path in config),
            # skip Factory and directly vectorize existing documents from DB
            is_file_bucket = connector.connector_type == ConnectorType.LOCAL_FILE and not connector.configuration.get(
                "file_path"
            )
            is_sql = self._is_sql_connector(connector)

            if is_file_bucket or is_sql:
                mode_name = "SQL MODE" if is_sql else "BUCKET MODE"
                logger.info(f"{mode_name} | Skipping Factory, using existing documents from DB")
                # Load existing documents from database
                db_docs = await self.doc_repo.get_by_connector(connector_id, limit=10000)

                if not db_docs:
                    logger.info("NO_CONTENT | No documents in bucket")
                    await self.state_service.finalize_connector(connector_id)
                    return

                logger.info(f"LOADED | {len(db_docs)} documents from database")
            else:
                # Normal flow: Load documents via Factory
                docs = await ConnectorFactory.load_documents(connector)
                logger.info(f"LOADED | {len(docs)} documents")

                if not docs:
                    logger.info("NO_CONTENT | Empty source")
                    await self.state_service.finalize_connector(connector_id)
                    return

                # Upsert to DB
                db_docs = await self.doc_repo.upsert_connector_documents(connector_id, docs)

            # 2.5 AI Schema Discovery (P0: Smart CSV)
            # We must detect schema BEFORE vectorization to ensure "Smart" ingestion.
            for doc in db_docs:
                if doc.file_path.lower().strip().endswith(".csv"):
                    # Check if schema exists in metadata
                    metadata = doc.file_metadata or {}
                    if not metadata.get("ai_schema"):
                        logger.info(f"🧠 Discovery | Triggering AI Schema Analysis for {doc.id}")
                        try:
                            # Serial execution to avoid rate limits on LLM
                            await self.schema_service.analyze_and_map_csv(doc.id)
                            # Refresh doc from DB to get updated metadata (schema)
                            # Optim: In-memory update if analyze returns schema, but re-fetching is safer
                        except Exception as e:
                            logger.warning(f"Discovery Failed for {doc.id}: {e}. Proceeding with default schema.")

            # P0: Reload docs to ensure Orchestrator gets the fresh Schema in metadata
            # (Upsert above returned old objects, Discovery updated them in DB)
            db_docs = await self.doc_repo.get_by_connector(connector_id)

            # 3. Vectorize
            await self._vectorize_documents(connector, db_docs)

            # Commit transaction
            await self.db.commit()

            # 4. Finalize
            await self.state_service.finalize_connector(connector_id)
            logger.info("SUCCESS | Connector Flow Completed")

        except ValueError as e:
            # Config/connector type errors from Factory
            await self.db.rollback()
            logger.error(f"CONFIGURATION_ERROR | {e}")
            await self.state_service.mark_connector_failed(connector_id, str(e))
            raise ConfigurationError(str(e))

        except Exception as e:
            await self.db.rollback()
            # Cleanup orphaned vectors
            await self.vector_service.delete_connector_vectors(str(connector_id))
            logger.error(f"FAILURE | Connector Flow | {e}", exc_info=True)
            await self.state_service.mark_connector_failed(connector_id, str(e))
            raise

    async def _vectorize_documents(self, connector, db_docs: list) -> None:
        """Run vectorization pipeline on loaded documents via Orchestrator."""
        orchestrator = await self._get_or_create_orchestrator()

        # P0: Delegate to Smart Batch Ingestion (handles CSV vs Generic routing)
        await orchestrator.ingest_batch(connector.id, db_docs)

    async def _get_or_create_orchestrator(self) -> IngestionOrchestrator:
        if self._orchestrator is None:
            client = await self.vector_service.get_async_qdrant_client()
            vector_repo = VectorRepository(client)
            self._orchestrator = IngestionOrchestrator(
                self.db,
                vector_repo,
                vector_service=self.vector_service,
                settings_service=self.settings_service,
                sql_discovery_service=self.sql_service,
            )
        return self._orchestrator

    # ========================================================================
    # PRIVATE: HELPERS
    # ========================================================================

    def _resolve_force_flag(self, connector, force: bool) -> bool:
        if connector.configuration and connector.configuration.get("force_sync"):
            return True
        return force

    async def _file_exists(self, path: str) -> bool:
        return await asyncio.to_thread(Path(path).exists)

    async def _cleanup_on_stop(self, connector_id: UUID) -> None:
        try:
            await self.db.rollback()
            connector = await self.connector_repo.get_by_id(connector_id)
            if connector:
                await self.state_service.update_connector_status(connector_id, ConnectorStatus.IDLE)
        except Exception as e:
            logger.warning(f"CLEANUP_FAILED | {connector_id}: {e}")

    def _is_sql_connector(self, connector) -> bool:
        """Centralized check for SQL/Vanna SQL connector types."""
        conn_type = str(connector.connector_type).lower().strip()
        return conn_type in [
            ConnectorType.SQL.value,
            ConnectorType.VANNA_SQL.value,
            "sql",
            "vanna_sql",
        ]


# ============================================================================
# FASTAPI DEPENDENCY INJECTION
# ============================================================================


async def get_ingestion_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    vector_service: Annotated[VectorService, Depends(get_vector_service)],
    settings_service: Annotated[SettingsService, Depends(get_settings_service)],
    state_service: Annotated[ConnectorStateService, Depends(get_connector_state_service)],
    schema_service: Annotated[SchemaDiscoveryService, Depends(get_schema_discovery_service)],
    sql_service: Annotated[SQLDiscoveryService, Depends(get_sql_discovery_service)],
) -> IngestionService:
    """
    Production dependency factory.
    """
    return IngestionService(
        db=db,
        vector_service=vector_service,
        settings_service=settings_service,
        state_service=state_service,
        schema_service=schema_service,
        sql_service=sql_service,
        clock=SystemClock(),
        config=IngestionConfig(),
    )
