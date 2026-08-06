"""FastAPI middleware that validates JWT tokens on protected routes."""

from typing import Any, cast

from core.infra.logging_config import get_logger
from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

from auth.auth_jwt import AUTH_SECRET, decode_jwt
from auth.auth_rbac import AUTH_ENABLED, PUBLIC_PATHS, PUBLIC_PREFIXES

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that validates JWT tokens on protected routes."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Validate JWT tokens on incoming requests."""
        # Skip auth for public paths
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
            return cast(Response, await call_next(request))

        # Skip if auth is not enabled
        if not AUTH_ENABLED:
            return cast(Response, await call_next(request))

        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        elif "?" in str(request.url) and "token=" in str(request.url):
            # Also support query param for WebSocket
            from urllib.parse import parse_qs

            token = parse_qs(str(request.url.query)).get("token", [""])[0]

        client_ip = request.client.host if request.client else "?"

        # ── Guest mode: no token → pass through as unauthenticated ────
        if not token:
            request.state.is_authenticated = False
            return cast(Response, await call_next(request))

        payload = decode_jwt(token, AUTH_SECRET)
        if payload is None:
            logger.warning(
                "Auth token rejected | client=%s | path=%s",
                client_ip, path,
            )
            request.state.is_authenticated = False
            return cast(Response, await call_next(request))

        user_id = payload.get("sub", "unknown")
        # Attach user info to request state
        request.state.user_id = user_id
        request.state.is_authenticated = True

        return cast(Response, await call_next(request))
