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


def test_list_generations_user_scoped(client) -> None:  # noqa: ANN001
    from repository.run_repo import create_run
    from repository.session_repo import create_session

    async def _seed() -> None:
        s1 = await create_session(title="s1", user_id="u1", kind="normal")
        s2 = await create_session(title="s2", user_id="u2", kind="normal")
        await create_run("甲", session_id=s1.id, content_type="wechat")
        await create_run("乙", session_id=s1.id, content_type="generic")
        await create_run("丙", session_id=s2.id, content_type="generic")

    asyncio.run(_seed())
    resp = client.get("/api/generations", headers={"X-User-ID": "u1"})
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    topics = {i["topic"] for i in items}
    assert topics == {"甲", "乙"}
    assert all(i["content_type"] in ("generic", "wechat") for i in items)

    limited = client.get("/api/generations?limit=1", headers={"X-User-ID": "u1"})
    assert len(limited.json()) == 1


def test_get_generation_denied_for_foreign_owner(client) -> None:  # noqa: ANN001
    from core.infra.database import SessionDB, get_session_factory
    from repository.run_repo import create_run

    async def _seed() -> str:
        factory = get_session_factory()
        async with factory() as session:
            session.add(SessionDB(id="s-u2", title="t", user_id="u2", kind="normal"))
            await session.commit()
        return await create_run("主题", session_id="s-u2", content_type="generic")

    run_id = asyncio.run(_seed())
    resp = client.get(f"/api/generations/{run_id}", headers={"X-User-ID": "u1"})
    assert resp.status_code == 404
    assert resp.json()["detail"]["error"]["code"] == "RUN_001"

    resp = client.get(f"/api/generations/{run_id}", headers={"X-User-ID": "u2"})
    assert resp.status_code == 200


def test_upload_asset_sanitizes_traversal_filename(client, monkeypatch, tmp_path) -> None:  # noqa: ANN001
    from pathlib import Path

    import routers.assets as assets_mod

    monkeypatch.setattr(assets_mod, "ASSET_DIR", tmp_path)

    resp = client.post(
        "/api/assets",
        files={"file": ("../../evil.png", b"\x89PNG\x0d\x0a\x1a\n", "image/png")},
        headers={"X-User-ID": "u1"},
    )
    assert resp.status_code == 201
    asset_id = resp.json()["id"]

    async def _read() -> str:
        from repository import get_asset

        asset = await get_asset(asset_id)
        assert asset is not None
        return asset.storage_path

    storage_path = asyncio.run(_read())
    assert ".." not in storage_path
    assert Path(storage_path).parent == tmp_path
    assert Path(storage_path).is_file()
