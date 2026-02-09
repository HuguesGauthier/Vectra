import json

import pytest
from fastapi.testclient import TestClient

from app.core.connection_manager import manager
from app.core.settings import settings
from app.main import app


@pytest.fixture(autouse=True)
def reset_manager():
    """Reset the singleton manager before each test."""
    manager._worker_connection = None
    manager.active_connections = set()
    manager.active_listeners = set()
    manager.upstream_connection = None


def test_worker_ws_nominal():
    client = TestClient(app)
    with client.websocket_connect(
        f"/api/v1/ws?client_type=worker", headers={"x-worker-secret": settings.WORKER_SECRET}
    ) as websocket:
        # 1. Server sends WORKER_STATUS: offline (before registration) ... wait, current is False
        # and then offline after connecting but before register?
        # Actually manager.connect sends current status.
        msg1 = websocket.receive_json()
        assert msg1["type"] == "WORKER_STATUS"

        # 2. After registration, it sends WORKER_STATUS: online
        msg2 = websocket.receive_json()
        assert msg2["type"] == "WORKER_STATUS"
        assert msg2["status"] == "online"

        # Just connecting should work
        assert manager.is_worker_online

        # Test heartbeat
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert data == "pong"


def test_worker_ws_unauthorized():
    client = TestClient(app)
    with pytest.raises(Exception):  # FastAPI TestClient raises for non-101
        with client.websocket_connect(
            f"/api/v1/ws?client_type=worker", headers={"x-worker-secret": "wrong-secret"}
        ) as websocket:
            pass


def test_worker_ws_conflict():
    client = TestClient(app)
    # Connect first worker
    with client.websocket_connect(
        f"/api/v1/ws?client_type=worker", headers={"x-worker-secret": settings.WORKER_SECRET}
    ) as ws1:
        # 1. ws1 registration
        ws1.receive_json()  # status: offline
        ws1.receive_json()  # status: online

        assert manager.is_worker_online
        first_worker_ws = manager._worker_connection

        # 2. Connect second worker (ws2)
        with client.websocket_connect(
            f"/api/v1/ws?client_type=worker", headers={"x-worker-secret": settings.WORKER_SECRET}
        ) as ws2:
            # ws2 sees current status then new status after registration
            ws2.receive_json()  # status: online
            ws2.receive_json()  # status: online (new register)

            assert manager.is_worker_online
            # Manager should have replaced the worker
            assert manager._worker_connection != first_worker_ws

            # The first worker (ws1) might receive the status update from ws2's registration
            # before it gets the close signal.
            msg = ws1.receive_json()
            assert msg["type"] == "WORKER_STATUS"

            # Now ws1 should be closed or next operation should fail
            with pytest.raises(Exception):
                # Small timeout/wait might be needed but TestClient is synchronous-looking
                ws1.receive_text()
