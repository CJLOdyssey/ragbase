"""Asset repository — user-level asset library CRUD."""

from datetime import UTC, datetime

from core.infra.database import AssetDB, get_session_factory
from sqlalchemy import asc, desc, select


async def create_asset(
    user_id: str,
    name: str,
    asset_type: str,
    size_bytes: int,
    storage_path: str,
    source: str = "upload",
    source_ref: str | None = None,
) -> AssetDB:
    """Create and persist an asset row; returns the created asset."""
    asset = AssetDB(
        user_id=user_id,
        name=name,
        asset_type=asset_type,
        size_bytes=size_bytes,
        storage_path=storage_path,
        source=source,
        source_ref=source_ref,
    )
    factory = get_session_factory()
    async with factory() as session:
        session.add(asset)
        await session.commit()
    return asset


async def get_asset(asset_id: str) -> AssetDB | None:
    """Fetch an asset by ID, or None if it does not exist."""
    factory = get_session_factory()
    async with factory() as session:
        return await session.get(AssetDB, asset_id)


async def get_asset_for_user(asset_id: str, user_id: str) -> AssetDB | None:
    """Fetch an asset only if it belongs to user_id. None otherwise."""
    factory = get_session_factory()
    async with factory() as session:
        asset = await session.get(AssetDB, asset_id)
        if asset is None or asset.user_id != user_id:
            return None
        return asset


async def update_asset_name(asset_id: str, user_id: str, name: str) -> AssetDB | None:
    """Rename an asset only if it belongs to user_id. None otherwise."""
    factory = get_session_factory()
    async with factory() as session:
        asset = await session.get(AssetDB, asset_id)
        if asset is None or asset.user_id != user_id:
            return None
        asset.name = name
        await session.commit()
        return asset


async def list_assets_by_user(
    user_id: str,
    sort_by: str | None = None,
    order: str | None = None,
) -> list[AssetDB]:
    """List a user's assets.

    默认：最新一次点击优先，其次点击次数从高到低（均 desc，全栈对齐）。
    支持显式 sort_by: usage_count | updated_at/last_used | name | size | created_at。
    """
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(AssetDB).where(AssetDB.user_id == user_id)
        # 显式排序（供前端/外部调用）
        sort_map = {
            "usage_count": AssetDB.usage_count,
            "usage": AssetDB.usage_count,
            "updated_at": AssetDB.updated_at,
            "updated": AssetDB.updated_at,
            "last_used": AssetDB.updated_at,
            "lastUsed": AssetDB.updated_at,
            "name": AssetDB.name,
            "size": AssetDB.size_bytes,
            "created_at": AssetDB.created_at,
        }
        if sort_by in sort_map:
            col = sort_map[sort_by]
            direction = desc if (order or "desc").lower() == "desc" else asc
            stmt = stmt.order_by(direction(col))
        else:
            # 默认：最新一次点击优先，其次点击次数从高到低
            stmt = stmt.order_by(desc(AssetDB.updated_at), desc(AssetDB.usage_count), desc(AssetDB.created_at))
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def list_asset_ids_by_kb(kb_id: str, user_id: str) -> list[str]:
    """List asset IDs belonging to a knowledge base, scoped to the owner."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(AssetDB.id).where(
                AssetDB.knowledge_base_id == kb_id,
                AssetDB.user_id == user_id,
            )
        )
        return list(result.scalars().all())


async def delete_asset(asset_id: str) -> str | None:
    """Delete an asset row. Returns storage_path if found, None otherwise."""
    factory = get_session_factory()
    async with factory() as session:
        asset = await session.get(AssetDB, asset_id)
        if asset is None:
            return None
        storage_path = asset.storage_path
        await session.delete(asset)
        await session.commit()
        return storage_path


async def increment_asset_usage(asset_id: str) -> None:
    """Increment an asset's usage_count and refresh last-click time (updated_at)."""
    factory = get_session_factory()
    async with factory() as session:
        asset = await session.get(AssetDB, asset_id)
        if asset is not None:
            asset.usage_count += 1
            asset.updated_at = datetime.now(UTC)
            await session.commit()


async def set_asset_indexed(asset_id: str, indexed: bool) -> None:
    """Set whether an asset has been indexed into the vector store."""
    factory = get_session_factory()
    async with factory() as session:
        asset = await session.get(AssetDB, asset_id)
        if asset is not None:
            asset.indexed = indexed
            await session.commit()


async def update_asset_tags(
    asset_id: str, user_id: str, tags: list[str]
) -> AssetDB | None:
    """Replace an asset's curated tags (owner-scoped); returns updated asset."""
    factory = get_session_factory()
    async with factory() as session:
        asset = await session.get(AssetDB, asset_id)
        if asset is None or asset.user_id != user_id:
            return None
        asset.tags = tags
        await session.commit()
        return asset
