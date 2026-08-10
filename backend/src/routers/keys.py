"""Enterprise API Key management routes.

Security invariants:
  - Keys are NEVER returned in plaintext — all responses show masked versions
  - Key storage is write-only from the client perspective
  - Decryption only happens inside Celery tasks, never in API handlers
  - All key mutations are audit-logged at INFO level
"""

import asyncio
from typing import Any

from auth import get_user_id
from core.audit import log_audit
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from domain.capabilities import validate_capabilities
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field, field_validator
from repository import (
    create_api_key,
    delete_api_key,
    get_api_keys,
    get_key_usage_stats,
    test_api_key_connection,
    update_api_key,
)

logger = get_logger(__name__)
router = APIRouter(tags=["keys"])


class KeyCreateRequest(BaseModel):
    provider: str = Field(..., min_length=1, max_length=32, pattern=r"^[a-z_]+$")
    capabilities: list[str] = Field(default_factory=lambda: ["llm"])
    label: str = Field(..., min_length=1, max_length=64)
    api_key: str = Field(
        ..., min_length=1, description="Plaintext API key — encrypted before storage"
    )
    base_url: str | None = None
    models: list[str] = Field(default_factory=list)
    is_default: bool = False

    @field_validator("capabilities")
    @classmethod
    def _check_caps(cls, v: list[str]) -> list[str]:
        err = validate_capabilities(v)
        if err:
            raise ValueError(err)
        return v


