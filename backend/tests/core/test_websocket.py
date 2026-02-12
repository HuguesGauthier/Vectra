import json
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from fastapi import WebSocket

from app.core.websocket import Websocket


@pytest.fixture(autouse=True)
async def cleanup_manager():
    """Ensure the singleton manager state is clean."""
    manager = Websocket()
    manager.active_connections.clear()
    manager.active_listeners.clear()
    manager._worker_connection = None
    manager.upstream_connection = None
    yield


@pytest.fixture
def manager():
    return Websocket()


async def successful_coro(*args, **kwargs):
    return None


@pytest.mark.asyncio
class TestWebsocket:
    async def test_connect_disconnect(self, manager):
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.accept.side_effect = successful_coro
        await manager.connect(mock_ws)
        assert mock_ws in manager.active_connections

        await manager.disconnect(mock_ws)
        assert mock_ws not in manager.active_connections

    async def test_broadcast_p0_safety(self, manager):
        """Verify P0 fix: exceptions during gather don't crash broadcast."""
        mock_ws_alive = AsyncMock(spec=WebSocket)
        mock_ws_alive.send_text.side_effect = successful_coro

        mock_ws_fail = AsyncMock(spec=WebSocket)

        # Exception during await
        async def fail_coro(*args, **kwargs):
            raise Exception("Fail")

        mock_ws_fail.send_text.side_effect = fail_coro

        manager.active_connections.update([mock_ws_alive, mock_ws_fail])

        # Should not raise
        await manager.broadcast({"t": "msg"})

        # Dead should be removed
        assert mock_ws_alive in manager.active_connections
        assert mock_ws_fail not in manager.active_connections

    async def test_worker_registration(self, manager):
        mock_ws = AsyncMock(spec=WebSocket)
        # Mock broadcast as it's called during registration
        with patch.object(manager, "broadcast", side_effect=successful_coro):
            await manager.register_worker(mock_ws)
            assert manager.is_worker_online
            assert manager._worker_connection == mock_ws

            manager.unregister_worker()
            assert not manager.is_worker_online

    async def test_emit_document_update(self, manager):
        with patch.object(manager, "broadcast", side_effect=successful_coro) as mock_b:
            dt = datetime.now()
            await manager.emit_document_update("id", "status", updated_at=dt)
            mock_b.assert_called()
            payload = mock_b.call_args[0][0]
            assert payload["type"] == "DOC_UPDATE"
            assert payload["updated_at"] == str(dt)

    async def test_stream_events_simple(self, manager):
        """Verify SSE listeners get messages."""
        gen = manager.stream_events()
        it = gen.__aiter__()

        # Generator is lazy, must start iteration to register
        task = asyncio.create_task(it.__anext__())

        # Wait for registration
        for _ in range(100):
            if len(manager.active_listeners) > 0:
                break
            await asyncio.sleep(0.01)

        assert len(manager.active_listeners) == 1

        await manager.broadcast({"hello": "world"})

        res = await asyncio.wait_for(task, timeout=2.0)
        assert json.loads(res) == {"hello": "world"}

        await gen.aclose()
        assert len(manager.active_listeners) == 0
