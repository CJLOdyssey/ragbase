"""Content-Security-Policy ASGI middleware for defense-in-depth XSS protection.

Pure ASGI to avoid Starlette BaseHTTPMiddleware header encoding issues with h11.
"""

from __future__ import annotations

import os

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Sensible default: self-only for API responses. Override via CSP_POLICY env var
# for stricter rules (e.g. script-src, connect-src for frontend origins).
# Set to empty string to disable.
_DEFAULT_CSP = "default-src 'self'; frame-src 'none'; object-src 'none'; base-uri 'self'"
CSP_POLICY = os.environ.get("CSP_POLICY", _DEFAULT_CSP).strip()


class CSPMiddleware:
    """Pure ASGI middleware that adds Content-Security-Policy header."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        policy = CSP_POLICY
        if not policy:
            await self.app(scope, receive, send)
            return

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append(
                    (b"content-security-policy", policy.encode("ascii"))
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, _send)
