"""Shared Pydantic schemas and helpers for the auth sub-package."""

import logging
import secrets
from typing import TYPE_CHECKING, Any

from fastapi import Request
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from redis.asyncio import Redis as _AsyncRedis

if TYPE_CHECKING:
    AsyncRedis = _AsyncRedis[Any]
else:
    AsyncRedis = _AsyncRedis

from auth import AUTH_SECRET, create_token
from repository.auth import create_refresh_token, get_user_by_id, get_user_roles

logger = logging.getLogger(__name__)

# ── Request schemas ─────────────────────────────────────────────────


class SendRegisterCodeRequest(BaseModel):
    email: EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    code: str
    password: str


class VerifyRequest(BaseModel):
    email: EmailStr
    code: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class RefreshRequest(BaseModel):
    """Refresh token arrives via httpOnly cookie — body intentionally empty."""


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str


class LogoutRequest(BaseModel):
    """Logout reads refresh_token from httpOnly cookie — body intentionally empty."""


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class MergeRequest(BaseModel):
    guest_id: str


# ── Response schemas ────────────────────────────────────────────────


class UserResponse(BaseModel):
    id: str
    email: str
    username: str | None
    roles: list[str]
    is_verified: bool


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class AuthConfigResponse(BaseModel):
    enabled: bool
    mode: str


class MessageResponse(BaseModel):
    message: str


class EmailHintResponse(BaseModel):
    message: str
    email_hint: str


# ── Helpers ─────────────────────────────────────────────────────────


def _generate_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _mask_email(email: str) -> str:
    """Mask email for display: u***@example.com."""
    local, at, domain = email.partition("@")
    if len(local) <= 1:
        return f"{local}***{at}{domain}"
    return f"{local[0]}***{at}{domain}"


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _check_rate_limit(r: AsyncRedis, key: str, max_count: int, window: int = 60) -> bool:
    """Increment + check rate limit; degrade open on Redis failure."""
    try:
        current = await r.incr(key)
        if current == 1:
            await r.expire(key, window)
        return bool(current <= max_count)
    except Exception:
        logger.warning("Rate limit Redis check failed — allowing request")
        return True


async def _store_code_in_redis(r: AsyncRedis, key: str, code: str, ttl: int) -> None:
    await r.set(key, code)
    await r.expire(key, ttl)


# ── Auth response builders (shared across sub-modules) ──────────────


async def _build_user_response(user_id: str, email: str, username: str | None) -> UserResponse:
    roles = await get_user_roles(user_id)
    user = await get_user_by_id(user_id)
    return UserResponse(
        id=user_id,
        email=email,
        username=username,
        roles=roles,
        is_verified=user.is_verified if user else False,
    )


ACCESS_TOKEN_TTL = 900  # 15 minutes — short-lived access token per best practice


def _cookie_secure(request: Request) -> bool:
    """Secure flag: https (direct or proxy-forwarded) → Secure; http dev → none.

    Reverse proxies must forward X-Forwarded-Proto (uvicorn --proxy-headers
    handles it); without it a production request behind TLS looks like http
    and the cookie would silently lose Secure, sending tokens in cleartext.
    """
    if request.url.scheme == "https":
        return True
    forwarded = request.headers.get("X-Forwarded-Proto")
    return "https" in (forwarded or "").lower().split(",")


def _set_access_token_cookie(response: Response, access_token: str, *, secure: bool) -> None:
    """Set the access token as an httpOnly cookie (prevents XSS theft).

    The cookie is httpOnly (inaccessible to JS), SameSite=Lax (CSRF-safe
    for top-level navigations). ``secure`` follows the request scheme
    (https → Secure; http dev → no Secure flag, else http clients silently
    drop the cookie and the frontend gets stuck on a "ghost login" where
    requests run anonymous while the UI still shows the user).
    The path is scoped to ``/api`` so the token is only sent to API
    endpoints, not static assets or unrelated routes.
    """
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=ACCESS_TOKEN_TTL,
        path="/api",
    )


def _clear_access_token_cookie(response: Response) -> None:
    """Clear the access_token httpOnly cookie on logout."""
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        samesite="lax",
        max_age=0,
        path="/api",
    )


REFRESH_TOKEN_TTL = 7 * 86400  # 7 days — matches create_refresh_token default ttl_days=7


def _set_refresh_token_cookie(response: Response, refresh_token: str, *, secure: bool) -> None:
    """Set the refresh token as an httpOnly cookie (prevents XSS theft).

    httpOnly (inaccessible to JS) + SameSite=Lax + existing XSRF header
    pattern per OWASP CSRF Prevention. Path scoped to /api. Read
    server-side only by the refresh/logout endpoints.
    """
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=REFRESH_TOKEN_TTL,
        path="/api",
    )


def _clear_refresh_token_cookie(response: Response) -> None:
    """Clear the refresh_token httpOnly cookie on logout."""
    response.set_cookie(
        key="refresh_token",
        value="",
        httponly=True,
        samesite="lax",
        max_age=0,
        path="/api",
    )


async def _create_auth_response(
    user_id: str, email: str, username: str | None, remember_me: bool = False
) -> AuthResponse:
    access_token = create_token(user_id, AUTH_SECRET, ttl=ACCESS_TOKEN_TTL)
    ttl_days = 30 if remember_me else 7
    refresh_token_raw, _ = await create_refresh_token(user_id, ttl_days=ttl_days)
    user_resp = await _build_user_response(user_id, email, username)
    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token_raw,
        expires_in=ACCESS_TOKEN_TTL,
        user=user_resp,
    )
