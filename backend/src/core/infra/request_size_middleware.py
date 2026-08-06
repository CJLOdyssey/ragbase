from __future__ import annotations

import os

from starlette.types import ASGIApp, Receive, Scope, Send

_MAX_BODY = int(os.environ.get("MAX_REQUEST_BODY_SIZE", "10_485_760"))  # 10 MiB default


class RequestSizeLimitMiddleware:
    """Pure ASGI middleware that rejects requests with oversized bodies.

    Reads Content-Length header before processing body.
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
