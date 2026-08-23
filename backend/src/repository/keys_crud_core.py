"""API key CRUD — encrypt, store, list, update, delete user API keys."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.infra.database import UserApiKey, get_session_factory
from core.infra.key_vault import decrypt_api_key, encrypt_api_key, mask_api_key
from sqlalchemy import select


async def create_api_key(
    user_id: str,
    provider: str,
    capabilities: list[str] | None = None,
    label: str = "",
    plaintext_key: str = "",
    base_url: str | None = None,
    models: list[str] | None = None,
    model_types: dict[str, str] | None = None,
    is_default: bool = False,
) -> UserApiKey:
    """Save a new API key — encrypts before storage, returns the created key."""
    factory = get_session_factory()
    async with factory() as session:
        # If set as default, clear other defaults for this user
        if is_default:
            result = await session.execute(
                select(UserApiKey).where(
                    UserApiKey.user_id == user_id,
                    UserApiKey.is_default.is_(True),
                )
            )
            for row in result.scalars().all():
                row.is_default = False

        encrypted = encrypt_api_key(plaintext_key)
        obj = UserApiKey(
            id=str(uuid4()),
            user_id=user_id,
            provider=provider,
            capabilities=capabilities if capabilities is not None else ["llm"],
            label=label,
            encrypted_key=encrypted,
            base_url=base_url,
            models=",".join(models) if models else "",
            model_types=model_types,
            is_active=True,
            is_default=is_default,
        )
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj


async def get_api_keys(
    user_id: str,
    fallback_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """List a user's API keys — keys are MASKED, never returned raw.

    Falls back to 'anonymous' user's keys when the current user has none,
    so new browsers can use pre-configured keys without re-entering.

    ``fallback_ids``: additional user IDs to search (e.g. X-User-ID from before login),
    so keys created under a client-generated anonymous ID remain visible after
    the user authenticates.
    """
    factory = get_session_factory()
    async with factory() as session:
        rows: list[UserApiKey] = []
        seen_ids: set[str] = set()
        # Search candidate IDs in priority order, deduplicating by key id.
        for cid in [user_id] + (fallback_ids or []):
            if not cid:
                continue
            stmt = (
                select(UserApiKey)
                .where(UserApiKey.user_id == cid)
                .order_by(UserApiKey.created_at)
            )
            result = await session.execute(stmt)
            for r in result.scalars().all():
                if r.id not in seen_ids:
                    rows.append(r)
                    seen_ids.add(r.id)

        # Ultimate fallback: anonymous user's keys (pre-configured defaults)
        if not rows and user_id != "anonymous":
            stmt = (
                select(UserApiKey)
                .where(UserApiKey.user_id == "anonymous")
                .order_by(UserApiKey.created_at)
            )
            result = await session.execute(stmt)
            rows = list(result.scalars().all())

        results = []
        for r in rows:
            try:
                key_masked = mask_api_key(decrypt_api_key(r.encrypted_key))
            except Exception:
                key_masked = "**** (解密失败，请重新添加)"
            results.append(
                {
                    "id": r.id,
                    "provider": r.provider,
                    "capabilities": list(r.capabilities or []),
                    "model_types": r.model_types,
                    "label": r.label,
                    "key_masked": key_masked,
                    "base_url": r.base_url,
                    "models": [m.strip() for m in r.models.split(",") if m.strip()]
                    if r.models
                    else [],
                    "is_active": r.is_active,
                    "is_default": r.is_default,
                    "last_used_at": r.last_used_at.isoformat() if r.last_used_at else None,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
            )
        return results


async def get_api_key_for_use(key_id: str, user_id: str) -> dict[str, Any] | None:
    """Fetch a decrypted API key for actual use (not masked).

    Args:
        key_id: The UUID of the key to retrieve.
        user_id: The owning user ID.

    Returns:
        A dict with provider, api_key (plaintext), base_url, and models,
        or None if the key is not found or inactive.

    """
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(UserApiKey).where(
            UserApiKey.id == key_id,
            UserApiKey.user_id == user_id,
            UserApiKey.is_active.is_(True),
        )
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()

        if row is None and user_id != "anonymous":
            stmt = select(UserApiKey).where(
                UserApiKey.id == key_id,
                UserApiKey.user_id == "anonymous",
                UserApiKey.is_active.is_(True),
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()

        if not row:
            return None

        row.last_used_at = datetime.now(UTC)
        await session.commit()

        return {
            "id": row.id,
            "provider": row.provider,
            "capabilities": list(row.capabilities or []),
            "model_types": row.model_types,
            "api_key": decrypt_api_key(row.encrypted_key),
            "base_url": row.base_url,
            "models": [m.strip() for m in row.models.split(",") if m.strip()] if row.models else [],
        }


async def update_api_key(
    key_id: str,
    user_id: str,
    label: str | None = None,
    plaintext_key: str | None = None,
    base_url: str | None = None,
    models: list[str] | None = None,
    is_active: bool | None = None,
    is_default: bool | None = None,
    capabilities: list[str] | None = None,
    model_types: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Update an API key configuration."""
    factory = get_session_factory()
    async with factory() as session:
        row = await session.get(UserApiKey, key_id)
        if row is None:
            return None
        owner_match = row.user_id == user_id
        anonymous_fallback = user_id != "anonymous" and row.user_id == "anonymous"
        if not owner_match and not anonymous_fallback:
            return None

        if label is not None:
            row.label = label
        if plaintext_key is not None:
            row.encrypted_key = encrypt_api_key(plaintext_key)
        if base_url is not None:
            row.base_url = base_url
        if models is not None:
            row.models = ",".join(models)
        if capabilities is not None:
            row.capabilities = capabilities
        if model_types is not None:
            row.model_types = model_types
        if is_active is not None:
            row.is_active = is_active
        if is_default is not None:
            row.is_default = is_default
            if is_default:
                # Clear other defaults
                result = await session.execute(
                    select(UserApiKey).where(
                        UserApiKey.user_id == user_id,
                        UserApiKey.is_default.is_(True),
                        UserApiKey.id != key_id,
                    )
                )
                for other in result.scalars().all():
                    other.is_default = False

        row.updated_at = datetime.now(UTC)
        await session.commit()

        return {
            "id": row.id,
            "label": row.label,
            "provider": row.provider,
            "capabilities": list(row.capabilities or []),
            "model_types": row.model_types,
            "key_masked": mask_api_key(decrypt_api_key(row.encrypted_key)),
            "is_active": row.is_active,
            "is_default": row.is_default,
        }


async def delete_api_key(key_id: str, user_id: str) -> bool:
    """Delete an API key. Returns False if not found or not owned by user."""
    factory = get_session_factory()
    async with factory() as session:
        row = await session.get(UserApiKey, key_id)
        if row is None:
            return False
        owner_match = row.user_id == user_id
        anonymous_fallback = user_id != "anonymous" and row.user_id == "anonymous"
        if not owner_match and not anonymous_fallback:
            return False
        await session.delete(row)
        await session.commit()
        return True
