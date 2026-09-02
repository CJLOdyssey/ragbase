"""Prompts repository — CRUD for :class:`PromptDB`.

Usage::

    from repository import create_prompt, update_prompt

    prompt = await create_prompt({"name": "...", "category": "general", "content": "..."})
    updated = await update_prompt(prompt.id, {"content": "..."})  # version bumps to vX.Y.Z+1
"""

from re import fullmatch
from typing import Any

from core.infra.database import PromptDB
from sqlalchemy import desc

from repository.base import BaseRepository


class PromptRepository(BaseRepository[PromptDB]):
    model = PromptDB
    default_order = desc(PromptDB.updated_at)

    @staticmethod
    def to_dict(obj: PromptDB) -> dict[str, Any]:
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
            "created_at": obj.created_at.isoformat(),
            "updated_at": obj.updated_at.isoformat(),
        }


# module-level aliases so callers import from `repository` without instantiating
get_prompts = PromptRepository.get_all
get_prompts_as_dicts = PromptRepository.get_all_as_dicts
get_prompt = PromptRepository.get_one


async def create_prompt(data: dict[str, Any]) -> PromptDB:
    """Create a prompt and return the persisted row."""
    return await PromptRepository.create_one(data)


def _bump_version(current: str) -> str:
    """Bump a semver-style version string (vX.Y.Z → vX.Y.Z+1).

    Non-conforming inputs reset to the v1.0.1 baseline so the column always
    holds a parseable value.
    """
    match = fullmatch(r"v(\d+)\.(\d+)\.(\d+)", current.strip())
    if not match:
        return "v1.0.1"
    major, minor, patch = (int(g) for g in match.groups())
    return f"v{major}.{minor}.{patch + 1}"


async def update_prompt(entity_id: str, data: dict[str, Any]) -> PromptDB | None:
    """Update a prompt, bumping its version column. Returns None if not found."""
    existing = await PromptRepository.get_one(entity_id)
    if existing is None:
        return None
    data = {**data, "version": _bump_version(existing.version)}
    return await PromptRepository.update_one(entity_id, data)


async def delete_prompt(entity_id: str) -> bool:
    """Delete a prompt by ID. Returns True if deleted, False if not found."""
    return await PromptRepository.delete_one(entity_id)
