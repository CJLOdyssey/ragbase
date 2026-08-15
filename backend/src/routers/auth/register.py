"""Registration, email verification, and resend endpoints."""

from typing import Any

import bcrypt
from auth.password_policy import validate_password
from broker import get_redis
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from fastapi import APIRouter, Request, Response
from repository.auth import create_user, get_user_by_email, mark_user_verified
from services.email_service import build_verification_email, send_email

from .schemas import (
    AuthResponse,
    EmailHintResponse,
    MessageResponse,
    RegisterRequest,
    SendRegisterCodeRequest,
    VerifyRequest,
    _check_rate_limit,
    _client_ip,
    _create_auth_response,
    _generate_code,
    _mask_email,
    _set_access_token_cookie,
    _set_refresh_token_cookie,
    _store_code_in_redis,
)

logger = get_logger(__name__)

router = APIRouter(tags=["auth"])


def _verify_key(email: str) -> str:
    return f"auth:verify:{email.lower()}"


@router.post("/send-register-code", status_code=200, response_model=EmailHintResponse)
async def send_register_code(body: SendRegisterCodeRequest, request: Request) -> Any:
    """Send an email verification code for registration."""
    email = body.email.lower().strip()
    r = get_redis()

    ip = _client_ip(request)
    rate_key = f"auth:send-register-code:ip:{ip}"
    if not await _check_rate_limit(r, rate_key, 3, 60):
        raise error_response(ErrorCode.RATE_LIMITED, detail="操作过于频繁，请稍后重试")

    existing = await get_user_by_email(email)
    if existing:
        raise error_response(ErrorCode.AUTH_EMAIL_EXISTS, detail="该邮箱已注册")

    code = _generate_code()
    verify_key = _verify_key(email)
    await _store_code_in_redis(r, verify_key, code, 300)

    subject, html = build_verification_email(code)
    await send_email(email, subject, html)

    email_hint = _mask_email(email)
    logger.info("Register code sent: %s", email_hint)
    return EmailHintResponse(
        message=f"验证码已发送到邮箱 {email_hint}",
        email_hint=email_hint,
    )


@router.post("/register", status_code=201, response_model=AuthResponse)
async def register(body: RegisterRequest, request: Request, response: Response) -> Any:
    """Register a new user account with email verification."""
    email = body.email.lower().strip()
    code = body.code.strip()
    password = body.password
    r = get_redis()

    ip = _client_ip(request)
    rate_key = f"auth:register:ip:{ip}"
    if not await _check_rate_limit(r, rate_key, 3, 60):
        raise error_response(ErrorCode.RATE_LIMITED, detail="操作过于频繁，请稍后重试")

    stored = await r.get(_verify_key(email))
    if stored is None:
        raise error_response(ErrorCode.INVALID_REQUEST, detail="验证码已过期，请重新获取验证码")

    attempts_key = f"auth:register:attempts:{email}"
    attempts = await r.incr(attempts_key)
    if attempts == 1:
        await r.expire(attempts_key, 300)
    if attempts > 3:
        await r.delete(_verify_key(email))
        raise error_response(ErrorCode.INVALID_REQUEST, detail="验证码已过期，请重新获取验证码")

    stored_code = stored.decode() if isinstance(stored, bytes) else stored
    if stored_code != code:
        raise error_response(ErrorCode.INVALID_REQUEST, detail="验证码错误")

    pwd_error = validate_password(password)
    if pwd_error:
        raise error_response(ErrorCode.INVALID_REQUEST, detail=pwd_error)

    existing = await get_user_by_email(email)
    if existing:
        raise error_response(ErrorCode.AUTH_EMAIL_EXISTS, detail="该邮箱已注册")

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()
    user = await create_user(email=email, password_hash=password_hash, is_verified=True)

    await r.delete(_verify_key(email))
    await r.delete(attempts_key)

    logger.info("User registered and verified: %s", _mask_email(email))
    auth_resp = await _create_auth_response(user.id, user.email, user.username)
    _set_access_token_cookie(response, auth_resp.access_token, secure=request.url.scheme == "https")
    _set_refresh_token_cookie(response, auth_resp.refresh_token, secure=request.url.scheme == "https")
    return auth_resp.model_copy(update={"refresh_token": ""})


@router.post("/verify", response_model=AuthResponse)
async def verify(body: VerifyRequest, request: Request, response: Response) -> Any:
    """Verify an email address with a verification code."""
    email = body.email.lower().strip()
    code = body.code.strip()
    r = get_redis()

    ip = _client_ip(request)
    rate_key = f"auth:verify:ip:{ip}"
    if not await _check_rate_limit(r, rate_key, 5, 60):
        raise error_response(ErrorCode.RATE_LIMITED, detail="操作过于频繁，请稍后重试")

    stored = await r.get(_verify_key(email))
    if stored is None:
        raise error_response(ErrorCode.INVALID_REQUEST, detail="验证码已过期，请重新获取")

    attempts_key = f"auth:verify:attempts:{email}"
    attempts = await r.incr(attempts_key)
    if attempts == 1:
        await r.expire(attempts_key, 300)
    if attempts > 3:
        await r.delete(_verify_key(email))
        raise error_response(ErrorCode.INVALID_REQUEST, detail="验证码已过期，请重新获取")

    stored_code = stored.decode() if isinstance(stored, bytes) else stored
    if stored_code != code:
        raise error_response(ErrorCode.INVALID_REQUEST, detail="验证码错误")

    await r.delete(_verify_key(email))
    await r.delete(attempts_key)

    user = await get_user_by_email(email)
    if user is None:
        raise error_response(ErrorCode.INVALID_REQUEST, detail="用户不存在")
    if user.is_verified:
        raise error_response(ErrorCode.INVALID_REQUEST, detail="该邮箱已验证，请直接登录")

    await mark_user_verified(user.id)
    logger.info("Email verified: %s", _mask_email(email))

    auth_resp = await _create_auth_response(user.id, user.email, user.username)
    _set_access_token_cookie(response, auth_resp.access_token, secure=request.url.scheme == "https")
    _set_refresh_token_cookie(response, auth_resp.refresh_token, secure=request.url.scheme == "https")
    return auth_resp.model_copy(update={"refresh_token": ""})


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(body: SendRegisterCodeRequest) -> Any:
    """Resend an email verification code."""
    email = body.email.lower().strip()
    r = get_redis()

    rate_key = f"auth:resend:{email}"
    if not await _check_rate_limit(r, rate_key, 1, 60):
        raise error_response(
            ErrorCode.RATE_LIMITED,
            detail="请 60 秒后再试",
        )

    user = await get_user_by_email(email)
    if user and not user.is_verified:
        code = _generate_code()
        await _store_code_in_redis(r, _verify_key(email), code, 300)
        subject, html = build_verification_email(code)
        await send_email(email, subject, html)
        logger.info("Verification resent: %s", _mask_email(email))

    return MessageResponse(message=f"验证码已发送到邮箱 {_mask_email(email)}")
