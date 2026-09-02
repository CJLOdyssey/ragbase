"""GET /api/assets surfaces the persisted index failure state (indexError).

Index failures used to live only in Redis progress keys (10-min TTL), so a
failed asset degraded to "unindexed" in the UI. The failure reason is now a
persistent column and must round-trip through the list endpoint.
"""

import pytest
from core.infra.database import AssetDB, get_session_factory
from fastapi.testclient import TestClient


async def _add_asset(asset_id: str, name: str, **extra: object) -> None:
    factory = get_session_factory()
    async with factory() as session:
        session.add(
            AssetDB(
                id=asset_id,
                user_id="admin-login",
                name=name,
                asset_type="document",
                size_bytes=47,
                storage_path=f"/tmp/{name}",
                **extra,  # type: ignore[arg-type]
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_list_assets_returns_index_error(client: TestClient):
    await _add_asset(
        "a-err",
        "hello.pdf",
        indexed=False,
        index_error="startxref not found",
    )
    resp = client.get("/api/assets")
    assert resp.status_code == 200
    items = {a["id"]: a for a in resp.json()}
    assert items["a-err"]["indexed"] is False
    assert items["a-err"]["indexError"] == "startxref not found"


@pytest.mark.asyncio
async def test_list_assets_without_failure_has_null_index_error(client: TestClient):
    await _add_asset("a-ok", "ok.pdf", indexed=True)
    resp = client.get("/api/assets")
    assert resp.status_code == 200
    items = {a["id"]: a for a in resp.json()}
    assert items["a-ok"]["indexed"] is True
    assert items["a-ok"]["indexError"] is None
