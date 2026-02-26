import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional, Set
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class Websocket:
    """
    Singleton class to manage WebSocket connections and broadcasting.
    Handles communication between Server <-> Frontend and Worker <-> Server.

    Architectural improvements:
    - Uses Sets for O(1) membership tests and removal.
    - Provides `stream_events` generator for resource-safe SSE.
    - Caps message queues to prevent OOM from slow consumers.
    """

    _instance: Optional["Websocket"] = None

    # Class-level defaults (to be shadowed by instance attrs in __new__)
    active_connections: Set[WebSocket] = set()
    active_listeners: Set[asyncio.Queue] = set()
    _worker_connection: Optional[WebSocket] = None
    _worker_metadata: Dict[str, Any] = {}
    _worker_last_seen: float = 0.0
    upstream_connection: Any = None
    _last_sse_log_time: float = 0.0

    def __new__(cls) -> "Websocket":
        if cls._instance is None:
            cls._instance = super(Websocket, cls).__new__(cls)
            cls._instance.active_connections = set()
            cls._instance.active_listeners = set()
            cls._instance._worker_connection = None
            cls._instance._worker_metadata = {}
            cls._instance._worker_last_seen = 0.0
            cls._instance.upstream_connection = None
            cls._instance._last_sse_log_time = 0.0
        return cls._instance

    # --- Client Connection Management ---

    async def connect(self, websocket: WebSocket) -> None:
        """Accepts a new WebSocket connection."""
        await websocket.accept()
        # Add unique ID for tracing
        websocket.conn_id = str(uuid4())[:8]
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. ID: {websocket.conn_id}. Active connections: {len(self.active_connections)}")

        # Send current worker status immediately
        await self.emit_worker_status(self.is_worker_online)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Handles WebSocket disconnection."""
        conn_id = getattr(websocket, "conn_id", "unknown")
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. ID: {conn_id}. Active connections: {len(self.active_connections)}")

        if websocket == self._worker_connection:
            await self.handle_worker_disconnect()

    # --- SSE / Event Streaming ---

    async def stream_events(self) -> AsyncGenerator[str, None]:
        """
        Yields broadcast messages as they arrive.
        Context-managed safety: ensures queue cleanup on exit.
        Preferred over subscribe/unsubscribe.
        """
        queue = asyncio.Queue(maxsize=100)  # Cap size to prevent leaks
        self.active_listeners.add(queue)
        try:
            while True:
                message = await queue.get()
                yield message
                queue.task_done()
        finally:
            self.active_listeners.discard(queue)

    def subscribe(self) -> asyncio.Queue:
        """
        Legacy subscription. Returns a queue.
        Caller MUST manually call unsubscribe().
        """
        queue = asyncio.Queue(maxsize=100)
        self.active_listeners.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribes a listener queue."""
        self.active_listeners.discard(queue)

    # --- Worker Management ---

    @property
    def is_worker_online(self) -> bool:
        return self._worker_connection is not None

    async def register_worker(self, websocket: WebSocket, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Registers a websocket connection as the dedicated worker connection."""
        conn_id = getattr(websocket, "conn_id", "unknown")

        # P0 FIX: Detect multiple workers
        hostname = (metadata or {}).get("hostname", "unknown")

        if self._worker_connection and self._worker_connection != websocket:
            old_id = getattr(self._worker_connection, "conn_id", "old")
            old_host = self._worker_metadata.get("hostname", "unknown")

            logger.warning(
                f"Replacing existing worker connection. " f"Old: {old_id} ({old_host}), New: {conn_id} ({hostname})"
            )
            # Close old worker connection to prevent zombie
            try:
                await self._worker_connection.close()
            except Exception as e:
                logger.warning(f"Failed to close old worker connection: {e}")

        self._worker_connection = websocket
        self._worker_metadata = metadata or {}
        self._worker_last_seen = time.time()

        logger.info(f"Worker registered successfully. ID: {conn_id} | Host: {hostname}")
        await self.emit_worker_status(True)

    def unregister_worker(self) -> None:
        self._worker_connection = None
        self._worker_metadata = {}
        self._worker_last_seen = 0.0
        logger.info("Worker unregistered.")

    async def handle_worker_disconnect(self) -> None:
        self.unregister_worker()
        await self.emit_worker_status(False)

    # --- Broadcasting ---

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Broadcasts a JSON message to all connected clients and listeners.
        """
        try:
            message_str = json.dumps(message)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize broadcast message: {e}")
            return

        # 1. Forward to Upstream (Worker -> API)
        if self.upstream_connection:
            try:
                await self.upstream_connection.send(message_str)
            except Exception as e:
                logger.warning(f"Failed to send to upstream: {e}")

        if not self.active_connections and not self.active_listeners:
            return

        # 2. WebSocket Clients
        # Create tasks for all connections
        # We start headers/execution immediately
        tasks = []
        dead_connections = []

        # 2. WebSocket Clients
        if self.active_connections:
            # P0: Secure the broadcast against failing connections
            tasks = []
            ws_list = list(self.active_connections)

            for ws in ws_list:
                tasks.append(asyncio.wait_for(ws.send_text(message_str), timeout=2.0))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, res in enumerate(results):
                    if isinstance(res, Exception):
                        ws = ws_list[i]
                        logger.warning(f"Failed to send to WebSocket [ID: {getattr(ws, 'conn_id', '?')}]: {res}")
                        dead_connections.append(ws)

        if dead_connections:
            # Cleanup dead connections
            for ws in dead_connections:
                logger.debug(f"Removing dead connection [ID: {getattr(ws, 'conn_id', '?')}]")
                try:
                    await self.disconnect(ws)
                except Exception:
                    pass

        # 3. SSE Listeners
        # P1: Rate-limit this log to once per minute to avoid flooding (Pragmatic Architect)
        now = time.time()
        if now - self._last_sse_log_time > 60:
            logger.debug(f"ROUTER_SSE | Broadcasting to {len(self.active_listeners)} listeners")
            self._last_sse_log_time = now
        # Use simple iteration, queues are non-blocking usually unless full
        dead_queues = []
        for queue in self.active_listeners:
            try:
                # put_nowait raises QueueFull if full
                queue.put_nowait(message_str)
                logger.debug("ROUTER_SSE | Message put in queue successfully")
            except asyncio.QueueFull:
                logger.warning("Listener queue full, dropping message (slow consumer)")
                # Optional: dead_queues.append(queue) if we want to kick slow consumers
                pass
            except Exception as e:
                logger.error(f"ROUTER_SSE | Error putting message in queue: {e}")
                dead_queues.append(queue)

        for q in dead_queues:
            self.active_listeners.discard(q)

    def set_upstream(self, connection: Any) -> None:
        self.upstream_connection = connection

    # --- Domain Specific Emitters (Business Logic) ---
    # Kept for compatibility but should technically be in a service.

    async def emit_connector_status(self, connector_id: UUID, status: str) -> None:
        await self.broadcast({"type": "CONNECTOR_STATUS", "id": str(connector_id), "status": status})

    async def emit_connector_progress(self, connector_id: UUID, current: int, total: int, percent: float) -> None:
        await self.broadcast(
            {
                "type": "CONNECTOR_PROGRESS",
                "id": str(connector_id),
                "current": current,
                "total": total,
                "percent": round(percent, 2),
            }
        )

    async def emit_connector_created(self, connector_data: Dict[str, Any]) -> None:
        await self.broadcast({"type": "CONNECTOR_CREATED", "data": connector_data})

    async def emit_connector_updated(self, connector_data: Dict[str, Any]) -> None:
        await self.broadcast({"type": "CONNECTOR_UPDATED", "data": connector_data})

    async def emit_connector_deleted(self, connector_id: UUID) -> None:
        await self.broadcast({"type": "CONNECTOR_DELETED", "id": str(connector_id)})

    async def emit_document_created(self, doc_data: Dict[str, Any]) -> None:
        await self.broadcast({"type": "DOC_CREATED", "data": doc_data})

    async def emit_document_deleted(self, document_id: str, connector_id: str) -> None:
        await self.broadcast({"type": "DOC_DELETED", "id": str(document_id), "connector_id": str(connector_id)})

    async def emit_document_update(
        self,
        doc_id: str,
        status: str,
        details: Optional[str] = None,
        doc_token_count: Optional[int] = None,
        vector_point_count: Optional[int] = None,
        updated_at: Any = None,
        last_vectorized_at: Any = None,
        processing_duration_ms: Optional[float] = None,
        code: Optional[str] = None,
    ) -> None:
        payload: Dict[str, Any] = {"type": "DOC_UPDATE", "id": doc_id, "status": status, "details": details}
        if code:
            payload["code"] = code
        if doc_token_count is not None:
            payload["doc_token_count"] = doc_token_count
        if vector_point_count is not None:
            payload["vector_point_count"] = vector_point_count
        if updated_at:
            payload["updated_at"] = str(updated_at)
        if last_vectorized_at:
            payload["last_vectorized_at"] = str(last_vectorized_at)
        if processing_duration_ms is not None:
            payload["processing_duration_ms"] = processing_duration_ms

        await self.broadcast(payload)

    async def emit_worker_status(self, is_online: bool) -> None:
        """Broadcast worker status with metadata if online."""
        status_data = {
            "type": "WORKER_STATUS",
            "status": "online" if is_online else "offline",
            "metadata": self._worker_metadata if is_online else None,
        }
        await self.broadcast(status_data)

    async def record_worker_heartbeat(self) -> None:
        """Updates the last seen timestamp for the worker."""
        if self._worker_connection:
            self._worker_last_seen = time.time()
            logger.debug("Worker heartbeat received.")

    async def send_to_worker(self, message: Dict[str, Any]) -> None:
        """Sends a direct message to the registered worker."""
        if self._worker_connection:
            try:
                # Add timeout to avoid blocking if worker is dead/slow
                await asyncio.wait_for(self._worker_connection.send_text(json.dumps(message)), timeout=2.0)
            except Exception as e:
                logger.error(f"Failed to send to worker: {e}")

    async def emit_trigger_document_sync(self, document_id: str) -> None:
        await self.send_to_worker({"type": "TRIGGER_DOC_SYNC", "id": str(document_id)})

    async def emit_trigger_connector_sync(self, connector_id: str) -> None:
        await self.send_to_worker({"type": "TRIGGER_CONNECTOR_SYNC", "id": str(connector_id)})

    async def emit_document_progress(self, doc_id: str, processed: int, total: int) -> None:
        await self.broadcast({"type": "DOC_PROGRESS", "doc_id": doc_id, "processed": processed, "total": total})

    async def emit_dashboard_stats(self, stats: Dict[str, Any]) -> None:
        """Broadcast dashboard statistics to all connected clients."""
        await self.broadcast({"type": "DASHBOARD_STATS", "data": stats})

    async def emit_advanced_analytics_stats(self, stats: Dict[str, Any]) -> None:
        """Broadcast advanced analytics statistics to all connected clients."""
        await self.broadcast({"type": "ADVANCED_ANALYTICS_STATS", "data": stats})


manager = Websocket()


async def get_websocket() -> Websocket:
    return manager
