"""Request body size limit middleware — rejects oversized requests with 413.

Pure ASGI to avoid Starlette BaseHTTPMiddleware buffering the whole body.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from core.env import env_int

# 10 MiB default.
_MAX_BODY = env_int("MAX_REQUEST_BODY_SIZE", 10_485_760)


class RequestSizeLimitMiddleware:
    """Pure ASGI middleware that rejects requests with oversized bodies.

    Reads the Content-Length header before processing the body. Chunked
    requests without Content-Length are not intercepted (documented limit).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                size = int(content_length)
                if size > _MAX_BODY:
                    await self._respond_413(send)
                    return
            except (ValueError, TypeError):
                pass

        await self.app(scope, receive, send)

    async def _respond_413(self, send: Send) -> None:
        body = b'{"detail":"Request entity too large"}'
        await send({
            "type": "http.response.start",
            "status": 413,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})