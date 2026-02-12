"""
Main Application Entrypoint - Configures FastAPI, Middleware, and Lifecycle.
"""

import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Union
from uuid import UUID, uuid4

from dotenv import load_dotenv

# P0 FIX: Force reload of .env file on hot-reload (e.g. key added)
load_dotenv(override=True)

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from alembic import command
from alembic.config import Config
from app.api.v1.router import router as api_router
from app.api.v1.ws import router as ws_router
from app.core.websocket import get_websocket
from app.core.database import SessionLocal
from app.core.exceptions import VectraException
from app.core.init_db import init_db
from app.core.logging import generate_request_id, set_correlation_id, setup_logging
from app.core.settings import settings
from app.models.error_log import ErrorLog
from app.services.settings_service import SettingsService
from app.workers.scheduler_service import scheduler_service

# Configure logging
setup_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


def run_migrations() -> None:
    """
    Run Alembic migrations synchronously (to be threaded).

    This function initializes the Alembic configuration and upgrades the
    database to the latest version ('head').
    """
    logger.info("Running database migrations...")
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    logger.info("Migrations completed successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application Lifespan Event Handler.

    Handles startup configuration and graceful shutdown, including database
    migrations, initialization, settings caching, and starting background services.

    Args:
        app: The FastAPI application instance.
    """
    # [STARTUP]
    try:
        logger.info("🚀 Starting Vectra API...")

        # 1. Database Migrations (Non-blocking)
        # P1: Fail fast if migrations fail
        await asyncio.to_thread(run_migrations)

        # 2. Database Initialization (Seed Admin)
        # P1: Fail fast if init fails
        await init_db()

        # 3. Load Settings Cache
        async with SessionLocal() as db:
            settings_service = SettingsService(db)
            await settings_service.load_cache()

        # 4. Observability: Initialize Arize Phoenix (if enabled)
        if settings.ENABLE_PHOENIX_TRACING:
            try:
                from openinference.instrumentation.llama_index import LlamaIndexInstrumentor
                from opentelemetry import trace as trace_api
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import SimpleSpanProcessor

                logger.info("🕊️ Launching Arize Phoenix (via OpenInference)...")
                endpoint = "http://localhost:6006/v1/traces"

                tracer_provider = TracerProvider()
                span_exporter = OTLPSpanExporter(endpoint=endpoint)
                tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
                trace_api.set_tracer_provider(tracer_provider)

                LlamaIndexInstrumentor().instrument()
                logger.info(f"🦜 OpenInference Instrumentation active. Exporting to {endpoint}")

            except ImportError:
                logger.warning("⚠️ Phoenix enabled but dependencies missing.")
            except Exception as e:
                logger.error(f"⚠️ Failed to launch Phoenix: {e}")

        # 5. Start Scheduler Service
        scheduler_service.start()

        # 6. Start Broadcast Tasks
        from app.api.v1.endpoints.dashboard import start_broadcast_task as start_dashboard_broadcast
        from app.api.v1.endpoints.analytics import start_broadcast_task as start_analytics_broadcast

        await start_dashboard_broadcast(interval_seconds=5)
        await start_analytics_broadcast(interval_seconds=10)

        logger.info("✅ Startup sequence complete.")

    except Exception as e:
        logger.critical(f"🛑 CRITICAL STARTUP FAILURE: {e}", exc_info=True)
        # P1: Fail Fast - prevent app from starting in broken state
        raise SystemExit(1) from e

    yield

    # [SHUTDOWN]
    logger.info("🛑 Shutting down application...")
    scheduler_service.shutdown()
    logger.info("Goodbye.")


app = FastAPI(title="Vectra API", lifespan=lifespan)


# --- Middleware Configuration ---


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next: Callable[[Request], Any]) -> Response:
    """
    Adds Correlation ID to all requests for tracing.

    Args:
        request: The incoming HTTP request.
        call_next: The next middleware or endpoint in the chain.

    Returns:
        The HTTP response with a Correlation ID header.
    """
    correlation_id = request.headers.get("X-Correlation-ID") or generate_request_id()
    set_correlation_id(correlation_id)
    response: Response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


# Configure CORS
# Use settings if available, else fallback to safe defaults plus localhost for dev
env_origins: Union[str, List[str]] = getattr(settings, "BACKEND_CORS_ORIGINS", [])
if isinstance(env_origins, str):
    env_origins = [o.strip() for o in env_origins.split(",") if o]

default_dev_origins: List[str] = [
    "http://localhost:9000",
    "http://127.0.0.1:9000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:9300",
    "http://127.0.0.1:9300",
]

origins: List[str] = list(set(list(env_origins) + default_dev_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# --- Exception Handlers ---


@app.exception_handler(Exception)
@app.exception_handler(VectraException)
@app.exception_handler(StarletteHTTPException)
@app.exception_handler(RequestValidationError)
async def global_exception_handler(
    request: Request,
    exc: Union[Exception, VectraException, StarletteHTTPException, RequestValidationError],
) -> JSONResponse:
    """
    Global exception handling with DB logging and strict response structure.

    This handler catches various exception types and returns a unified JSON
    response. In production, it logs technical errors to the database.
    In debug mode, it provides detailed tracebacks in the response.

    Args:
        request: The incoming HTTP request.
        exc: The raised exception.

    Returns:
        A JSON response containing error details.
    """
    error_id: UUID = uuid4()

    # Defaults
    error_code: str = "INTERNAL_SERVER_ERROR"
    status_code: int = 500
    message: str = "Internal Server Error"
    error_type: str = "TECHNICAL"
    details: Dict[str, Any] = {}

    # Map Known Exceptions
    if isinstance(exc, VectraException):
        error_code = exc.error_code
        status_code = exc.status_code
        message = exc.message
        error_type = exc.type
        details = exc.details
    elif isinstance(exc, (StarletteHTTPException, RequestValidationError)):
        status_code = getattr(exc, "status_code", 422)
        message = str(getattr(exc, "detail", str(exc)))
        error_code = f"HTTP_{status_code}"
        error_type = "FUNCTIONAL" if status_code < 500 else "TECHNICAL"

    # Log to Console
    if settings.DEBUG and status_code >= 500:
        logger.critical("\n" + "=" * 80)
        logger.critical(f"🔴 EXCEPTION CAUGHT: {type(exc).__name__}")
        logger.critical("=" * 80)
        logger.critical(traceback.format_exc())
        logger.critical("=" * 80 + "\n")
    else:
        logger.error(
            f"❌ FAIL | ID: {error_id} | Code: {error_code} | "
            f"Method: {request.method} | Path: {request.url.path} | "
            f"Error: {message}",
            exc_info=True if status_code >= 500 else False,
        )

    # Log to DB (Best Effort) - Production Only
    if settings.ENV == "production" and status_code >= 500:
        # P1: Avoid recursion if DB logging itself fails
        if not getattr(request.state, "exception_logged_to_db", False):
            try:
                request.state.exception_logged_to_db = True
                async with SessionLocal() as db:
                    error_log = ErrorLog(
                        id=error_id,
                        status_code=status_code,
                        method=request.method,
                        path=str(request.url.path),
                        error_message=str(exc),
                        stack_trace=traceback.format_exc(),
                    )
                    db.add(error_log)
                    await db.commit()
            except Exception as db_exc:
                logger.critical(f"CRITICAL: Failed to write ErrorLog to DB: {db_exc}")

    # Construct Response
    content: Dict[str, Any] = {
        "id": str(error_id),
        "code": error_code,
        "message": message,
        "type": error_type,
    }

    # Only expose trace in DEBUG mode for 500 errors
    if settings.DEBUG:
        if status_code >= 500:
            content["debug_trace"] = traceback.format_exc()
            content["type"] = type(exc).__name__
            content["request_path"] = str(request.url)
        content["details"] = details

    return JSONResponse(status_code=status_code, content=content)


# --- Routers ---
app.include_router(api_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")


@app.get("/")
async def root() -> Dict[str, str]:
    """
    Root endpoint returning API status and version.

    Returns:
        A dictionary with status and version.
    """
    return {"status": "ok", "version": "1.0.0"}


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """
    Checks the health of the API and the background worker.

    Returns:
        A dictionary with API and worker status.
    """
    worker_status = "online" if manager.is_worker_online else "offline"
    return {"api": "online", "worker": worker_status}
