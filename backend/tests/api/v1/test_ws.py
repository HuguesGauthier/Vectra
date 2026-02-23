import pytest
import json
from fastapi.testclient import TestClient
from fastapi import status
from app.main import app
from app.core.settings import get_settings


from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def worker_secret():
    return str(get_settings().WORKER_SECRET)


def drain_status(websocket):
    """Drain any WORKER_STATUS messages from the queue."""
    # We might get multiple status updates (initial connect + registration)
    while True:
        try:
            # Use a tiny timeout to check if there's a pending status message
            data = websocket.receive_json()
            if data.get("type") == "WORKER_STATUS":
                continue
            return data  # Return the first non-status message
        except Exception:
            return None


def test_websocket_client_happy_path(client):
    with client.websocket_connect("/api/v1/ws?client_type=client") as websocket:
        # Drain initial worker status message(s)
        websocket.send_text("ping")
        # Heartbeat doesn't send JSON, so drain_status won't work directly here
        # Let's just manually skip WORKER_STATUS
        while True:
            data = websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "WORKER_STATUS":
                    continue
            except:
                pass
            assert data == "pong"
            break


def test_websocket_worker_auth_success(client, worker_secret):
    with client.websocket_connect(
        "/api/v1/ws?client_type=worker", headers={"x-worker-secret": worker_secret}
    ) as websocket:
        websocket.send_text("ping")
        while True:
            data = websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "WORKER_STATUS":
                    continue
            except:
                pass
            assert data == "pong"
            break


def test_websocket_worker_auth_query_param(client, worker_secret):
    with client.websocket_connect(f"/api/v1/ws?client_type=worker&token={worker_secret}") as websocket:
        websocket.send_text("ping")
        while True:
            data = websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "WORKER_STATUS":
                    continue
            except:
                pass
            assert data == "pong"
            break


def test_websocket_worker_auth_failure(client):
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(
            "/api/v1/ws?client_type=worker", headers={"x-worker-secret": "wrong-secret"}
        ) as websocket:
            pass
    assert excinfo.value.code == status.WS_1008_POLICY_VIOLATION


def test_websocket_worker_broadcast(client, worker_secret):
    with client.websocket_connect("/api/v1/ws?client_type=client") as ws_client:
        with client.websocket_connect(
            "/api/v1/ws?client_type=worker", headers={"x-worker-secret": worker_secret}
        ) as ws_worker:
            # Worker broadcasts a message
            msg_to_send = {"type": "TEST_BROADCAST", "data": "hello"}
            ws_worker.send_text(json.dumps(msg_to_send))

            # Client should receive it, possibly after some status updates
            received = None
            for _ in range(5):  # Try a few times
                data = ws_client.receive_json()
                if data.get("type") == "WORKER_STATUS":
                    continue
                received = data
                break

            assert received == msg_to_send


def test_websocket_worker_invalid_json(client, worker_secret):
    with client.websocket_connect(
        "/api/v1/ws?client_type=worker", headers={"x-worker-secret": worker_secret}
    ) as ws_worker:
        # Invalid JSON should not crash the loop
        ws_worker.send_text("not json")
        ws_worker.send_text("ping")

        while True:
            data = ws_worker.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "WORKER_STATUS":
                    continue
            except:
                pass
            assert data == "pong"
            break
