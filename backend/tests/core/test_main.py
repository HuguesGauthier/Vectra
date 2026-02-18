"""
Unit tests for main.py (Lifecycle & Exception Handling).
"""

import json
import sys
import traceback
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
    """✅ SUCCESS: Startup sequence runs migrations, seeds DB, and starts scheduler."""
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
async def test_startup_sequence_exception():
    """✅ SUCCESS: Startup sequence handles exceptions gracefully."""
    with (
        patch("app.main.run_migrations", side_effect=Exception("Migration failed")),
        patch("app.main.logger") as mock_logger,
    ):
        # Execute Lifespan
        with pytest.raises(SystemExit):
            async with lifespan(app):
                pass
        
        # In lifespan, it calls logger.critical on line 122
        mock_logger.critical.assert_called()


def test_run_migrations():
    """✅ SUCCESS: run_migrations calls alembic commands."""
    with (
        patch("app.main.Config") as mock_config,
        patch("app.main.command.upgrade") as mock_upgrade,
    ):
        run_migrations()
        mock_config.assert_called_once_with("alembic.ini")
        mock_upgrade.assert_called_once()


def test_health_check_nominal(client):
    """✅ SUCCESS: Health check returns online."""
    with patch("app.main.manager") as mock_manager:
        mock_manager.is_worker_online = True
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"api": "online", "worker": "online", "storage": "online"}


def test_health_check_worker_offline(client):
    """✅ SUCCESS: Health check returns worker offline."""
    with patch("app.main.manager") as mock_manager:
        mock_manager.is_worker_online = False
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"api": "online", "worker": "offline", "storage": "online"}


def test_root_endpoint(client):
    """✅ SUCCESS: Root endpoint returns 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}


def test_correlation_id_middleware(client):
    """✅ SUCCESS: Correlation ID middleware adds header."""
    response = client.get("/", headers={"X-Correlation-ID": "test-id"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "test-id"

    response = client.get("/")
    assert response.status_code == 200
    assert "X-Correlation-ID" in response.headers


@pytest.mark.asyncio
async def test_global_exception_handler_vectra_exception():
    """✅ SUCCESS: Handles VectraException."""
    from app.main import global_exception_handler
    
    exc = VectraException(message="Test error", status_code=400, error_code="TEST_CODE")
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = "/test"
    # Properly mock state
    request.state = MagicMock()
    
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
    """✅ SUCCESS: Handles StarletteHTTPException."""
    from app.main import global_exception_handler
    
    exc = StarletteHTTPException(status_code=404, detail="Not Found")
    request = MagicMock(spec=Request)
    request.method = "GET"
    request.url.path = "/test"
    request.state = MagicMock()
    
    response = await global_exception_handler(request, exc)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_global_exception_handler_request_validation_error():
    """✅ SUCCESS: Handles RequestValidationError."""
    from app.main import global_exception_handler
    
    exc = RequestValidationError(errors=[])
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.url.path = "/test"
    request.state = MagicMock()
    
    response = await global_exception_handler(request, exc)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_global_exception_handler_generic_exception_debug():
    """✅ SUCCESS: Handles generic Exception in DEBUG mode."""
    from app.main import global_exception_handler
    
    exc = Exception("Unexpected error")
    request = MagicMock(spec=Request)
    request.method = "POST"
    request.url.path = "/error"
    request.url = MagicMock()
    request.url.__str__.return_value = "http://testserver/error"
    request.state = MagicMock()
    
    with patch("app.main.settings") as mock_settings:
        mock_settings.DEBUG = True
        
        response = await global_exception_handler(request, exc)
        assert response.status_code == 500
        data = json.loads(response.body)
        assert "debug_trace" in data


@pytest.mark.asyncio
async def test_global_exception_handler_production_log_db():
    """✅ SUCCESS: Logs to DB in production for 500 errors."""
    from app.main import global_exception_handler
    
    exc = Exception("Critical failure")
    request = MagicMock(spec=Request)
    request.method = "PUT"
    request.url.path = "/prod-error"
    # Ensure state check passes
    request.state = MagicMock()
    del request.state.exception_logged_to_db # Force getattr to use default False
    
    with (
        patch("app.main.settings") as mock_settings,
        patch("app.main.SessionLocal") as mock_session_lib,
        patch("app.main.ErrorLog") as mock_error_log_model,
        patch("app.main.logger") as mock_logger,
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
    """✅ SUCCESS: Handles DB failure during error logging gracefully."""
    from app.main import global_exception_handler
    
    exc = Exception("Critical failure")
    request = MagicMock(spec=Request)
    request.method = "PUT"
    request.url.path = "/prod-error"
    request.state = MagicMock()
    del request.state.exception_logged_to_db
    
    with (
        patch("app.main.settings") as mock_settings,
        patch("app.main.SessionLocal") as mock_session_lib,
        patch("app.main.logger") as mock_logger,
        patch("app.main.ErrorLog"),
    ):
        mock_settings.ENV = "production"
        mock_settings.DEBUG = False
        
        mock_db = MagicMock()
        mock_db.commit = AsyncMock(side_effect=Exception("DB Down"))
        mock_session_lib.return_value.__aenter__.return_value = mock_db
        
        response = await global_exception_handler(request, exc)
        assert response.status_code == 500
        mock_logger.critical.assert_called()
