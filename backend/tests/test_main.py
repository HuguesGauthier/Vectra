import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, PropertyMock
import sys

# Mock dependencies globally for test collection
sys.modules["pyodbc"] = MagicMock()
sys.modules["vanna"] = MagicMock()
sys.modules["vanna.base"] = MagicMock()

from app.main import app

client = TestClient(app)


def test_read_main():
    """Happy Path: Root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}


def test_health_check():
    """Happy Path: Health check."""
    with patch("app.main.manager") as mock_manager:
        mock_manager.is_worker_online = True
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"api": "online", "worker": "online", "storage": "online"}


def test_exception_handler_vectra_exception():
    """Worst Case: Custom exception handling."""
    from app.core.exceptions import FunctionalError

    @app.get("/trigger-error")
    async def trigger_error():
        raise FunctionalError("Test Error", error_code="TEST_CODE")

    response = client.get("/trigger-error")
    assert response.status_code == 400
    assert response.json()["code"] == "TEST_CODE"
    assert response.json()["message"] == "Test Error"


def test_exception_handler_unhandled():
    """Worst Case: Unhandled internal error."""
    # Using VectraException with a high status code to simulate a 500
    # and ensure our mapping logic is triggered without crashing the test runner.
    from app.core.exceptions import TechnicalError

    with patch("app.main.manager.__class__.is_worker_online", new_callable=PropertyMock) as mock_prop:
        mock_prop.side_effect = TechnicalError("Mocked Internal Error", status_code=500)
        response = client.get("/health")
        assert response.status_code == 500
        data = response.json()
        assert data["code"] == "TECHNICAL_ERROR" or data["code"] == "technical_error"
        assert "id" in data
