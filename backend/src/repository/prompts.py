"""Prompts repository — CRUD for :class:`PromptDB`."""

from typing import Any

from core.infra.cache import get_cache
from core.infra.database import PromptDB
from sqlalchemy import desc

from repository.base import BaseRepository

CACHE_KEY_PROMPTS = "prompts:all"


class PromptRepository(BaseRepository[PromptDB]):
    model = PromptDB
    default_order = desc(PromptDB.updated_at)

    @staticmethod
    def to_dict(obj: Any) -> dict[str, Any]:
        """Serialize a PromptDB row to a JSON-safe dict."""
        return {
            "id": obj.id,
            "name": obj.name,
            "description": obj.description,
            "category": obj.category,
            "content": obj.content,
            "model": obj.model,
            "status": obj.status,
            "version": obj.version,
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        }


async def _invalidate_prompts_cache() -> None:
    """Invalidate the prompts list cache after mutations."""
    cache = get_cache()
    await cache.delete(CACHE_KEY_PROMPTS)


async def get_cached_prompts_as_dicts() -> list[dict[str, Any]]:
    """Return all prompts as dicts, using Redis cache with 5-min TTL.

    Falls through to DB on cache miss; mutations invalidate the cache.
    """
    cache = get_cache()
    cached = await cache.get(CACHE_KEY_PROMPTS)
    if cached is not None:
        # SAFETY: cached value was stored by `PromptRepository.get_all_as_dicts()` which returns list[dict]
        from typing import cast
        return cast(list[dict[str, Any]], cached)

    result = await PromptRepository.get_all_as_dicts()
    await cache.set(CACHE_KEY_PROMPTS, result)
    return result


# module-level aliases (read-only are direct references, writes are wrapped for cache)
get_prompts = PromptRepository.get_all
get_prompts_as_dicts = PromptRepository.get_all_as_dicts
get_prompt = PromptRepository.get_one


async def create_prompt(data: dict[str, Any]) -> PromptDB:
    """Create a prompt and invalidate cache."""
    result = await PromptRepository.create_one(data)
    await _invalidate_prompts_cache()
    return result


def _bump_version(current: str) -> str:
    """Bump a semver-style version string (vX.Y.Z → vX.Y.Z+1)."""
    import re

    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", current.strip())
    if not match:
        return "v1.0.1"
    major, minor, patch = (int(g) for g in match.groups())
    return f"v{major}.{minor}.{patch + 1}"


async def update_prompt(entity_id: str, data: dict[str, Any]) -> PromptDB | None:
    """Update a prompt, bumping its version column, and invalidate cache."""
    existing = await PromptRepository.get_one(entity_id)
    if existing is None:
        return None
    data = {**data, "version": _bump_version(existing.version or "v1.0.0")}
    result = await PromptRepository.update_one(entity_id, data)
    await _invalidate_prompts_cache()
    return result


async def delete_prompt(entity_id: str) -> bool:
    """Delete a prompt and invalidate cache."""
    result = await PromptRepository.delete_one(entity_id)
    await _invalidate_prompts_cache()
    return result
