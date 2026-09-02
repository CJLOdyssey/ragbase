"""Password management endpoints: forgot, reset, change."""

import hmac
from typing import Any

import bcrypt
from auth import CurrentUser, get_current_user
from auth.password_policy import validate_password
from broker import get_redis
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from fastapi import APIRouter, Depends
from repository.auth import (
    get_user_by_email,
    get_user_by_id,
    revoke_all_user_tokens,
    update_password,
)
from services.email_service import (
    build_password_changed_email,
    build_reset_email,
    send_email,
)

from .schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    _check_rate_limit,
    _generate_code,
    _mask_email,
    _store_code_in_redis,
)

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])


def _reset_key(email: str) -> str:
    return f"auth:reset:{email.lower()}"


def _fail_key(email: str) -> str:
    return f"auth:fail:{email.lower()}"


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(body: ForgotPasswordRequest) -> Any:
    """Send a password reset verification code via email."""
    email = body.email.lower().strip()
    r = get_redis()

    rate_key = f"auth:forgot:{email}"
    if not await _check_rate_limit(r, rate_key, 3, 60):
        raise error_response(ErrorCode.RATE_LIMITED, detail="操作过于频繁，请稍后重试")

    user = await get_user_by_email(email)
    if user:
        code = _generate_code()
        await _store_code_in_redis(r, _reset_key(email), code, 900)
        subject, html = build_reset_email(code)
        await send_email(email, subject, html)
        logger.info("Reset code sent: %s", _mask_email(email))

    return MessageResponse(message="如果该邮箱已注册，将收到重置验证码")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(body: ResetPasswordRequest) -> Any:
    """Reset a user's password using a verification code."""
    email = body.email.lower().strip()
    code = body.code.strip()
    new_password = body.new_password
    r = get_redis()

    stored = await r.get(_reset_key(email))
    if stored is None:
        raise error_response(ErrorCode.INVALID_REQUEST, detail="验证码已过期，请重新获取")

    attempts_key = f"auth:reset:attempts:{email}"
    attempts = await r.incr(attempts_key)
    if attempts == 1:
        await r.expire(attempts_key, 900)
    if attempts > 3:
        await r.delete(_reset_key(email))
        raise error_response(ErrorCode.INVALID_REQUEST, detail="验证码已过期，请重新获取")

    stored_code = stored.decode() if isinstance(stored, bytes) else stored
    if not hmac.compare_digest(stored_code, code):
        raise error_response(ErrorCode.INVALID_REQUEST, detail="验证码错误")

    pwd_error = validate_password(new_password)
    if pwd_error:
        raise error_response(ErrorCode.INVALID_REQUEST, detail=pwd_error)

    user = await get_user_by_email(email)
    if user is None:
        raise error_response(ErrorCode.INVALID_REQUEST, detail="验证码已过期，请重新获取")

    if bcrypt.checkpw(new_password.encode(), user.password_hash.encode()):
        raise error_response(ErrorCode.INVALID_REQUEST, detail="新密码不能与旧密码相同")

    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt(rounds=12)).decode()
    await update_password(user.id, new_hash)
    await revoke_all_user_tokens(user.id)

    await r.delete(_reset_key(email))
    await r.delete(attempts_key)
    await r.delete(_fail_key(email))

    subject, html = build_password_changed_email()
    await send_email(email, subject, html)

    logger.info("Password reset: %s", _mask_email(email))
    return MessageResponse(message="密码已重置，请重新登录")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    """Change the current user's password after verifying the old one.

    Per-user rate limit (5/min) — a stolen session must not allow unlimited
    password-change attempts (OWASP A07).
    """
    r = get_redis()
    rate_key = f"auth:change-pwd:{current_user.id}"
    if not await _check_rate_limit(r, rate_key, 5, 60):
        raise error_response(ErrorCode.RATE_LIMITED, detail="操作过于频繁，请稍后重试")

    user = await get_user_by_id(current_user.id)
    if user is None:
        raise error_response(ErrorCode.AUTH_USER_NOT_FOUND, detail="用户不存在")

    if not bcrypt.checkpw(body.old_password.encode(), user.password_hash.encode()):
        raise error_response(ErrorCode.AUTH_UNAUTHORIZED, detail="原密码错误")

    if bcrypt.checkpw(body.new_password.encode(), user.password_hash.encode()):
        raise error_response(ErrorCode.INVALID_REQUEST, detail="新密码不能与旧密码相同")

    pwd_error = validate_password(body.new_password)
    if pwd_error:
        raise error_response(ErrorCode.INVALID_REQUEST, detail=pwd_error)

    new_hash = bcrypt.hashpw(body.new_password.encode(), bcrypt.gensalt(rounds=12)).decode()
    await update_password(user.id, new_hash)
    await revoke_all_user_tokens(user.id)

    subject, html = build_password_changed_email()
    await send_email(user.email, subject, html)

    logger.info("Password changed: user=%s", current_user.id)
    return MessageResponse(message="密码已修改，请重新登录")
