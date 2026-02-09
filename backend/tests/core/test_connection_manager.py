import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.connection_manager import ConnectionManager


@pytest.fixture
def connection_manager():
    # Singleton pattern reset logic if needed, or fresh instance logic (though it uses __new__)
    # For testing, we can just instantiate it but better to reset its state
    cm = ConnectionManager()
    cm.active_connections = set()
    cm.active_listeners = set()
    cm._worker_connection = None
    cm.upstream_connection = None
    return cm


@pytest.mark.asyncio
class TestConnectionManager:
    async def test_connect(self, connection_manager):
        mock_ws = AsyncMock()
        await connection_manager.connect(mock_ws)

        mock_ws.accept.assert_awaited_once()
        assert mock_ws in connection_manager.active_connections
        # Should also try to broadcast worker status (offline by default)

    async def test_disconnect(self, connection_manager):
        mock_ws = AsyncMock()
        connection_manager.active_connections.add(mock_ws)

        await connection_manager.disconnect(mock_ws)
        assert mock_ws not in connection_manager.active_connections

    async def test_broadcast(self, connection_manager):
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        connection_manager.active_connections.update([mock_ws1, mock_ws2])

        message = {"type": "TEST"}
        await connection_manager.broadcast(message)

        expected_str = json.dumps(message)
        mock_ws1.send_text.assert_awaited_with(expected_str)
        mock_ws2.send_text.assert_awaited_with(expected_str)

    async def test_broadcast_error_handling(self, connection_manager):
        # ws1 works, ws2 fails -> ws2 should be removed
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.send_text.side_effect = Exception("Closed")

        connection_manager.active_connections.update([mock_ws1, mock_ws2])

        await connection_manager.broadcast({"t": "x"})

        assert mock_ws1 in connection_manager.active_connections
        assert mock_ws2 not in connection_manager.active_connections

    # --- Worker Tests ---

    async def test_register_worker(self, connection_manager):
        mock_ws = AsyncMock()
        await connection_manager.register_worker(mock_ws)

        assert connection_manager.is_worker_online
        assert connection_manager._worker_connection == mock_ws

    async def test_unregister_worker(self, connection_manager):
        mock_ws = AsyncMock()
        await connection_manager.register_worker(mock_ws)
        connection_manager.unregister_worker()

        assert not connection_manager.is_worker_online
        assert connection_manager._worker_connection is None

    async def test_worker_disconnect_cleanup(self, connection_manager):
        mock_ws = AsyncMock()
        # Connect normally
        await connection_manager.connect(mock_ws)
        # Register as worker
        await connection_manager.register_worker(mock_ws)

        # Now disconnect
        await connection_manager.disconnect(mock_ws)

        assert not connection_manager.is_worker_online
        assert mock_ws not in connection_manager.active_connections

    async def test_send_to_worker(self, connection_manager):
        mock_ws = AsyncMock()
        await connection_manager.register_worker(mock_ws)

        msg = {"cmd": "work"}
        await connection_manager.send_to_worker(msg)

        mock_ws.send_text.assert_awaited_with(json.dumps(msg))

    async def test_send_to_worker_no_worker(self, connection_manager):
        # Should normally just log warning/error and not crash
        await connection_manager.send_to_worker({"x": 1})
        # No assertions needed, just ensuring no raise

    async def test_send_to_worker_timeout(self, connection_manager):
        """Verify that slow send_to_worker is caught by timeout."""
        mock_ws = AsyncMock()
        await connection_manager.register_worker(mock_ws)

        # Simulate hang
        async def slow_send(*args, **kwargs):
            await asyncio.sleep(2.1)

        mock_ws.send_text.side_effect = slow_send

        # Should NOT raise, but log error "TimeoutError"
        await connection_manager.send_to_worker({"ping": "pong"})
        # Success if we reach here without unhandled exception

    # --- Upstream Sending ---

    async def test_upstream_forwarding(self, connection_manager):
        mock_upstream = AsyncMock()
        connection_manager.set_upstream(mock_upstream)

        message = {"broadcast": True}
        await connection_manager.broadcast(message)

        mock_upstream.send.assert_awaited_with(json.dumps(message))

    async def test_emit_helpers(self, connection_manager):
        # Test one helper as representative of all structured emitters
        mock_broadcast = AsyncMock()
        connection_manager.broadcast = mock_broadcast

        await connection_manager.emit_worker_status(True)
        mock_broadcast.assert_awaited_with({"type": "WORKER_STATUS", "status": "online"})

        await connection_manager.emit_system_metrics(10.0, 20.0)
        mock_broadcast.assert_awaited()
        # Checking payload structure roughly
        args, _ = mock_broadcast.call_args
        assert args[0]["type"] == "DASHBOARD_UPDATE"
        assert args[0]["data"]["cpu"] == 10.0

    async def test_register_worker_replacement(self, connection_manager):
        """Test registering a new worker when one already exists."""
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        await connection_manager.register_worker(mock_ws1)

        # Register second worker - should verify log (covered by line hit)
        await connection_manager.register_worker(mock_ws2)

        assert connection_manager._worker_connection == mock_ws2

    async def test_broadcast_serialization_error(self, connection_manager):
        """Test broadcast with non-serializable object."""
        # Sets with objects are not JSON serializable by default
        bad_obj = {"set": {object()}}

        # Should catch TypeError/ValueError and log error, returning None
        await connection_manager.broadcast(bad_obj)
        # No assertion needed, just verifying it doesn't raise

    async def test_emit_connector_lifecycle(self, connection_manager):
        """Test connector lifecycle events."""
        connection_manager.broadcast = AsyncMock()

        # Created
        await connection_manager.emit_connector_created({"id": "1", "name": "C1"})
        connection_manager.broadcast.assert_awaited_with(
            {"type": "CONNECTOR_CREATED", "data": {"id": "1", "name": "C1"}}
        )

        # Deleted
        cid = "123"
        await connection_manager.emit_connector_deleted(cid)
        connection_manager.broadcast.assert_awaited_with({"type": "CONNECTOR_DELETED", "id": "123"})

    async def test_emit_document_events(self, connection_manager):
        """Test document events including usage of all optional params."""
        connection_manager.broadcast = AsyncMock()

        # Deleted
        await connection_manager.emit_document_deleted("doc1", "conn1")
        connection_manager.broadcast.assert_awaited_with({"type": "DOC_DELETED", "id": "doc1", "connector_id": "conn1"})

        # Update with Code and Datetime
        dt_now = datetime.now()
        await connection_manager.emit_document_update(
            doc_id="doc1", status="INDEXED", code="def foo(): pass", updated_at=dt_now, last_vectorized_at="2023-01-01"
        )

        call_args = connection_manager.broadcast.call_args[0][0]
        assert call_args["type"] == "DOC_UPDATE"
        assert call_args["code"] == "def foo(): pass"
        assert call_args["updated_at"] == str(dt_now)
        assert call_args["last_vectorized_at"] == "2023-01-01"

        # Update with String dates (covers else branches line 180)
        await connection_manager.emit_document_update(
            doc_id="doc2",
            status="INDEXED",
            updated_at="2023-01-01",
        )
        call_args = connection_manager.broadcast.call_args[0][0]
        assert call_args["updated_at"] == "2023-01-01"

    async def test_trigger_sync(self, connection_manager):
        """Test trigger sync emission to worker."""
        connection_manager.send_to_worker = AsyncMock()

        await connection_manager.emit_trigger_document_sync("doc1")

        connection_manager.send_to_worker.assert_awaited_with({"type": "TRIGGER_DOC_SYNC", "id": "doc1"})

    async def test_emit_business_metrics(self, connection_manager):
        """Test business metrics emission."""
        connection_manager.broadcast = AsyncMock()

        metrics = {"total_files": 100}
        await connection_manager.emit_business_metrics(metrics)

        connection_manager.broadcast.assert_awaited_with(
            {"type": "DASHBOARD_UPDATE", "event": "BUSINESS_METRICS", "data": metrics}
        )
