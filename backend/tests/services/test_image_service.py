"""ImageService provider dispatch tests."""

import base64
from importlib import import_module
from pathlib import Path

import httpx
import pytest
from core.base import Base
from core.infra.database import get_session_factory
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

img_mod = import_module("services.image_service")

pytestmark = pytest.mark.unit

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


async def _mem_db(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_async_engine(
        "sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    get_session_factory()
    monkeypatch.setattr(
        "core.infra.database._async_session_factory",
        async_sessionmaker(engine, expire_on_commit=False),
    )


async def _tmp_img_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    img_dir = tmp_path / "images"
    img_dir.mkdir(parents=True)
    monkeypatch.setattr(img_mod, "IMAGE_DIR", img_dir)


def _mock_key(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _key(key_id: str, user_id: str) -> dict[str, str | None]:
        return {"api_key": "sk-test", "base_url": None}

    monkeypatch.setattr(img_mod, "get_api_key_for_use", _key)


def _handler_openai(request: httpx.Request) -> httpx.Response:
    if "/images/generations" in request.url.path:
        return httpx.Response(
            200,
            json={"data": [{"b64_json": base64.b64encode(_PNG).decode()}]},
        )
    return httpx.Response(404)


def _handler_dashscope(request: httpx.Request) -> httpx.Response:
    if request.url.host == "cdn.example.com":
        return httpx.Response(200, content=_PNG, headers={"content-type": "image/png"})
    if request.url.path.endswith("/api/v1/tasks/task-1"):
        return httpx.Response(
            200,
            json={"output": {"task_status": "SUCCEEDED", "results": [{"url": "https://cdn.example.com/1.png"}]}},
        )
    if request.url.path.endswith("/image-synthesis"):
        return httpx.Response(200, json={"output": {"task_id": "task-1"}})
    return httpx.Response(404)


def _handler_stability(request: httpx.Request) -> httpx.Response:
    if "/stable-image/generate/" in request.url.path:
        return httpx.Response(200, content=_PNG, headers={"content-type": "image/png"})
    return httpx.Response(404)


@pytest.mark.asyncio
async def test_openai_image_generation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    await _mem_db(monkeypatch)
    await _tmp_img_dir(monkeypatch, tmp_path)
    _mock_key(monkeypatch)
    monkeypatch.setattr(img_mod, "_new_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(_handler_openai)))
    from repository.run_repo import create_run
    run_id = await create_run("主题")
    result = await img_mod.image_service.generate(
        run_id, "一只猫", provider="openai", key_id="k1", user_id="u1"
    )
    assert result.storage_path.endswith(".png")


@pytest.mark.asyncio
async def test_dashscope_image_generation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    await _mem_db(monkeypatch)
    await _tmp_img_dir(monkeypatch, tmp_path)
    _mock_key(monkeypatch)
    monkeypatch.setattr(img_mod, "_new_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(_handler_dashscope)))
    from repository.run_repo import create_run
    run_id = await create_run("主题")
    result = await img_mod.image_service.generate(
        run_id, "一只猫", provider="dashscope", key_id="k1", user_id="u1"
    )
    assert result.storage_path.endswith(".png")


@pytest.mark.asyncio
async def test_stability_image_generation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    await _mem_db(monkeypatch)
    await _tmp_img_dir(monkeypatch, tmp_path)
    _mock_key(monkeypatch)
    monkeypatch.setattr(img_mod, "_new_client", lambda: httpx.AsyncClient(transport=httpx.MockTransport(_handler_stability)))
    from repository.run_repo import create_run
    run_id = await create_run("主题")
    result = await img_mod.image_service.generate(
        run_id, "一只猫", provider="stability", key_id="k1", user_id="u1"
    )
    assert result.storage_path.endswith(".png")


@pytest.mark.asyncio
async def test_unsupported_provider_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    await _mem_db(monkeypatch)
    await _tmp_img_dir(monkeypatch, tmp_path)
    from repository.run_repo import create_run
    run_id = await create_run("主题")
    with pytest.raises(ValueError):
        await img_mod.image_service.generate(run_id, "x", provider="nope", user_id="u1")
