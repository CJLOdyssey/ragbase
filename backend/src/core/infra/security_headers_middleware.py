"""Security headers ASGI middleware — defence-in-depth for common web attacks.

Adds X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security,
Referrer-Policy, and Permissions-Policy headers to every HTTP response.

Pure ASGI to avoid Starlette BaseHTTPMiddleware header encoding issues with h11.
"""

from __future__ import annotations

import os

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Sensible defaults: nosniff + deny framing + HSTS 1 year with subdomains +
# strict referrer policy + feature lockdown (no camera/mic/geolocation/etc.).
# Override individual headers via env vars. Set to empty string to disable.
# Note: X-XSS-Protection is intentionally omitted — OWASP marks it deprecated
# and recommends against setting it (it is itself an XSS vector).
_SECURE_HEADERS: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (
        b"permissions-policy",
        b"camera=(), microphone=(), geolocation=(), payment=(), "
        b"usb=(), magnetometer=(), gyroscope=()",
    ),
]

# Per-header overrides — set env var to empty string to skip that header.
_ENV_OVERRIDES: dict[str, int] = {
    "X_CONTENT_TYPE_OPTIONS": 0,
    "X_FRAME_OPTIONS": 1,
    "STRICT_TRANSPORT_SECURITY": 2,
    "REFERRER_POLICY": 3,
    "PERMISSIONS_POLICY": 4,
}


class SecurityHeadersMiddleware:
    """Pure ASGI middleware that adds security headers to every response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        headers = _build_headers()

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                # Preserve multi-value headers (e.g. multiple Set-Cookie) —
                # dict() collapsing would silently drop all but the last.
                existing = list(message.get("headers", []))
                existing_keys = {k for k, _ in existing}
                for k, v in headers:
                    if k not in existing_keys:
                        existing.append((k, v))
                message["headers"] = existing
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
