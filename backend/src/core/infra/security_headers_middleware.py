"""Security headers ASGI middleware — defence-in-depth for common web attacks.

Adds X-Content-Type-Options, X-Frame-Options, and Strict-Transport-Security
headers to every HTTP response.

Pure ASGI to avoid Starlette BaseHTTPMiddleware header encoding issues with h11.
"""

from __future__ import annotations

import os

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Sensible default: nosniff + deny framing + HSTS 1 year with subdomains.
# Override individual headers via env vars. Set to empty string to disable.
_SECURE_HEADERS: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
]

# Per-header overrides — set env var to empty string to skip that header.
_ENV_OVERRIDES: dict[str, int] = {
    "X_CONTENT_TYPE_OPTIONS": 0,
    "X_FRAME_OPTIONS": 1,
    "STRICT_TRANSPORT_SECURITY": 2,
}


class SecurityHeadersMiddleware:
    """Pure ASGI middleware that adds security headers to every response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        headers = _build_headers()

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                existing = dict(message.get("headers", []))
                for k, v in headers:
                    if k not in existing:
                        existing[k] = v
                message["headers"] = list(existing.items())
            await send(message)

        await self.app(scope, receive, _send)


def _build_headers() -> list[tuple[bytes, bytes]]:
    result: list[tuple[bytes, bytes]] = []
    for key, idx in _ENV_OVERRIDES.items():
        val = os.environ.get(key)
        if val is not None:
            if val:
                result.append((_SECURE_HEADERS[idx][0], val.encode("ascii")))
            # empty string → skip this header
        else:
            result.append(_SECURE_HEADERS[idx])
    return result
