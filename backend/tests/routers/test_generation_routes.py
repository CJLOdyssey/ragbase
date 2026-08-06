"""Generation / assets / compose-templates route tests."""

import asyncio

import pytest

pytestmark = pytest.mark.unit


def test_list_compose_templates(client) -> None:  # noqa: ANN001
    from core.infra.database import ComposeTemplateDB, get_session_factory

    async def _seed() -> None:
        factory = get_session_factory()
        async with factory() as session:
            session.add(
                ComposeTemplateDB(id="square", name="square", layout_json={"ratio": "1:1"})
            )
            await session.commit()

    asyncio.run(_seed())
    resp = client.get("/api/compose-templates")
    assert resp.status_code == 200
    assert any(t["id"] == "square" for t in resp.json())


def test_create_generation_rejects_empty_topic(client) -> None:  # noqa: ANN001
    resp = client.post("/api/generations", json={"contentType": "generic", "topic": ""})
    assert resp.status_code == 400


def test_create_generation_success(client, monkeypatch) -> None:  # noqa: ANN001
    from importlib import import_module

    gen_mod = import_module("services.generation_service")

    async def _fake_create(**kwargs):  # noqa: ANN002
        from repository.run_repo import create_run

        run_id = await create_run(kwargs["topic"], content_type=kwargs["content_type"])
        return {"run_id": run_id, "session_id": None, "status": "pending"}

    monkeypatch.setattr(gen_mod.generation_service, "create_generation", _fake_create)
    resp = client.post(
        "/api/generations",
        json={"contentType": "xiaohongshu", "topic": "AI 写作", "generationMode": "generate"},
        headers={"X-User-ID": "u1"},
    )
    assert resp.status_code == 200
    assert resp.json()["run_id"]


def test_assets_crud_flow(client) -> None:  # noqa: ANN001
    from core.infra.database import AssetDB, get_session_factory

    async def _seed() -> None:
        factory = get_session_factory()
        async with factory() as session:
            session.add(
                AssetDB(
                    user_id="u1",
                    name="brand.md",
                    asset_type="document",
                    storage_path="/tmp/b.md",
                )
            )
            await session.commit()

    asyncio.run(_seed())
    resp = client.get("/api/assets", headers={"X-User-ID": "u1"})
    assert resp.status_code == 200
    assets = resp.json()
    assert len(assets) == 1 and assets[0]["name"] == "brand.md"


def test_delete_asset_denied_for_foreign_owner(client) -> None:  # noqa: ANN001
    from core.infra.database import AssetDB, get_session_factory
    from sqlalchemy import select

    async def _seed() -> str:
        factory = get_session_factory()
        async with factory() as session:
            asset = AssetDB(
                user_id="u2",
                name="secret.md",
                asset_type="document",
                storage_path="/tmp/secret.md",
            )
            session.add(asset)
            await session.commit()
            return asset.id

    async def _count() -> int:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(AssetDB).where(AssetDB.id == asset_id)
            )
            return len(list(result.scalars().all()))

    asset_id = asyncio.run(_seed())
    resp = client.delete(f"/api/assets/{asset_id}", headers={"X-User-ID": "u1"})
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "ASSET_001"
    assert asyncio.run(_count()) == 1


def test_compose_bogus_run_returns_run_not_found(client) -> None:  # noqa: ANN001
    resp = client.post(
        "/api/generations/bogus/compose",
        json={"templateId": "square"},
        headers={"X-User-ID": "u1"},
    )
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "RUN_001"


def test_variations_bogus_run_returns_run_not_found(client) -> None:  # noqa: ANN001
    resp = client.post("/api/generations/bogus/variations", headers={"X-User-ID": "u1"})
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "RUN_001"
