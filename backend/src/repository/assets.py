"""Asset repository — user-level asset library CRUD."""

from core.infra.database import AssetDB, get_session_factory
from sqlalchemy import select


async def create_asset(
    user_id: str,
    name: str,
    asset_type: str,
    size_bytes: int,
    storage_path: str,
) -> AssetDB:
    asset = AssetDB(
        user_id=user_id,
        name=name,
        asset_type=asset_type,
        size_bytes=size_bytes,
        storage_path=storage_path,
    )
    factory = get_session_factory()
    async with factory() as session:
        session.add(asset)
        await session.commit()
    return asset


async def get_asset(asset_id: str) -> AssetDB | None:
    factory = get_session_factory()
    async with factory() as session:
        return await session.get(AssetDB, asset_id)


async def list_assets_by_user(user_id: str) -> list[AssetDB]:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(AssetDB).where(AssetDB.user_id == user_id).order_by(AssetDB.created_at.desc())
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
    factory = get_session_factory()
    async with factory() as session:
        asset = await session.get(AssetDB, asset_id)
        if asset is not None:
            asset.usage_count += 1
            await session.commit()


async def set_asset_indexed(asset_id: str, indexed: bool) -> None:
    factory = get_session_factory()
    async with factory() as session:
        asset = await session.get(AssetDB, asset_id)
        if asset is not None:
            asset.indexed = indexed
            await session.commit()
