"""
WebSocket API endpoints for the Vectra backend.

This module provides the WebSocket endpoint for both frontend clients and
the Python worker, handling real-time communication and status updates.
"""

import json
import logging
import secrets
from enum import StrEnum
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect, status

from app.core.websocket import Websocket, get_websocket
from app.core.settings import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class ClientType(StrEnum):
    """
    Enumeration for different types of WebSocket clients.

    Attributes:
        CLIENT: Represents a frontend client (e.g., React Dashboard).
        WORKER: Represents the backend Python worker.
    """

    CLIENT = "client"
    WORKER = "worker"


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    manager: Websocket = Depends(get_websocket),
    client_type: ClientType = Query(ClientType.CLIENT),
    token: Optional[str] = Query(default=None),
) -> None:
    """
    WebSocket Endpoint handling both Frontend clients and the Python Worker.

    This endpoint manages the lifecycle of WebSocket connections, including
    handshake, security checks, message processing, and disconnection.
    Workers must provide valid authentication using a secret token.

    Protocol:
    - Frontend clients connect with `client_type=client`.
    - Workers connect with `client_type=worker` and must provide `x-worker-secret`
      header or a `token` query parameter matching `settings.WORKER_SECRET`.

    Args:
        websocket: The WebSocket connection instance.
        manager: Singleton manager for handling active connections.
        client_type: Type of the connecting client (client or worker).
            Defaults to ClientType.CLIENT.
        token: Optional authentication token (used if x-worker-secret header is missing).

    Returns:
        None

    Raises:
        WebSocketDisconnect: When the client disconnects normally.
    """
    func_name: str = "websocket_endpoint"

    logger.debug(f"CONNECT | {func_name} | Incoming connection [Type: {client_type}]")

    # 1. Connection Phase & Authentication
    try:
        if client_type == ClientType.WORKER:
            # Extract secret from headers or query param
            secret: Optional[str] = websocket.headers.get("x-worker-secret")

            if not secret and token:
                secret = token

            # Securely compare secrets to prevent timing attacks
            expected_secret = str(settings.WORKER_SECRET)
            if not secret or not secrets.compare_digest(secret, expected_secret):
                logger.warning(
                    f"SECURITY | {func_name} | Unauthorized Worker Attempt. "
                    f"Received: {secret!r} | Expected: [REDACTED]"
                )
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return

        # Accept connection and add to manager
        await manager.connect(websocket)

        conn_id: str = str(getattr(websocket, "conn_id", "unknown"))
        if client_type == ClientType.WORKER:
            logger.info(f"START | {func_name} | Secure Worker Connected [ID: {conn_id}]")
            await manager.register_worker(websocket)
        else:
            logger.debug(f"START | {func_name} | Client Connected [ID: {conn_id}]")

    except Exception as e:
        logger.error(f"FAIL | {func_name} | Connection refused or failed during setup | Error: {e}", exc_info=True)
        return

    # 2. Communication Loop
    try:
        while True:
            # Wait for text messages
            data: str = await websocket.receive_text()

            # Heartbeat check
            if data == "ping":
                await websocket.send_text("pong")
                continue

            # Status request
            if data == "get_worker_status":
                await manager.emit_worker_status(manager.is_worker_online)
                continue

            # Worker Broadcast: Re-broadcast worker messages to all frontend clients
            if client_type == ClientType.WORKER:
                try:
                    payload: Any = json.loads(data)
                    if isinstance(payload, dict):
                        await manager.broadcast(payload)
                    else:
                        logger.warning(f"Context | {func_name} | Msg: Worker sent non-dictionary JSON: {type(payload)}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Context | {func_name} | Msg: Invalid JSON from worker | Error: {e!r}")
                except Exception as e:
                    logger.error(
                        f"FAIL | {func_name} | Worker broadcast error | Error: {e}",
                        exc_info=True,
                    )

    except WebSocketDisconnect as e:
        logger.info(f"FINISH | {func_name} | {client_type} Disconnected [Code: {e.code}]")
    except Exception as e:
        logger.error(f"FAIL | {func_name} | Unexpected error in WS loop | Error: {e!r}", exc_info=True)
    finally:
        # 3. Cleanup Phase
        try:
            await manager.disconnect(websocket)
        except Exception as e:
            logger.debug(f"Cleanup | {func_name} | Disconnect failed (likely already closed) | Error: {e}")
