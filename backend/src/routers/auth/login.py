"""Login, refresh token, and logout endpoints."""

from datetime import UTC, datetime
from typing import Any

import bcrypt
from auth import AUTH_SECRET, create_token
from broker import get_redis
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from fastapi import APIRouter, Request, Response
from repository.auth import (
    consume_refresh_token,
    create_refresh_token,
    get_user_by_email,
    increment_failed_logins,
    reset_failed_logins,
)

from .schemas import (
    ACCESS_TOKEN_TTL,
    AuthResponse,
    LoginRequest,
    _build_user_response,
    _check_rate_limit,
    _clear_access_token_cookie,
    _clear_refresh_token_cookie,
    _client_ip,
    _create_auth_response,
    _mask_email,
    _set_access_token_cookie,
    _set_refresh_token_cookie,
)

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest, request: Request, response: Response) -> Any:
    """Authenticate a user with email and password."""
    email = body.email.lower().strip()
    password = body.password
    r = get_redis()

    ip = _client_ip(request)
    rate_key_ip = f"auth:login:ip:{ip}"
    rate_key_email = f"auth:login:email:{email}"
    if not await _check_rate_limit(r, rate_key_ip, 10, 60):
        raise error_response(ErrorCode.RATE_LIMITED, detail="操作过于频繁，请稍后重试")
    if not await _check_rate_limit(r, rate_key_email, 5, 60):
        raise error_response(ErrorCode.RATE_LIMITED, detail="操作过于频繁，请稍后重试")

    user = await get_user_by_email(email)
    if user is None:
        raise error_response(ErrorCode.AUTH_UNAUTHORIZED, detail="邮箱或密码错误")

    if user.locked_until:
        locked_until = user.locked_until.replace(tzinfo=UTC) if user.locked_until.tzinfo is None else user.locked_until
        if locked_until > datetime.now(UTC):
            remaining = int((locked_until - datetime.now(UTC)).total_seconds())
            raise error_response(
                ErrorCode.AUTH_ACCOUNT_LOCKED,
                detail=f"账户已被临时锁定，请 {max(remaining, 60)} 秒后再试",
            )

    if not user.is_verified:
        raise error_response(ErrorCode.AUTH_EMAIL_NOT_VERIFIED, detail="请先验证邮箱")

    if not user.is_active:
        raise error_response(ErrorCode.AUTH_ACCOUNT_DISABLED, detail="账户已被禁用")

    if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        await increment_failed_logins(email)
        raise error_response(ErrorCode.AUTH_UNAUTHORIZED, detail="邮箱或密码错误")

    await reset_failed_logins(email)
    logger.info("User logged in: %s", _mask_email(email))

    auth_resp = await _create_auth_response(user.id, user.email, user.username, body.remember_me)
    _set_access_token_cookie(response, auth_resp.access_token, secure=request.url.scheme == "https")
    _set_refresh_token_cookie(response, auth_resp.refresh_token, secure=request.url.scheme == "https")
    return AuthResponse(
        access_token=auth_resp.access_token,
        refresh_token="",
        expires_in=auth_resp.expires_in,
        user=auth_resp.user,
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh(request: Request, response: Response) -> Any:
    """Exchange the refresh_token cookie for new access and refresh tokens."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise error_response(ErrorCode.AUTH_TOKEN_EXPIRED, detail="登录已过期，请重新登录")
    user, family_id = await consume_refresh_token(refresh_token)
    if user is None:
        _clear_refresh_token_cookie(response)
        raise error_response(ErrorCode.AUTH_TOKEN_EXPIRED, detail="登录已过期，请重新登录")

    new_refresh_token_raw, _ = await create_refresh_token(user.id, family_id=family_id, ttl_days=7)
    access_token = create_token(user.id, AUTH_SECRET, ttl=ACCESS_TOKEN_TTL)
    user_resp = await _build_user_response(user.id, user.email, user.username)

    _set_access_token_cookie(response, access_token, secure=request.url.scheme == "https")
    _set_refresh_token_cookie(response, new_refresh_token_raw, secure=request.url.scheme == "https")
    return AuthResponse(access_token="", refresh_token="", expires_in=ACCESS_TOKEN_TTL, user=user_resp)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response) -> None:
    """Invalidate the refresh_token cookie and clear both auth cookies."""
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token:
        await consume_refresh_token(refresh_token)
    _clear_access_token_cookie(response)
    _clear_refresh_token_cookie(response)
