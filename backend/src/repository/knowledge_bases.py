"""Knowledge base repository — multi-KB isolation CRUD."""

from typing import Any

from core.infra.database import AssetDB, KnowledgeBaseDB, get_session_factory
from sqlalchemy import func, select, update


async def create_kb(
    user_id: str,
    name: str,
    description: str = "",
    embed_model: str | None = None,
    parser_config: dict[str, Any] | None = None,
) -> KnowledgeBaseDB:
    """Create and persist a knowledge base row; returns the created KB."""
    kb = KnowledgeBaseDB(
        user_id=user_id,
        name=name,
        description=description,
        embed_model=embed_model,
        parser_config=parser_config,
    )
    factory = get_session_factory()
    async with factory() as session:
        session.add(kb)
        await session.commit()
    return kb


async def list_kbs(user_id: str) -> list[KnowledgeBaseDB]:
    """List a user's knowledge bases, newest first."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(KnowledgeBaseDB)
            .where(KnowledgeBaseDB.user_id == user_id)
            .order_by(KnowledgeBaseDB.created_at.desc())
        )
        return list(result.scalars().all())


async def count_assets_by_kb(user_id: str) -> dict[str, int]:
    """Count assets per knowledge base for a user."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(AssetDB.knowledge_base_id, func.count(AssetDB.id))
            .where(
                AssetDB.user_id == user_id,
                AssetDB.knowledge_base_id.isnot(None),
            )
            .group_by(AssetDB.knowledge_base_id)
        )
        return {kb_id: count for kb_id, count in result.all() if kb_id}


async def get_kb(kb_id: str, user_id: str) -> KnowledgeBaseDB | None:
    """Fetch a KB only if it belongs to user_id. None otherwise."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(KnowledgeBaseDB).where(
                KnowledgeBaseDB.id == kb_id,
                KnowledgeBaseDB.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()


async def delete_kb(kb_id: str, user_id: str) -> bool:
    """Delete a KB and nullify all assets' knowledge_base_id referencing it.

    Returns True if the KB was found and deleted, False otherwise.
    """
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(KnowledgeBaseDB).where(
                KnowledgeBaseDB.id == kb_id,
                KnowledgeBaseDB.user_id == user_id,
            )
        )
        kb = result.scalar_one_or_none()
        if kb is None:
            return False
        # Nullify assets referencing this KB
        await session.execute(
            update(AssetDB)
            .where(AssetDB.knowledge_base_id == kb_id)
            .values(knowledge_base_id=None)
        )
        await session.delete(kb)
        await session.commit()
        return True


async def update_kb(
    kb_id: str, user_id: str, name: str | None = None, description: str | None = None
) -> KnowledgeBaseDB | None:
    """Update a KB's name/description. Returns updated KB or None if not found."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(KnowledgeBaseDB).where(
                KnowledgeBaseDB.id == kb_id,
                KnowledgeBaseDB.user_id == user_id,
            )
        )
        kb = result.scalar_one_or_none()
        if kb is None:
            return None
        if name is not None:
            kb.name = name
        if description is not None:
            kb.description = description
        await session.commit()
        return kb


async def change_indexing_config(
    kb_id: str,
    user_id: str,
    embed_model: str | None = None,
    parser_config: dict[str, Any] | None = None,
) -> tuple[KnowledgeBaseDB | None, list[str]]:
    """Rebind a KB's indexing config and invalidate its indexed assets.

    Vectors are products of (embedding model, chunking parameters): changing
    either makes existing vectors stale, so every indexed asset of the KB is
    reset to ``indexed=False`` in the same transaction — the caller then
    purges stale chunks and requeues indexing (last-write-wins: rebinding
    again mid-rebuild is safe).

    Only the provided fields change; passing both as-is is a no-op.
    Returns (updated_kb, affected_asset_ids); (None, []) when not found.
    """
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(KnowledgeBaseDB).where(
                KnowledgeBaseDB.id == kb_id,
                KnowledgeBaseDB.user_id == user_id,
            )
        )
        kb = result.scalar_one_or_none()
        if kb is None:
            return None, []

        affected: list[str] = []
        model_changed = embed_model is not None and kb.embed_model != embed_model
        config_changed = (
            parser_config is not None and kb.parser_config != parser_config
        )
        if model_changed or config_changed:
            rows = await session.execute(
                select(AssetDB.id).where(
                    AssetDB.knowledge_base_id == kb_id,
                    AssetDB.indexed.is_(True),
                )
            )
            affected = list(rows.scalars().all())
            if affected:
                await session.execute(
                    update(AssetDB)
                    .where(AssetDB.id.in_(affected))
                    .values(indexed=False)
                )
            if model_changed:
                kb.embed_model = embed_model
            if config_changed:
                kb.parser_config = parser_config
        await session.commit()
        return kb, affected


async def change_embed_model(
    kb_id: str, user_id: str, embed_model: str
) -> tuple[KnowledgeBaseDB | None, list[str]]:
    """Backward-compatible shim — rebind only the embedding model."""
    return await change_indexing_config(kb_id, user_id, embed_model=embed_model)


async def assign_asset_to_kb(asset_id: str, kb_id: str | None, user_id: str) -> bool:
    """Assign an asset to a KB (or nullify if kb_id is None).

    Returns True if the asset was found and updated, False otherwise.
    Validates that both the asset and KB (if provided) belong to user_id.
    """
    factory = get_session_factory()
    async with factory() as session:
        # Verify asset ownership
        asset = await session.get(AssetDB, asset_id)
        if asset is None or asset.user_id != user_id:
            return False
        # If assigning to a KB, verify KB ownership
        if kb_id is not None:
            kb_result = await session.execute(
                select(KnowledgeBaseDB).where(
                    KnowledgeBaseDB.id == kb_id,
                    KnowledgeBaseDB.user_id == user_id,
                )
            )
            if kb_result.scalar_one_or_none() is None:
                return False
        asset.knowledge_base_id = kb_id
        await session.commit()
        return True
