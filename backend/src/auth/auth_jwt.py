"""JWT token creation and verification via PyJWT (HS256).

Keeps a legacy decode branch for the pre-PyJWT simplified HMAC token format
``base64(user_id:ts:sig[:16])`` so previously issued tokens still validate.
"""

import base64
import hashlib
import hmac
import os
import time
from typing import Any

import jwt
from core.infra.logging_config import get_logger

logger = get_logger(__name__)

AUTH_SECRET = os.environ.get("AUTH_SECRET", "")


def _base64url_decode(data: str) -> bytes:
    """Decode base64url-encoded string with padding fix."""
    rem = len(data) % 4
    if rem:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data)


def decode_jwt(token: str, secret: str) -> dict[str, Any] | None:
    """Decode and verify a JWT token.

    Returns the payload dict if valid, None otherwise.
    Standard tokens are verified with PyJWT (HS256, header alg enforced).
    Simplified legacy tokens fall back to the old HMAC verification.
    """
    if not secret:
        return None

    parts = token.split(".")
    if len(parts) == 3:
        try:
            return jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"require": ["exp"], "verify_exp": True},
            )
        except Exception as exc:
            # Expected outcome for attacker-supplied tokens — log the reason
            # without a stack trace to avoid log flooding on auth probing.
            logger.warning("JWT decode rejected: %s", exc)
            return None

    # Legacy simplified token: base64url(user_id:ts:sig[:16])
    if len(parts) == 1:
        try:
            raw = _base64url_decode(token).decode()
            user_id, ts_str, provided_sig = raw.rsplit(":", 2)
            expected = hmac.new(
                secret.encode(),
                f"{user_id}:{ts_str}".encode(),
                hashlib.sha256,
            ).hexdigest()[:16]
            if not hmac.compare_digest(provided_sig, expected):
                return None
            if int(ts_str) < int(time.time()) - 86400:
                return None
            return {"sub": user_id, "iat": int(ts_str)}
        except (ValueError, UnicodeDecodeError):
            return None

    return None


def create_token(user_id: str, secret: str, ttl: int = 86400) -> str:
    """Create an HS256 JWT token for the given user_id."""
    if not secret:
        # PyJWT >= 2.12 raises InvalidKeyError on empty key; guard like decode_jwt
        # so test environments without AUTH_SECRET don't explode.
        raise ValueError("AUTH_SECRET is empty — cannot create token")
    now = int(time.time())
    return jwt.encode(
        {"sub": user_id, "iat": now, "exp": now + ttl},
        secret,
        algorithm="HS256",
    )
