import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from croniter import croniter

# Enforce .env loading for consistent secrets
from dotenv import load_dotenv
from sqlalchemy.future import select

from app.core.database import SessionLocal
from app.models.connector import Connector
from app.models.connector_document import ConnectorDocument
from app.models.enums import ConnectorStatus, DocStatus

# Calculate path to .env in project root (d:\Vectra\.env)
# worker.py is in d:\Vectra\backend\worker.py
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
if os.path.exists(env_path):
    load_dotenv(env_path)
else:
    # Fallback to standard location logic if executed from different context
    pass

# ENFORCE THREADING (Simplified for Cloud Mode)
# No manual overrides for OMP/MKL needed for cloud-only mode
# os.environ["OMP_NUM_THREADS"] = ...

from app.core.websocket import manager  # noqa: E402
from app.core.logging import setup_logging
from app.core.settings import settings
from app.core.time import SystemClock
from app.services.connector_state_service import ConnectorStateService
from app.services.ingestion_service import IngestionService

# Configure logging (use centralized setup)
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Silence noisy libraries (apscheduler not in setup_logging)
logging.getLogger("apscheduler").setLevel(logging.WARNING)

import json
from uuid import UUID

import websockets


async def maintain_socket_connection():
    """Maintains a persistent WebSocket connection to the API."""
    uri = "ws://localhost:8000/api/v1/ws?client_type=worker"
    while True:
        try:
            logger.info(f"Connecting to API at {uri}...")
            logger.info(f"DEBUG: Worker connecting with Secret: '{settings.WORKER_SECRET}'")
            async with websockets.connect(
                uri, ping_timeout=60, additional_headers={"x-worker-secret": settings.WORKER_SECRET}
            ) as websocket:
                logger.info("Connected to API via WebSocket.")

                # Register this connection as upstream for broadcast
                manager.set_upstream(websocket)

                try:
                    # Create tasks for reading and writing (heartbeat)
                    async def heartbeat():
                        while True:
                            try:
                                await websocket.send("ping")
                                logger.debug("Sent heartbeat")
                                await asyncio.sleep(10)  # Send every 10 seconds
                            except Exception:
                                break

                    async def consume():
                        async for message in websocket:
                            if message == "pong":
                                continue
                            try:
                                data = json.loads(message)
                                if data.get("type") == "TRIGGER_DOC_SYNC":
                                    doc_id = data.get("id")
                                    logger.info(f"Received TRIGGER_DOC_SYNC for {doc_id}")
                                    # Launch as task to not block socket loop
                                    asyncio.create_task(process_single_document_wrapper(UUID(doc_id)))
                                if data.get("type") == "TRIGGER_CONNECTOR_SYNC":
                                    conn_id = data.get("id")
                                    logger.info(f"Received TRIGGER_CONNECTOR_SYNC for {conn_id}")
                                    asyncio.create_task(process_connector_wrapper(UUID(conn_id)))
                            except Exception as e:
                                logger.error(f"Error processing message: {e}")

                    # Run both tasks
                    heartbeat_task = asyncio.create_task(heartbeat())
                    consume_task = asyncio.create_task(consume())

                    # Wait for consumer to finish (connection closed) or heartbeat to fail
                    done, pending = await asyncio.wait(
                        [heartbeat_task, consume_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    # Cancel pending task
                    for task in pending:
                        task.cancel()

                finally:
                    manager.set_upstream(None)
                    # Identify which task finished
                    finished_tasks = [t for t in done if not t.cancelled()]
                    for t in finished_tasks:
                        if t == heartbeat_task:
                            logger.warning("WebSocket heartbeat task finished.")
                        elif t == consume_task:
                            logger.warning("WebSocket consume task finished (Connection closed by server).")

                    # Log exceptions if any
                    for t in done:
                        if t.exception():
                            logger.error(f"Task failed with exception: {t.exception()}")

            logger.info("Connection loop iteration finished. Waiting 1s before reconnecting...")
            await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}. Reconnecting in 1s...")
            await asyncio.sleep(1)


# WRAPPERS FOR SERVICE INSTANTIATION
from app.services.settings_service import SettingsService
from app.services.sql_discovery_service import SQLDiscoveryService


async def process_connector_wrapper(connector_id: UUID):
    async with SessionLocal() as db:
        try:
            state_service = ConnectorStateService(db, SystemClock())
            settings_service = SettingsService(db)
            sql_service = SQLDiscoveryService(db, settings_service)

            service = IngestionService(
                db,
                state_service=state_service,
                settings_service=settings_service,
                sql_service=sql_service,
                clock=SystemClock(),
            )
            await service.process_connector(connector_id)
        except Exception as e:
            logger.error(f"Wrapper failed for connector {connector_id}: {e}")


async def process_single_document_wrapper(doc_id: UUID):
    async with SessionLocal() as db:
        try:
            state_service = ConnectorStateService(db, SystemClock())
            settings_service = SettingsService(db)
            sql_service = SQLDiscoveryService(db, settings_service)

            service = IngestionService(
                db,
                state_service=state_service,
                settings_service=settings_service,
                sql_service=sql_service,
                clock=SystemClock(),
            )
            await service.process_single_document(doc_id, force=True)
        except Exception as e:
            logger.error(f"Wrapper failed for doc {doc_id}: {e}")


async def check_triggers():
    """
    Periodic task to check for manual or scheduled triggers.
    """
    logger.debug("Checking for triggers...")
    try:
        async with SessionLocal() as db:
            # 1. Scheduled Triggers
            result = await db.execute(
                select(Connector).where(
                    (Connector.is_enabled == True)
                    & (
                        (Connector.status == ConnectorStatus.STARTING)
                        | (Connector.status == ConnectorStatus.QUEUED)
                        | (
                            (Connector.status == ConnectorStatus.IDLE)
                            & (Connector.schedule_cron.isnot(None))
                            & (Connector.schedule_cron != "")
                        )
                    )
                )
            )
            candidates = result.scalars().all()

            now = datetime.now(timezone.utc)
            for connector in candidates:
                try:
                    should_run = False

                    if connector.status == ConnectorStatus.STARTING:
                        should_run = True
                        logger.info(f"Detected manual/starting trigger for {connector.name}")

                    elif connector.status == ConnectorStatus.QUEUED:
                        should_run = True
                        logger.info(f"Picking up QUEUED job for {connector.name}")

                    elif connector.status == ConnectorStatus.IDLE and connector.schedule_cron:
                        if croniter.match(connector.schedule_cron, now):
                            # Dedup logic
                            if connector.last_vectorized_at:
                                time_since = (now - connector.last_vectorized_at).total_seconds()
                                if time_since < 60:
                                    continue
                            should_run = True
                            logger.info(f"Triggering scheduled scan for {connector.name}")

                    if should_run:
                        connector_id = connector.id
                        connector.status = ConnectorStatus.SYNCING
                        db.add(connector)
                        await db.commit()
                        asyncio.create_task(process_connector_wrapper(connector_id))

                except Exception as e:
                    logger.error(f"Error checking schedule for {connector.name}: {e}")

            # 2. Pending Documents (Single Sync Fallback / Catch-up)
            # Even with WebSocket triggers, we keep this as a fallback for missed events
            result_docs = await db.execute(
                select(ConnectorDocument)
                .where(ConnectorDocument.status == DocStatus.PENDING)
                .order_by(ConnectorDocument.updated_at.asc())
                .limit(10)
            )

            pending_docs = result_docs.scalars().all()

            for doc in pending_docs:
                doc_id = doc.id
                logger.info(f"Worker picked up pending document {doc_id} (Fallback polling)")
                doc.status = DocStatus.PROCESSING
                db.add(doc)
                await db.commit()

                # EMIT STATUS UPDATE (Crucial for UI)
                # We use a temporary simple emit here, but the service will handle the rest
                try:
                    await manager.emit_document_update(
                        str(doc_id), DocStatus.PROCESSING, "Processing started on worker."
                    )
                except Exception as e:
                    logger.warning(f"Failed to emit status update: {e}")

                asyncio.create_task(process_single_document_wrapper(doc_id))

    except Exception as e:
        logger.error(f"Error in Trigger Checker: {e}")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    scheduler = AsyncIOScheduler(event_loop=loop)

    # 1 Minute Scheduler (Cron + Fallback)
    scheduler.add_job(
        check_triggers,
        trigger=IntervalTrigger(seconds=10),
        id="trigger_checker",
        name="Check DB for pending jobs",
        replace_existing=True,
    )

    # Broadcast System Metrics - MOVED TO API SERVER
    # See app/api/v1/endpoints/dashboard.py for new implementation
    from app.workers.scheduler_service import scheduler_service

    # Cleanup Old Logs (Sunday at 3 AM)
    scheduler.add_job(
        scheduler_service.cleanup_old_logs,
        "cron",
        day_of_week="sun",
        hour=3,
        id="log_cleanup",
        replace_existing=True,
    )

    # Start WebSocket Task
    loop.create_task(maintain_socket_connection())

    # Initialize Settings Cache
    async def startup():
        async with SessionLocal() as db:
            from app.services.settings_service import SettingsService

            settings_service = SettingsService(db)
            await settings_service.load_cache()
            logger.info("Settings cache loaded in worker.")
            logger.info(f"DEBUG: Worker started with Secret: '{settings.WORKER_SECRET}'")

            # Initialize Phoenix for Worker Traceability (Deep Tracing)
            if settings.ENABLE_PHOENIX_TRACING:
                try:
                    import phoenix as px
                    from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
                    from opentelemetry import trace as trace_api
                    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                    from opentelemetry.sdk.trace import TracerProvider
                    from opentelemetry.sdk.trace.export import SimpleSpanProcessor

                    # Configure OpenTelemetry to export to Phoenix Docker Container
                    endpoint = "http://localhost:6006/v1/traces"

                    # DEBUG: Enable OTel internal logging
                    import sys

                    from opentelemetry.sdk.resources import Resource

                    tracer_provider = TracerProvider(resource=Resource.create({"service.name": "vectra-worker"}))
                    span_exporter = OTLPSpanExporter(endpoint=endpoint)

                    # Use BatchSpanProcessor for production, but Simple for debug
                    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
                    trace_api.set_tracer_provider(tracer_provider)

                    # Initialize Automatic Instrumentation
                    LlamaIndexInstrumentor().instrument()

                    logger.info(f"🦜 Worker OpenInference Instrumentation active (to {endpoint})")

                except ImportError as e:
                    logger.warning(f"⚠️ Phoenix enabled but dependencies missing in worker: {e}")
                except Exception as e:
                    logger.error(f"⚠️ Failed to launch Phoenix in worker: {e}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to init Phoenix in worker: {e}")

    loop.run_until_complete(startup())

    logger.info("Starting APScheduler...")
    scheduler.start()

    try:
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
