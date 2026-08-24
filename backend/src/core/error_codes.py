"""Structured error code system.

Format: ``{MODULE}_{3_DIGIT_NUMBER}`` (e.g. ``TEAM_001``, ``AGENT_002``).

Usage::

    from core.error_codes import ErrorCode, error_response

    # Raises an HTTPException with structured JSON body:
    raise error_response(ErrorCode.TEAM_001, detail="'MyTeam' already exists")
    raise error_response(ErrorCode.AGENT_NOT_FOUND, detail="Agent not found")
"""

from enum import StrEnum

from fastapi import HTTPException
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_410_GONE,
    HTTP_413_CONTENT_TOO_LARGE,
    HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
)


class ErrorCode(StrEnum):
    """Structured error codes used across the application.

    Naming convention: ``{MODULE}_{MEANING}``.
    ``_001`` = not-found, ``_002`` = duplicate/exists, ``_003`` = constraint,
    ``_004`` = forbidden, ``_005`` = creation-failed, ``_006`` = generation-failed.
    """

    # ── Agent ────────────────────────────────────────────────────────
    AGENT_NOT_FOUND = "AGENT_001"
    AGENT_DUPLICATE = "AGENT_002"
    AGENT_LAST_APPROVER = "AGENT_003"
    AGENT_LAST_ACTIVE = "AGENT_004"
    AGENT_CREATE_FAILED = "AGENT_005"

    # ── Prompt ──────────────────────────────────────────────────────
    PROMPT_NOT_FOUND = "PROMPT_001"
    PROMPT_DUPLICATE = "PROMPT_002"

    # ── Tool ─────────────────────────────────────────────────────────
    TOOL_NOT_FOUND = "TOOL_001"
    TOOL_GENERATE_FAILED = "TOOL_002"

    # ── MCP ──────────────────────────────────────────────────────────
    MCP_NOT_FOUND = "MCP_001"

    # ── Skill ────────────────────────────────────────────────────────
    SKILL_NOT_FOUND = "SKILL_001"
    SKILL_GENERATE_FAILED = "SKILL_002"

    # ── Team ─────────────────────────────────────────────────────────
    TEAM_CONFLICT = "TEAM_001"
    TEAM_NOT_FOUND = "TEAM_002"
    TEAM_MEMBER_NOT_FOUND = "TEAM_003"

    # ── Key ──────────────────────────────────────────────────────────
    KEY_NOT_FOUND = "KEY_001"
    KEY_INVALID = "KEY_002"

    # ── Asset ────────────────────────────────────────────────────────
    ASSET_NOT_FOUND = "ASSET_001"

    # ── Compose ──────────────────────────────────────────────────────
    TEMPLATE_NOT_FOUND = "COMPOSE_001"

    # ── Generation ───────────────────────────────────────────────────
    GENERATION_LIMIT = "GEN_001"

    # ── Session ──────────────────────────────────────────────────────
    SESSION_NOT_FOUND = "SESSION_001"
    SESSION_FORBIDDEN = "SESSION_002"

    # ── Attachment ──────────────────────────────────────────────────
    ATTACHMENT_NOT_FOUND = "ATTACHMENT_001"
    ATTACHMENT_TOO_LARGE = "ATTACHMENT_002"
    ATTACHMENT_TYPE_INVALID = "ATTACHMENT_003"
    ATTACHMENT_FILE_MISSING = "ATTACHMENT_004"

    # ── Version ─────────────────────────────────────────────────────
    VERSION_NOT_FOUND = "VERSION_001"

    # ── Command ─────────────────────────────────────────────────────
    COMMAND_NOT_FOUND = "COMMAND_001"

    # ── Workflow ────────────────────────────────────────────────────
    WORKFLOW_NOT_FOUND = "WORKFLOW_001"

    # ── System Team ─────────────────────────────────────────────────
    SYSTEM_TEAM_NOT_FOUND = "SYSTEM_TEAM_001"

    # ── Auth ─────────────────────────────────────────────────────────
    AUTH_UNAUTHORIZED = "AUTH_001"
    AUTH_INSUFFICIENT_ROLE = "AUTH_002"
    AUTH_TOKEN_EXPIRED = "AUTH_003"
    AUTH_EMAIL_EXISTS = "AUTH_004"
    AUTH_USER_NOT_FOUND = "AUTH_005"
    AUTH_ACCOUNT_LOCKED = "AUTH_006"
    AUTH_EMAIL_NOT_VERIFIED = "AUTH_007"
    AUTH_ACCOUNT_DISABLED = "AUTH_008"

    # ── Rate Limiting ────────────────────────────────────────────────
    RATE_LIMITED = "RATE_001"

    # ── Memory ───────────────────────────────────────────────────────
    MEMORY_NOT_FOUND = "MEMORY_001"

    # ── Run ─────────────────────────────────────────────────────────
    RUN_NOT_FOUND = "RUN_001"

    # ── Monitoring / review queue ───────────────────────────────────
    REVIEW_NOT_FOUND = "REVIEW_001"

    # ── RAG chunks ───────────────────────────────────────────────────
    CHUNK_NOT_FOUND = "CHUNK_001"

    # ── General ──────────────────────────────────────────────────────
    INTERNAL_ERROR = "GENERAL_001"
    INVALID_REQUEST = "GENERAL_002"


