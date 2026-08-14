"""Per-user domain event channel — cross-client realtime sync.

Authenticated frontends subscribe here to receive session CRUD events published
by any of the user's clients, keeping conversation lists in sync across
browsers/devices. Events are a fast-path cache invalidation; the DB remains the
source of truth (clients refetch fully on reconnect).
"""

from typing import Any

from auth.auth_jwt import AUTH_SECRET, decode_jwt
from auth.auth_rbac import AUTH_ENABLED
from broker import subscribe_user_events
from core.infra.logging_config import get_logger
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = get_logger(__name__)
router = APIRouter(tags=["events"])


def _ws_user_id(websocket: WebSocket) -> str:
    """Resolve user identity from the WS handshake access_token cookie."""
    if not AUTH_ENABLED:
        return "guest"
    token = websocket.cookies.get("access_token")
    if not token:
        return ""
    payload = decode_jwt(token, AUTH_SECRET)
    if payload:
        uid = payload.get("sub")
        if isinstance(uid, str) and uid:
            return uid
    return ""


@router.websocket("/api/ws/events")
async def user_events_ws(websocket: WebSocket) -> Any:
    """Stream domain events for the authenticated user."""
    client_host = websocket.client.host if websocket.client else "?"
    await websocket.accept()
    user_id = _ws_user_id(websocket)
    if not user_id:
        logger.warning(
            "User events WS rejected | client=%s (not authenticated)",
            client_host,
        )
        await websocket.send_json({"type": "status", "status": "error", "error": "未登录"})
        await websocket.close(code=1008)
        return
    logger.info(
        "User events WS connected | user=%s | client=%s",
        user_id, client_host,
    )
    try:
        await websocket.send_json({"type": "status", "status": "connected"})
        async for event in subscribe_user_events(user_id):
            try:
                await websocket.send_json(event)
            except WebSocketDisconnect:
                return
    except WebSocketDisconnect:
        logger.info(
            "User events WS disconnected | user=%s | client=%s",
            user_id, client_host,
        )
    finally:
        logger.info(
            "User events WS closed | user=%s | client=%s",
            user_id, client_host,
        )
