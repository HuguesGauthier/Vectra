from unittest.mock import AsyncMock, MagicMock
import json
import pytest
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient

from app.api.v1.ws import router
from app.core.websocket import Websocket, get_websocket
from app.core.settings import settings

# Mock Manager
mock_manager = MagicMock(spec=Websocket)


async def mock_connect(websocket):
    await websocket.accept()
    # Simulate the emit_worker_status(True/False) that real manager does
    await websocket.send_json({"type": "WORKER_STATUS", "status": "online"})


async def mock_register_worker(websocket):
    # Simulate emit_worker_status(True)
    await websocket.send_json({"type": "WORKER_STATUS", "status": "online"})


mock_manager.connect = AsyncMock(side_effect=mock_connect)
mock_manager.disconnect = AsyncMock()
mock_manager.broadcast = AsyncMock()
mock_manager.register_worker = AsyncMock(side_effect=mock_register_worker)
mock_manager.emit_worker_status = AsyncMock()
type(mock_manager).is_worker_online = True

# Setup isolated app for WS testing
app = FastAPI()
app.include_router(router)


async def override_get_manager():
    return mock_manager


app.dependency_overrides[get_websocket] = lambda: mock_manager

client = TestClient(app)


class TestWebSocket:

    def setup_method(self):
        mock_manager.connect.side_effect = mock_connect
        mock_manager.register_worker.side_effect = mock_register_worker
        mock_manager.broadcast.reset_mock()
        mock_manager.emit_worker_status.reset_mock()

    def test_client_connection(self):
        """Test standard client connection works."""
        with client.websocket_connect("/ws?client_type=client") as websocket:
            # mock_connect sends json
            data = websocket.receive_json()
            assert data == {"type": "WORKER_STATUS", "status": "online"}

            websocket.send_text("ping")
            data = websocket.receive_text()
            assert data == "pong"

    def test_worker_connection_authorized_header(self):
        """Test worker connection accepted with correct header."""
        secret = settings.WORKER_SECRET
        with client.websocket_connect("/ws?client_type=worker", headers={"x-worker-secret": secret}) as websocket:
            # 1. connect msg
            websocket.receive_json()
            # 2. register msg
            websocket.receive_json()

            websocket.send_text("ping")
            data = websocket.receive_text()
            assert data == "pong"

    def test_worker_connection_authorized_query(self):
        """Test worker connection accepted with correct query param token (fallback)."""
        secret = settings.WORKER_SECRET
        with client.websocket_connect(f"/ws?client_type=worker&token={secret}") as websocket:
            # 1. connect msg
            websocket.receive_json()
            # 2. register msg
            websocket.receive_json()

            websocket.send_text("ping")
            data = websocket.receive_text()
            assert data == "pong"

    def test_worker_connection_unauthorized(self):
        """Test worker connection REJECTED without secret."""
        # Note: TestClient raising WebSocketDisconnect on close code 1008
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/ws?client_type=worker") as websocket:
                websocket.send_text("ping")

        # 1008 Policy Violation
        assert exc.value.code == 1008

    def test_worker_connection_wrong_secret(self):
        """Test worker connection REJECTED with WRONG secret."""
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect("/ws?client_type=worker", headers={"x-worker-secret": "wrong"}) as websocket:
                websocket.send_text("ping")
        assert exc.value.code == 1008

    def test_get_worker_status(self):
        """Test get_worker_status command."""
        with client.websocket_connect("/ws?client_type=client") as websocket:
            websocket.receive_json()  # consume initial status
            websocket.send_text("get_worker_status")
            # Wait a bit or just assume it was called
            # Since it's a loop, we might need to send another message to ensure it processed the first one
            websocket.send_text("ping")
            websocket.receive_text()

            mock_manager.emit_worker_status.assert_called()

    def test_worker_broadcast_valid(self):
        """Test worker broadcasting valid JSON."""
        secret = settings.WORKER_SECRET
        with client.websocket_connect(f"/ws?client_type=worker&token={secret}") as websocket:
            websocket.receive_json()
            websocket.receive_json()

            msg = {"type": "TEST", "data": "hello"}
            websocket.send_text(json.dumps(msg))

            # Send ping to ensure the loop processed the broadcast
            websocket.send_text("ping")
            websocket.receive_text()

            mock_manager.broadcast.assert_called_with(msg)

    def test_worker_broadcast_invalid_json(self):
        """Test worker broadcasting invalid JSON."""
        secret = settings.WORKER_SECRET
        with client.websocket_connect(f"/ws?client_type=worker&token={secret}") as websocket:
            websocket.receive_json()
            websocket.receive_json()

            websocket.send_text("invalid json")

            # Send ping to ensure the loop processed the broadcast
            websocket.send_text("ping")
            websocket.receive_text()

            mock_manager.broadcast.assert_not_called()

    def test_worker_broadcast_non_dict(self):
        """Test worker broadcasting non-dictionary JSON."""
        secret = settings.WORKER_SECRET
        with client.websocket_connect(f"/ws?client_type=worker&token={secret}") as websocket:
            websocket.receive_json()
            websocket.receive_json()

            websocket.send_text(json.dumps(["not", "a", "dict"]))

            # Send ping to ensure the loop processed the broadcast
            websocket.send_text("ping")
            websocket.receive_text()

            mock_manager.broadcast.assert_not_called()

    def test_worker_broadcast_exception(self):
        """Test worker broadcast when an exception occurs in manager.broadcast."""
        mock_manager.broadcast.side_effect = Exception("Broadcast failed")
        secret = settings.WORKER_SECRET
        with client.websocket_connect(f"/ws?client_type=worker&token={secret}") as websocket:
            websocket.receive_json()
            websocket.receive_json()

            msg = {"type": "TEST"}
            websocket.send_text(json.dumps(msg))

            # Send ping to ensure the loop processed the broadcast
            websocket.send_text("ping")
            websocket.receive_text()

            mock_manager.broadcast.assert_called_with(msg)
        mock_manager.broadcast.side_effect = None
