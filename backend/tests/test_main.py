"""
Unit tests for main.py (Lifecycle & Exception Handling).
"""

import json
import sys
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import VectraException
from app.main import app, lifespan, run_migrations


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_startup_sequence():
    """\u2705 SUCCESS: Startup sequence runs migrations, seeds DB, and starts scheduler."""
    with (
        patch("app.main.run_migrations") as mock_mig,
        patch("app.main.init_db", new_callable=AsyncMock) as mock_init,
        patch("app.main.SettingsService") as mock_settings,
        patch("app.main.scheduler_service") as mock_scheduler,
        patch("app.main.SessionLocal") as mock_session_lib,
        patch("app.api.v1.endpoints.dashboard.start_broadcast_task", new_callable=AsyncMock) as mock_db_broadcast,
        patch("app.api.v1.endpoints.analytics.start_broadcast_task", new_callable=AsyncMock) as mock_an_broadcast,
    ):
        # Mock DB Context
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_session_lib.return_value.__aenter__.return_value = mock_db

        mock_service_inst = AsyncMock()
        mock_settings.return_value = mock_service_inst

        # Execute Lifespan
        async with lifespan(app):
            pass

        # Verify
        mock_mig.assert_called_once()
        mock_init.assert_awaited_once()
        mock_service_inst.load_cache.assert_awaited_once()
        mock_scheduler.start.assert_called_once()
        mock_db_broadcast.assert_awaited_once()
        mock_an_broadcast.assert_awaited_once()
        mock_scheduler.shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_startup_sequence_with_phoenix():
    """\u2705 SUCCESS: Startup sequence with Phoenix enabled."""
    mock_instrumentor = MagicMock()
    
    # Mock all necessary modules
    modules = {
        "openinference.instrumentation.llama_index": MagicMock(),
        "opentelemetry": MagicMock(),
        "opentelemetry.exporter.otlp.proto.http.trace_exporter": MagicMock(),
        "opentelemetry.sdk.trace": MagicMock(),
        "opentelemetry.sdk.trace.export": MagicMock(),
    }
    
    with (
        patch.dict(sys.modules, modules),
        patch("app.main.run_migrations"),
        patch("app.main.init_db", new_callable=AsyncMock),
        patch("app.main.SettingsService") as mock_settings,
        patch("app.main.scheduler_service"),
        patch("app.main.SessionLocal") as mock_session_lib,
        patch("app.api.v1.endpoints.dashboard.start_broadcast_task", new_callable=AsyncMock),
        patch("app.api.v1.endpoints.analytics.start_broadcast_task", new_callable=AsyncMock),
        patch("app.main.settings") as mock_settings_val,
    ):
        mock_settings_val.ENABLE_PHOENIX_TRACING = True
        mock_settings_val.LOG_LEVEL = "INFO"
        
        # Configure mock instrumentor
        modules["openinference.instrumentation.llama_index"].LlamaIndexInstrumentor.return_value = mock_instrumentor
        
        # Mock DB Context
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_session_lib.return_value.__aenter__.return_value = mock_db

        mock_service_inst = AsyncMock()
        mock_settings.return_value = mock_service_inst

        # Execute Lifespan
        async with lifespan(app):
            pass
            
        mock_instrumentor.instrument.assert_called_once()


@pytest.mark.asyncio
async def test_startup_sequence_phoenix_import_error():
    """\u2705 SUCCESS: Startup sequence handles Phoenix import error."""
    # We want to ensure that if 'openinference' fails to import, it logs a warning
    with (
        patch("app.main.run_migrations"),
        patch("app.main.init_db", new_callable=AsyncMock),
        patch("app.main.SettingsService") as mock_settings,
        patch("app.main.scheduler_service"),
        patch("app.main.SessionLocal") as mock_session_lib,
        patch("app.api.v1.endpoints.dashboard.start_broadcast_task", new_callable=AsyncMock),
        patch("app.api.v1.endpoints.analytics.start_broadcast_task", new_callable=AsyncMock),
        patch("app.main.settings") as mock_settings_val,
        patch("app.main.logger") as mock_logger,
        patch("builtins.__import__", side_effect=ImportError),
    ):
        mock_settings_val.ENABLE_PHOENIX_TRACING = True
        
        # Mock DB Context
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_session_lib.return_value.__aenter__.return_value = mock_db

        mock_service_inst = AsyncMock()
        mock_settings.return_value = mock_service_inst

        async with lifespan(app):
            pass
        
        mock_logger.warning.assert_called()


@pytest.mark.asyncio
async def test_startup_sequence_exception():
    """\u2705 SUCCESS: Startup sequence handles exceptions gracefully."""
    with (
        patch("app.main.run_migrations", side_effect=Exception("Migration failed")),
        patch("app.main.logger") as mock_logger,
    ):
        # Execute Lifespan
        async with lifespan(app):
            pass
        
        mock_logger.error.assert_called()