_STATUS_MAP: dict[ErrorCode, int] = {
    # 400
    ErrorCode.CHUNK_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.INVALID_REQUEST: HTTP_400_BAD_REQUEST,
    ErrorCode.AGENT_LAST_APPROVER: HTTP_400_BAD_REQUEST,
    ErrorCode.AGENT_LAST_ACTIVE: HTTP_400_BAD_REQUEST,
    ErrorCode.KEY_INVALID: HTTP_400_BAD_REQUEST,
    # 401
    ErrorCode.AUTH_UNAUTHORIZED: HTTP_401_UNAUTHORIZED,
    ErrorCode.AUTH_TOKEN_EXPIRED: HTTP_401_UNAUTHORIZED,
    # 403
    ErrorCode.AUTH_INSUFFICIENT_ROLE: HTTP_403_FORBIDDEN,
    ErrorCode.AUTH_EMAIL_NOT_VERIFIED: HTTP_403_FORBIDDEN,
    ErrorCode.AUTH_ACCOUNT_DISABLED: HTTP_403_FORBIDDEN,
    ErrorCode.SESSION_FORBIDDEN: HTTP_403_FORBIDDEN,
    # 404
    ErrorCode.AGENT_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.PROMPT_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.TOOL_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.MCP_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.SKILL_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.TEAM_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.TEAM_MEMBER_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.KEY_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.SESSION_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.ATTACHMENT_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.VERSION_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.COMMAND_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.WORKFLOW_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.SYSTEM_TEAM_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.RUN_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.REVIEW_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.MEMORY_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.AUTH_USER_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.ASSET_NOT_FOUND: HTTP_404_NOT_FOUND,
    ErrorCode.TEMPLATE_NOT_FOUND: HTTP_404_NOT_FOUND,
    # 429
    ErrorCode.GENERATION_LIMIT: HTTP_429_TOO_MANY_REQUESTS,
    ErrorCode.RATE_LIMITED: HTTP_429_TOO_MANY_REQUESTS,
    # 409
    ErrorCode.TEAM_CONFLICT: HTTP_409_CONFLICT,
    ErrorCode.AGENT_DUPLICATE: HTTP_409_CONFLICT,
    ErrorCode.PROMPT_DUPLICATE: HTTP_409_CONFLICT,
    ErrorCode.AUTH_EMAIL_EXISTS: HTTP_409_CONFLICT,
    # 410
    ErrorCode.ATTACHMENT_FILE_MISSING: HTTP_410_GONE,
    # 413
    ErrorCode.ATTACHMENT_TOO_LARGE: HTTP_413_CONTENT_TOO_LARGE,
    # 415
    ErrorCode.ATTACHMENT_TYPE_INVALID: HTTP_415_UNSUPPORTED_MEDIA_TYPE,
    # 423
    ErrorCode.AUTH_ACCOUNT_LOCKED: 423,
    # 500
    ErrorCode.INTERNAL_ERROR: HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.AGENT_CREATE_FAILED: HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.TOOL_GENERATE_FAILED: HTTP_500_INTERNAL_SERVER_ERROR,
    ErrorCode.SKILL_GENERATE_FAILED: HTTP_500_INTERNAL_SERVER_ERROR,
}


def error_response(code: ErrorCode, detail: str | None = None) -> HTTPException:
    """Return an ``HTTPException`` with structured JSON body.

    Usage::

        raise error_response(ErrorCode.TEAM_CONFLICT, detail="'MyTeam' already exists")
    """
    status = _STATUS_MAP.get(code, HTTP_500_INTERNAL_SERVER_ERROR)
    message = detail or code.name.replace("_", " ").title()
    return HTTPException(
        status_code=status,
        detail={
            "error": {"code": code.value, "message": message},
        },
    )
