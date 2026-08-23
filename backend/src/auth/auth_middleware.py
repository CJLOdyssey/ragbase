"""FastAPI middleware that validates JWT tokens on protected routes."""

from typing import Any, cast

from core.infra.logging_config import get_logger
from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

from auth.auth_jwt import AUTH_SECRET, decode_jwt
from auth.auth_rbac import PUBLIC_PATHS, PUBLIC_PREFIXES

logger = get_logger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that validates JWT tokens on protected routes."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        """Validate JWT tokens on incoming requests."""
        # Skip auth for public paths
        path = request.url.path
        if path in PUBLIC_PATHS or path.startswith(PUBLIC_PREFIXES):
            return cast(Response, await call_next(request))

        # Extract token from Authorization header, query param, or httpOnly cookie
        auth_header = request.headers.get("Authorization", "")
        token = ""
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        elif "?" in str(request.url) and "token=" in str(request.url):
            # Also support query param for WebSocket
            from urllib.parse import parse_qs

            token = parse_qs(str(request.url.query)).get("token", [""])[0]
        else:
            token = request.cookies.get("access_token", "")

        client_ip = request.client.host if request.client else "?"

        # No token → reject with 401
        if not token:
            request.state.is_authenticated = False
            logger.warning("Auth missing token | client=%s | path=%s", client_ip, path)
            return JSONResponse(
                status_code=401,
                content={
                    "detail": {
                        "error": {"code": "AUTH_001", "message": "未登录或会话已过期"}
                    }
                },
            )

        payload = decode_jwt(token, AUTH_SECRET)
        if payload is None:
            logger.warning(
                "Auth token rejected | client=%s | path=%s",
                client_ip, path,
            )
            request.state.is_authenticated = False
            return JSONResponse(
                status_code=401,
                content={
                    "detail": {
                        "error": {"code": "AUTH_001", "message": "未登录或会话已过期"}
                    }
                },
            )

        user_id = payload.get("sub", "unknown")
        # 校验用户仍存在：用户合并/删除后旧 JWT 的 sub 已失效
        if user_id != "unknown":
            try:
                from repository.auth import get_user_by_id

                user = await get_user_by_id(user_id)
            except Exception:
                user = None
            if user is None:
                logger.warning(
                    "Auth token user not found | user_id=%s | client=%s | path=%s",
                    user_id, client_ip, path,
                )
                request.state.user_invalid_token = True
                request.state.is_authenticated = False
                return cast(Response, await call_next(request))

        # Attach user info to request state
        request.state.user_id = user_id
        request.state.is_authenticated = True

        return cast(Response, await call_next(request))
