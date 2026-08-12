"""API key CRUD repository — encrypt, store, list, and manage user API keys."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.infra.database import KeyUsageLog, UserApiKey, get_session_factory
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
        # Collect unique candidate IDs
        candidates = {user_id}
        if fallback_ids:
            candidates.update(fbid for fbid in fallback_ids if fbid and fbid != user_id)

        rows: list[UserApiKey] = []
        seen_ids: set[str] = set()
        # Search candidates in priority order, deduplicating by key id.
        # "anonymous" is a real key namespace (guest-configured + pre-configured
        # defaults) — AUTH_ENABLED resolves every unauthenticated request to it,
        # so skipping it here would make guest chats and guest-configured keys
        # permanently invisible.  ponytail: just query it like any other id.
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


async def _resolve_key_row(session: Any, user_id: str) -> Any:
    stmt = select(UserApiKey).where(
        UserApiKey.user_id == user_id,
        UserApiKey.is_active.is_(True),
        UserApiKey.is_default.is_(True),
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row:
        return row

    stmt = (
        select(UserApiKey)
        .where(
            UserApiKey.user_id == user_id,
            UserApiKey.is_active.is_(True),
        )
        .order_by(UserApiKey.created_at)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_api_key_for_model(model: str, user_id: str) -> dict[str, Any] | None:
    """Fetch an active key whose comma-separated models list contains ``model``.

    Prefers the user's own keys, falling back to ``anonymous`` keys. Model
    matching is exact per entry — substring matches are rejected so that a
    ``deepseek-v4-flash`` key never serves a ``deepseek-v4-flash-x`` request.
    """
    if not model:
        return None

    factory = get_session_factory()
    async with factory() as session:
        row = await _match_model_in_session(session, user_id, model)
        if row is None and user_id != "anonymous":
            row = await _match_model_in_session(session, "anonymous", model)
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


async def _match_model_in_session(session: Any, user_id: str, model: str) -> Any:
    from sqlalchemy import func

    stmt = (
        select(UserApiKey)
        .where(
            UserApiKey.user_id == user_id,
            UserApiKey.is_active.is_(True),
            func.concat(",", UserApiKey.models, ",").like(f"%,{model},%"),
        )
        .order_by(UserApiKey.created_at)
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_default_api_key(user_id: str) -> dict[str, Any] | None:
    """Fetch the user's default API key, with anonymous and system-wide fallbacks.

    Falls back chain: user default → anonymous → any active default in system.
    """
    factory = get_session_factory()
    async with factory() as session:
        row = await _resolve_key_row(session, user_id)
        if row is None and user_id != "anonymous":
            row = await _resolve_key_row(session, "anonymous")

        # Guest fallback: if the guest has no key and anonymous has none,
        # look for any active default key in the system.
        # This covers the case where a merge moved all guest keys to a real user.
        if row is None and user_id.startswith("u_"):
            stmt = (
                select(UserApiKey)
                .where(
                    UserApiKey.is_active.is_(True),
                    UserApiKey.is_default.is_(True),
                )
                .limit(1)
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


def _pick_embedding_model(models: str) -> str | None:
    """Pick an embedding-capable model from a key's comma-joined models list.

    bge-m3 is preferred (deterministic 1024-dim output) over other
    embedding-named models, regardless of list order.
    """
    if not models:
        return None
    candidates = [x.strip() for x in models.split(",")]
    for m in candidates:
        if "bge-m3" in m.lower():
            return m
    for m in candidates:
        lowered = m.lower()
        if "embedding" in lowered or "bge-" in lowered:
            return m
    return None


def _pick_rerank_model(models: str) -> str | None:
    """Pick a reranker model from a key's comma-joined models list.

    bge-reranker-v2-m3 is preferred over other rerank-named models.
    """
    if not models:
        return None
    candidates = [x.strip() for x in models.split(",")]
    for m in candidates:
        if "bge-reranker-v2-m3" in m.lower():
            return m
    for m in candidates:
        if "rerank" in m.lower():
            return m
    return None


async def get_rerank_config() -> dict[str, str] | None:
    """Resolve the reranker endpoint: {api_key, base_url, model}.

    Prefers an active key whose models list names a reranker; None when no
    key declares one (rerank then stays disabled).
    """
    from core.infra.database import UserApiKey
    from core.infra.key_vault import decrypt_api_key

    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(UserApiKey)
            .where(UserApiKey.is_active.is_(True))
            .order_by(UserApiKey.created_at)
        )
        rows = (await session.execute(stmt)).scalars().all()

    for row in rows:
        model = _pick_rerank_model(row.models)
        if model and row.base_url:
            return {
                "api_key": decrypt_api_key(row.encrypted_key),
                "base_url": row.base_url,
                "model": model,
            }
    return None


async def get_embedding_config() -> dict[str, str | None] | None:
    """Resolve the embedding endpoint: {api_key, base_url, model}.

    Prefers an active key whose models list names an embedding model (e.g.
    bge-m3 / *-embedding-*); falls back to the oldest embedding-capability
    key with the legacy DashScope endpoint.
    """
    from core.infra.database import UserApiKey
    from core.infra.key_vault import decrypt_api_key

    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(UserApiKey)
            .where(
                UserApiKey.is_active.is_(True),
                _capabilities_contains(session, "embedding"),
            )
            .order_by(UserApiKey.created_at)
        )
        rows = (await session.execute(stmt)).scalars().all()

    if not rows:
        return None
    for row in rows:
        model = _pick_embedding_model(row.models)
        if model:
            return {
                "api_key": decrypt_api_key(row.encrypted_key),
                "base_url": row.base_url,
                "model": model,
            }
    row = rows[0]
    # Imported lazily: keys_crud sits at the tail of rag -> core -> repository
    # import chain; a top-level import would cycle back into rag_embedding.
    from rag.rag_embedding import EMBEDDING_MODEL

    return {
        "api_key": decrypt_api_key(row.encrypted_key),
        # Keep the key's own endpoint: a key without declared embedding models
        # may still point at an OpenAI-compatible provider (e.g. SiliconFlow).
        # Only a key with no base_url at all falls back to the legacy DashScope
        # native protocol. Model comes from EMBEDDING_MODEL (env-tunable), never
        # hardcoded.
        "base_url": row.base_url,
        "model": EMBEDDING_MODEL,
    }


async def get_embedding_api_key() -> str | None:
    """Get the decrypted API key for embedding (backward-compat shim)."""
    cfg = await get_embedding_config()
    return cfg["api_key"] if cfg else None


async def get_tool_api_key(provider: str) -> str | None:
    """Get the decrypted API key for a tool provider (e.g. 'tavily')."""
    from core.infra.database import UserApiKey
    from core.infra.key_vault import decrypt_api_key

    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(UserApiKey)
            .where(
                UserApiKey.provider == provider,
                UserApiKey.is_active.is_(True),
                _capabilities_contains(session, "tool"),
            )
            .order_by(UserApiKey.created_at)
            .limit(1)
        )
        row = (await session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return decrypt_api_key(row.encrypted_key)


def _capabilities_contains(session: Any, capability: str) -> Any:
    """Array-contains predicate: JSONB ``@>`` on postgres, ``json_each`` on sqlite.

    ``UserApiKey.capabilities`` is JSONB on postgres (``contains`` compiles to
    the ``@>`` operator) but plain JSON on sqlite (``with_variant``), where the
    ``@>`` operator does not exist — emulate "array contains value" with the
    json1 ``json_each`` table function so filtering is SQL-side on both engines.
    """
    from sqlalchemy import exists, func

    if session.get_bind().dialect.name == "postgresql":
        return UserApiKey.capabilities.contains([capability])
    elements = func.json_each(UserApiKey.capabilities).table_valued("value")
    return exists(select(elements.c.value).where(elements.c.value == capability))


async def sum_user_tokens_since(user_id: str, since: datetime) -> int:
    """Total LLM tokens consumed by a user since a timestamp (budget check).

    Queries the append-only KeyUsageLog (tokens_total per call).
    """
    from sqlalchemy import func

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(func.coalesce(func.sum(KeyUsageLog.tokens_total), 0)).where(
                KeyUsageLog.user_id == user_id,
                KeyUsageLog.created_at >= since,
            )
        )
        return int(result.scalar_one())


async def log_key_usage(
    key_id: str | None,
    user_id: str,
    run_id: str | None,
    provider: str,
    model: str,
    tokens_prompt: int = 0,
    tokens_completion: int = 0,
    duration_ms: int = 0,
    status: str = "success",
    error_message: str | None = None,
) -> Any:
    """Record an LLM call in the audit log."""
    total = tokens_prompt + tokens_completion
    factory = get_session_factory()
    async with factory() as session:
        log = KeyUsageLog(
            id=str(uuid4()),
            key_id=key_id,
            user_id=user_id,
            run_id=run_id,
            provider=provider,
            model=model,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            tokens_total=total,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
        )
        session.add(log)
        await session.commit()


async def get_key_usage_stats(user_id: str | None = None) -> dict[str, Any]:
    """Get usage statistics for API keys usage.

    If user_id is None or 'anonymous', returns stats across all users.
    """
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import func

        # Today's stats
        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        stmt_today = select(
            func.count(KeyUsageLog.id).label("requests"),
            func.sum(KeyUsageLog.tokens_total).label("tokens"),
        ).where(
            KeyUsageLog.created_at >= today_start,
            KeyUsageLog.status == "success",
        )
        if user_id and user_id != 'anonymous':
            stmt_today = stmt_today.where(KeyUsageLog.user_id == user_id)
        result_today = await session.execute(stmt_today)
        today = result_today.one()

        # Month's stats
        month_start = today_start.replace(day=1)
        stmt_month = select(
            func.count(KeyUsageLog.id).label("requests"),
            func.sum(KeyUsageLog.tokens_total).label("tokens"),
        ).where(
            KeyUsageLog.created_at >= month_start,
            KeyUsageLog.status == "success",
        )
        if user_id and user_id != 'anonymous':
            stmt_month = stmt_month.where(KeyUsageLog.user_id == user_id)
        result_month = await session.execute(stmt_month)
        month = result_month.one()

        return {
            "today_requests": today.requests or 0,
            "today_tokens": today.tokens or 0,
            "month_requests": month.requests or 0,
            "month_tokens": month.tokens or 0,
        }
