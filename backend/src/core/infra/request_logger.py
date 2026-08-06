"""Request logging middleware — logs every HTTP request with timing, status, and metadata."""

import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from core.infra.logging_config import get_logger
from observability import set_trace_id

logger = get_logger(__name__)

ASGIReceive = Callable[[], Awaitable[dict[str, Any]]]
ASGISend = Callable[[dict[str, Any]], Awaitable[None]]
Scope = dict[str, Any]

_EXEMPT_PREFIXES = ("/api/health", "/ws/", "/metrics")
_SENSITIVE_HEADERS = {b"authorization", b"cookie", b"x-api-key", b"proxy-authorization"}
_MAX_BODY_BYTES = 2 * 1024


def _mask(val: str, keep: int = 8) -> str:
    if len(val) <= keep + 4:
        return "***"
    return val[:4] + "***" + val[-keep:]


def _format_duration(seconds: float) -> str:
    if seconds < 1.0:
        return f"{seconds * 1000:.0f}ms"
    return f"{seconds:.2f}s"


class RequestLogMiddleware:
    """ASGI middleware that logs every non-exempt HTTP request/response cycle."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: ASGIReceive, send: ASGISend) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path.startswith(_EXEMPT_PREFIXES):
            await self.app(scope, receive, send)
            return

        request_id = uuid.uuid4().hex[:12]
        scope.setdefault("state", {})["request_id"] = request_id
        set_trace_id(request_id)

        method = scope.get("method", "UNKNOWN")
        query_string = scope.get("query_string", b"").decode("utf-8", errors="replace")
        client_ip = _client_ip(scope)

        # ── Wrap receive to capture body for logging ─────────────────────
        body_chunks: list[bytes] = []

        async def _receive() -> dict[str, Any]:
            msg = await receive()
            if msg["type"] == "http.request":
                body_chunks.append(msg.get("body", b""))
            return msg

        headers = {k: v for k, v in scope.get("headers", [])}
        content_length = headers.get(b"content-length", b"").decode()
        ua = headers.get(b"user-agent", b"").decode("utf-8", errors="replace")[:120]

        # ── Log incoming (without body — it hasn't been read yet) ─────────
        qs = f"?{query_string}" if query_string else ""
        logger.info(
            "[REQ] %s | %s%s | client=%s | len=%s | ua=%s | rid=%s",
            method,
            path,
            qs,
            client_ip,
            content_length or "-",
            ua or "-",
            request_id,
        )

        # ── Wrap send to capture status & timing ─────────────────────────
        start = time.monotonic()
        status_code = 0

        async def _send(msg: dict[str, Any]) -> None:
            nonlocal status_code
            if msg["type"] == "http.response.start":
                status_code = msg.get("status", 0)
            await send(msg)

        try:
            await self.app(scope, _receive, _send)
        except Exception:
            duration = time.monotonic() - start
            logger.exception(
                "[REQ] %s %s | UNHANDLED | duration=%s | rid=%s",
                method,
                path,
                _format_duration(duration),
                request_id,
            )
            raise

        duration = time.monotonic() - start

        # ── Build body for error logging ──────────────────────────────────
        body_bytes = b"".join(body_chunks)
        body_for_log = body_bytes[:_MAX_BODY_BYTES].decode("utf-8", errors="replace")
        if len(body_bytes) > _MAX_BODY_BYTES:
            body_for_log += "... (truncated)"

        duration = time.monotonic() - start

        # ── Log outgoing ─────────────────────────────────────────────────
        log_level = logger.info if status_code < 500 else logger.error
        log_level(
            "[RES] %s %s → %d | duration=%s | rid=%s",
            method,
            path,
            status_code,
            _format_duration(duration),
            request_id,
        )

        # If it was a client or server error, include a hint
        if 400 <= status_code < 500:
            logger.warning(
                "[RES] %s %s → %d | body[:500]=%s | rid=%s",
                method,
                path,
                status_code,
                body_for_log[:500],
                request_id,
            )
        elif status_code >= 500:
            logger.error(
                "[RES] %s %s → %d | body[:500]=%s | rid=%s",
                method,
                path,
                status_code,
                body_for_log[:500],
                request_id,
            )


def _client_ip(scope: dict[str, Any]) -> str:
    for header_name, header_value in scope.get("headers", []):
        if header_name == b"x-forwarded-for":
            return str(header_value.decode("utf-8").split(",")[0].strip())
        if header_name == b"x-real-ip":
            return str(header_value.decode("utf-8"))
    addr = scope.get("client")
    return str(addr[0]) if addr else "unknown"