class KeyUpdateRequest(BaseModel):
    capabilities: list[str] | None = Field(default=None)
    label: str | None = None
    api_key: str | None = Field(default=None, description="New plaintext key (optional)")
    base_url: str | None = None
    models: list[str] | None = None
    is_active: bool | None = None
    is_default: bool | None = None

    @field_validator("capabilities")
    @classmethod
    def _check_caps(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        err = validate_capabilities(v)
        if err:
            raise ValueError(err)
        return v


class FetchModelsRequest(BaseModel):
    api_key: str = Field(..., min_length=1)
    base_url: str | None = None
    provider: str = Field(default="custom")


class KeyResponse(BaseModel):
    id: str
    provider: str
    capabilities: list[str]
    label: str
    key_masked: str
    base_url: str | None
    models: list[str]
    is_active: bool
    is_default: bool
    last_used_at: str | None
    created_at: str | None


# ── CRUD routes ──────────────────────────────────────────────────────────────


@router.get("/api/keys", response_model=list[KeyResponse])
async def list_keys(request: Request) -> Any:
    """List all API keys for the authenticated user. Keys are MASKED."""
    user_id = get_user_id(request)
    # Include X-User-ID as fallback so keys created under a client-generated
    # anonymous ID are still visible after the user authenticates (JWT cookie).
    x_uid = str(request.headers.get("X-User-ID", ""))
    fallback_ids = [x_uid] if x_uid and x_uid != user_id else None
    try:
        keys = await get_api_keys(user_id, fallback_ids=fallback_ids)
        return [
            KeyResponse(
                id=k["id"],
                provider=k["provider"],
                capabilities=k.get("capabilities", ["llm"]),
                label=k["label"],
                key_masked=k["key_masked"],
                base_url=k["base_url"],
                models=k["models"],
                is_active=k["is_active"],
                is_default=k["is_default"],
                last_used_at=k["last_used_at"],
                created_at=k["created_at"],
            )
            for k in keys
        ]
    except Exception as e:
        logger.error("Error listing keys for user %s: %s", user_id, e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e


@router.post("/api/keys", status_code=201, response_model=KeyResponse)
async def add_key(req: KeyCreateRequest, request: Request) -> Any:
    """Save a new API key. Auto-validates connectivity and fetches available models."""
    user_id = get_user_id(request)
    logger.info(
        "Key creation requested | user=%s | provider=%s | label=%s",
        user_id,
        req.provider,
        req.label,
    )

    obj = await create_api_key(
        user_id=user_id,
        provider=req.provider,
        capabilities=req.capabilities,
        label=req.label,
        plaintext_key=req.api_key,
        base_url=req.base_url,
        models=req.models,
        is_default=req.is_default,
    )

    # Pure-embedding keys skip connectivity test and model fetch
    if set(req.capabilities) == {"embedding"}:
        from core.infra.key_vault import decrypt_api_key, mask_api_key

        return KeyResponse(
            id=obj.id,
            provider=obj.provider,
            capabilities=obj.capabilities,
            label=obj.label,
            key_masked=mask_api_key(decrypt_api_key(obj.encrypted_key)),
            base_url=obj.base_url,
            models=[],
            is_active=obj.is_active,
            is_default=obj.is_default,
            last_used_at=obj.last_used_at.isoformat() if obj.last_used_at else None,
            created_at=obj.created_at.isoformat() if obj.created_at else None,
        )

    test_result = await test_api_key_connection(obj.id, user_id)

    if not test_result.get("success"):
        logger.warning(
            "Key validation failed (non-blocking): %s",
            test_result.get("message", "connection error"),
        )
    fetched_models = test_result.get("models", []) if test_result.get("success") else []
    models_to_store = fetched_models if fetched_models else req.models

    await update_api_key(
        key_id=obj.id,
        user_id=user_id,
        models=models_to_store,
    )

    from core.infra.key_vault import decrypt_api_key, mask_api_key

    return KeyResponse(
        id=obj.id,
        provider=obj.provider,
        capabilities=obj.capabilities,
        label=obj.label,
        key_masked=mask_api_key(decrypt_api_key(obj.encrypted_key)),
        base_url=obj.base_url,
        models=models_to_store,
        is_active=obj.is_active,
        is_default=obj.is_default,
        last_used_at=obj.last_used_at.isoformat() if obj.last_used_at else None,
        created_at=obj.created_at.isoformat() if obj.created_at else None,
    )


@router.put("/api/keys/{key_id}", response_model=KeyResponse)
async def edit_key(key_id: str, req: KeyUpdateRequest, request: Request) -> Any:
    """Update an API key. Re-validates if api_key or base_url changed."""
    user_id = get_user_id(request)
    result = await update_api_key(
        key_id=key_id,
        user_id=user_id,
        capabilities=req.capabilities,
        label=req.label,
        plaintext_key=req.api_key,
        base_url=req.base_url,
        models=req.models,
        is_active=req.is_active,
        is_default=req.is_default,
    )
    if not result:
        raise error_response(ErrorCode.KEY_NOT_FOUND, detail="Key not found or access denied")

    if req.api_key or req.base_url:
        test_result = await test_api_key_connection(key_id, user_id)
        if test_result.get("success"):
            fetched_models = test_result.get("models", [])
            if fetched_models:
                await update_api_key(key_id=key_id, user_id=user_id, models=fetched_models)
                result["models"] = fetched_models

    await log_audit("create", "api_key", result["label"], "创建成功")
    return KeyResponse(
        id=result["id"],
        provider=result["provider"],
        capabilities=result.get("capabilities", ["llm"]),
        label=result["label"],
        key_masked=result["key_masked"],
        base_url=result.get("base_url"),
        models=result.get("models", []),
        is_active=result["is_active"],
        is_default=result["is_default"],
        last_used_at=result.get("last_used_at"),
        created_at=result.get("created_at"),
    )


@router.delete("/api/keys/{key_id}")
async def remove_key(key_id: str, request: Request) -> Any:
    """Delete an API key. Irreversible — the encrypted key is permanently removed."""
    user_id = get_user_id(request)
    # Get label before deletion
    keys = await get_api_keys(user_id)
    target = next((k for k in keys if k["id"] == key_id), None)
    key_label = target["label"] if target else key_id
    deleted = await delete_api_key(key_id, user_id)
    if not deleted:
        raise error_response(ErrorCode.KEY_NOT_FOUND, detail="Key not found or access denied")
    await log_audit("delete", "api_key", key_label, "删除成功")
    logger.info("Key deleted | user=%s | key_id=%s", user_id, key_id)
    return {"status": "deleted", "id": key_id}


@router.post("/api/keys/{key_id}/test")
async def test_key_connection(key_id: str, request: Request) -> Any:
    """Test connectivity for a stored key. Does NOT expose the plaintext key."""
    user_id = get_user_id(request)
    result = await test_api_key_connection(key_id, user_id)
    if result.get("success"):
        return {"success": True, "message": result.get("message", "OK")}
    return {"success": False, "message": result.get("message", "Test failed")}


@router.post("/api/keys/fetch-models")
async def fetch_models_from_provider(req: FetchModelsRequest) -> Any:
    """Fetch available models from a provider's API without saving a key."""
    from repository.keys import _test_connection_sync

    key_cfg = {
        "provider": req.provider,
        "api_key": req.api_key,
        "base_url": req.base_url,
    }
    result = await asyncio.to_thread(_test_connection_sync, key_cfg)
    if result.get("success"):
        return {
            "success": True,
            "models": result.get("models", []),
            "types": result.get("types", {}),
        }
    logger.warning("Model fetch failed (non-blocking): %s", result.get("message", "unknown"))
    return {"success": False, "models": [], "message": result.get("message", "Connection failed")}


@router.get("/api/keys/usage")
async def key_usage(request: Request) -> Any:
    """Get token usage statistics for the authenticated user."""
    user_id = get_user_id(request)
    try:
        stats = await get_key_usage_stats(user_id)
        return stats
    except Exception as e:
        logger.error("Error fetching usage for user %s: %s", user_id, e, exc_info=True)
        raise error_response(ErrorCode.INTERNAL_ERROR) from e
