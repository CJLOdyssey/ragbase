"""Asset repository tests (unit, in-memory sqlite)."""

import pytest
from repository.assets import (
    create_asset,
    delete_asset,
    get_asset,
    get_asset_for_user,
    increment_asset_usage,
    list_assets_by_user,
    set_asset_index_result,
    update_asset_name,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_asset_crud_roundtrip() -> None:
    asset = await create_asset("u1", "brand.md", "document", 42, "/tmp/assets/brand.md")
    assert asset.id
    assert asset.source == "upload"
    assert asset.source_ref is None
    fetched = await get_asset(asset.id)
    assert fetched is not None and fetched.name == "brand.md"
    assert [a.id for a in await list_assets_by_user("u1")] == [asset.id]
    await increment_asset_usage(asset.id)
    await set_asset_index_result(asset.id, True, None)
    updated = await get_asset(asset.id)
    assert updated is not None and updated.usage_count == 1 and updated.indexed is True
    path = await delete_asset(asset.id)
    assert path == "/tmp/assets/brand.md"
    assert await get_asset(asset.id) is None


@pytest.mark.asyncio
async def test_set_asset_index_result_persists_error() -> None:
    """Failure persists the reason; a later success clears it."""
    asset = await create_asset("u1", "broken.pdf", "document", 10, "/tmp/x.pdf")
    await set_asset_index_result(asset.id, False, "startxref not found")
    failed = await get_asset(asset.id)
    assert failed is not None
    assert failed.indexed is False
    assert failed.index_error == "startxref not found"

    await set_asset_index_result(asset.id, True, None)
    ok = await get_asset(asset.id)
    assert ok is not None
    assert ok.indexed is True
    assert ok.index_error is None


@pytest.mark.asyncio
async def test_create_asset_with_url_source() -> None:
    asset = await create_asset(
        "u1",
        "remote.md",
        "document",
        42,
        "/tmp/assets/remote.md",
        source="url",
        source_ref="https://example.com/doc.md",
    )
    assert asset.source == "url"
    assert asset.source_ref == "https://example.com/doc.md"
    fetched = await get_asset(asset.id)
    assert fetched is not None and fetched.source == "url"
    assert fetched.source_ref == "https://example.com/doc.md"


@pytest.mark.asyncio
async def test_get_asset_for_user_scoped() -> None:
    asset = await create_asset("u1", "brand.md", "document", 42, "/tmp/assets/brand.md")
    assert await get_asset_for_user(asset.id, "u1") is not None
    assert await get_asset_for_user(asset.id, "u2") is None
    assert await get_asset_for_user("no-such-asset", "u1") is None


@pytest.mark.asyncio
async def test_update_asset_name_owner_only() -> None:
    asset = await create_asset("u1", "old.md", "document", 42, "/tmp/assets/old.md")

    renamed = await update_asset_name(asset.id, "u1", "new.md")
    assert renamed is not None and renamed.name == "new.md"

    assert await update_asset_name(asset.id, "u2", "hijack.md") is None
    assert await update_asset_name("no-such-asset", "u1", "x.md") is None

    fetched = await get_asset(asset.id)
    assert fetched is not None and fetched.name == "new.md"
