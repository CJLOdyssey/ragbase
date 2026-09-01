"""Shared ASGI scope helpers for middleware implementations."""

from __future__ import annotations

import os
from typing import Any

# Headers trusted for client IP resolution, checked in order.
_FORWARDED_FOR = b"x-forwarded-for"
_REAL_IP = b"x-real-ip"

# Only trust proxy headers when the app is deployed behind a trusted reverse
# proxy that overwrites them. Direct-exposure deployments (uvicorn on
# 0.0.0.0) must NOT trust client-supplied X-Forwarded-For — attackers would
# spoof it to bypass IP-based rate limiting (OWASP A07).
_TRUST_PROXY_HEADERS = os.environ.get("TRUST_PROXY_HEADERS", "0") in ("1", "true", "yes")


def client_ip(scope: dict[str, Any]) -> str:
    """Resolve the client IP from proxy headers, falling back to the peer address.

    Proxy headers are only honored when ``TRUST_PROXY_HEADERS=1`` (deployment
    behind a trusted reverse proxy that strips client-supplied headers).
    Otherwise the TCP peer address is authoritative.
    """
    if _TRUST_PROXY_HEADERS:
        for header_name, header_value in scope.get("headers", []):
            if header_name == _FORWARDED_FOR:
                return str(header_value.decode("utf-8").split(",")[0].strip())
            if header_name == _REAL_IP:
                return str(header_value.decode("utf-8"))
    addr = scope.get("client")
    return str(addr[0]) if addr else "unknown"


__all__ = ["client_ip"]