def test_run_migrations():
    """\u2705 SUCCESS: run_migrations calls alembic commands."""
    with (
        patch("app.main.Config") as mock_config,
        patch("app.main.command.upgrade") as mock_upgrade,
    ):
        run_migrations()
        mock_config.assert_called_once_with("alembic.ini")
        mock_upgrade.assert_called_once()


def test_health_check_nominal(client):
    """\u2705 SUCCESS: Health check returns online."""
    with patch("app.main.manager") as mock_manager:
        mock_manager.is_worker_online = True
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"api": "online", "worker": "online"}


def test_health_check_worker_offline(client):
    """\u2705 SUCCESS: Health check returns worker offline."""
    with patch("app.main.manager") as mock_manager:
        mock_manager.is_worker_online = False
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"api": "online", "worker": "offline"}


def test_root_endpoint(client):
    """\u2705 SUCCESS: Root endpoint returns 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}


def test_correlation_id_middleware(client):
    """\u2705 SUCCESS: Correlation ID middleware adds header."""
    response = client.get("/", headers={"X-Correlation-ID": "test-id"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "test-id"

    response = client.get("/")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers


@pytest.mark.asyncio
async def test_global_exception_handler_vectra_exception():
    """\u2705 SUCCESS: Handles VectraException."""
    from app.main import global_exception_handler
    
    exc = VectraException(message="Test error", status_code=400, error_code="TEST_CODE")
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = "/test"
    
    with patch("app.main.settings") as mock_settings:
        mock_settings.DEBUG = False
        mock_settings.ENV = "production"
        
        response = await global_exception_handler(request, exc)
        assert response.status_code == 400
        data = json.loads(response.body)
        assert data["code"] == "TEST_CODE"
        assert data["message"] == "Test error"


@pytest.mark.asyncio
async def test_global_exception_handler_http_exception():
    """\u2705 SUCCESS: Handles StarletteHTTPException."""
    from app.main import global_exception_handler
    
    exc = StarletteHTTPException(status_code=404, detail="Not Found")
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = "/test"
    
    response = await global_exception_handler(request, exc)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_global_exception_handler_request_validation_error():
    """\u2705 SUCCESS: Handles RequestValidationError."""
    from app.main import global_exception_handler
    
    exc = RequestValidationError(errors=[])
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.url.path = "/test"
    
    response = await global_exception_handler(request, exc)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_global_exception_handler_generic_exception_debug():
    """\u2705 SUCCESS: Handles generic Exception in DEBUG mode."""
    from app.main import global_exception_handler
    
    exc = Exception("Unexpected error")
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.url.path = "/error"
    request.url = MagicMock()
    request.url.__str__.return_value = "http://testserver/error"
    
    with patch("app.main.settings") as mock_settings:
        mock_settings.DEBUG = True
        
        response = await global_exception_handler(request, exc)
        assert response.status_code == 500
        data = json.loads(response.body)
        assert "debug_trace" in data


@pytest.mark.asyncio
async def test_global_exception_handler_production_log_db():
    """\u2705 SUCCESS: Logs to DB in production for 500 errors."""
    from app.main import global_exception_handler
    
    exc = Exception("Critical failure")
    request = MagicMock(spec=Request)
    request.method = "PUT"
    request.url.path = "/prod-error"
    
    with (
        patch("app.main.settings") as mock_settings,
        patch("app.main.SessionLocal") as mock_session_lib,
        patch("app.main.ErrorLog") as mock_error_log_model,
    ):
        mock_settings.ENV = "production"
        mock_settings.DEBUG = False
        
        mock_db = MagicMock()
        mock_db.commit = AsyncMock()
        mock_session_lib.return_value.__aenter__.return_value = mock_db
        
        response = await global_exception_handler(request, exc)
        assert response.status_code == 500
        
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_global_exception_handler_db_failure():
    """\u2705 SUCCESS: Handles DB failure during error logging gracefully."""
    from app.main import global_exception_handler
    
    exc = Exception("Critical failure")
    request = MagicMock(spec=Request)
    request.method = "PUT"
    request.url.path = "/prod-error"
    
    with (
        patch("app.main.settings") as mock_settings,
        patch("app.main.SessionLocal") as mock_session_lib,
        patch("app.main.logger") as mock_logger,
    ):
        mock_settings.ENV = "production"
        mock_settings.DEBUG = False
        
        mock_db = MagicMock()
        mock_db.commit = AsyncMock(side_effect=Exception("DB Down"))
        mock_session_lib.return_value.__aenter__.return_value = mock_db
        
        response = await global_exception_handler(request, exc)
        assert response.status_code == 500
        mock_logger.critical.assert_called_with(ANY)
