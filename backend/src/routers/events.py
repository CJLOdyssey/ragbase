"""Per-user domain event channel — cross-client realtime sync.

Authenticated frontends subscribe here to receive session CRUD events published
by any of the user's clients, keeping conversation lists in sync across
browsers/devices. Events are a fast-path cache invalidation; the DB remains the
source of truth (clients refetch fully on reconnect).
"""

import asyncio
import contextlib
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

    # 推流独立 task：Redis 事件 → WS。主循环专注断开检测。
    # 若这里 `async for subscribe_user_events` 阻塞等 Redis 消息而不监听客户端
    # 断开，客户端关闭后 task 挂着、pubsub 连接不归还 → Redis 池占满 →
    # MaxConnectionsError 阻塞全部 Redis 操作（run 失败"Too many connections"）。
    async def pump() -> None:
        async for event in subscribe_user_events(user_id):
            await websocket.send_json(event)

    pump_task = asyncio.create_task(pump())
    try:
        await websocket.send_json({"type": "status", "status": "connected"})
        # events WS 只推不收：receive 在客户端断开时抛 WebSocketDisconnect；
        # 每 30s 发 ping 检测半开连接（send 失败同样抛 → 清理）。
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive(), timeout=30.0)
            except TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue
            if msg.get("type") == "websocket.disconnect":
                break
    except (WebSocketDisconnect, RuntimeError):
        logger.info(
            "User events WS disconnected | user=%s | client=%s",
            user_id, client_host,
        )
    finally:
        # 关键：取消 pump → subscribe_user_events 的 finally close pubsub →
        # Redis 连接归还池，不累积。
        pump_task.cancel()
        with contextlib.suppress(Exception):
            await pump_task
        logger.info(
            "User events WS closed | user=%s | client=%s",
            user_id, client_host,
        )
