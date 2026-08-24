"""API key resolution — model/config lookups across user and anonymous keys."""

from datetime import UTC, datetime
from typing import Any

from core.infra.database import UserApiKey, get_session_factory
from core.infra.key_vault import decrypt_api_key
from core.infra.logging_config import get_logger
from sqlalchemy import select

logger = get_logger(__name__)


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


async def get_embedding_config(
    preferred_model: str | None = None,
) -> dict[str, str | None] | None:
    """Resolve the embedding endpoint: {api_key, base_url, model}.

    With ``preferred_model`` (a KB's bound embedding model), an active
    embedding-capability key declaring exactly that model wins — keeping
    query/document vectors in the KB's own space. Falls back to the global
    heuristic: an active embedding-capability key whose models list names an
    embedding model (e.g. bge-m3 / *-embedding-*); else the oldest
    embedding-capability key with the legacy DashScope endpoint.
    """
    from core.infra.database import UserApiKey
    from core.infra.key_vault import decrypt_api_key

    async def _embedding_key_rows() -> list[Any]:
        """Active embedding-capability keys, oldest first."""
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
        return list(rows)

    if preferred_model:
        for row in await _embedding_key_rows():
            declared = [x.strip() for x in (row.models or "").split(",")]
            if preferred_model in declared:
                return {
                    "api_key": decrypt_api_key(row.encrypted_key),
                    "base_url": row.base_url,
                    "model": preferred_model,
                }
        logger.warning(
            "Preferred embedding model %r not declared on any active "
            "embedding-capability key — falling back to global resolution",
            preferred_model,
        )

    rows = await _embedding_key_rows()
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
