"""GenerationService orchestration tests."""

from importlib import import_module

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

gen_mod = import_module("services.generation_service")
from core.base import Base
from core.infra.database import get_session_factory
from services.generation_service import generation_service

pytestmark = pytest.mark.unit


async def _mem_session_factory(monkeypatch: pytest.MonkeyPatch) -> None:
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


def _mock_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _model_key(model: str, user_id: str) -> dict[str, str | None]:
        return {"api_key": "sk-test", "base_url": None}

    async def _default_key(user_id: str) -> dict[str, str | None]:
        return {"api_key": "sk-test", "base_url": None}

    monkeypatch.setattr(gen_mod, "get_api_key_for_model", _model_key)
    monkeypatch.setattr(gen_mod, "get_default_api_key", _default_key)


async def _fake_stream(url: str, headers: dict, body: dict, run_id: str, timeout: float = 300.0):
    """Fake LLM stream: emits the structured JSON body then stops."""
    payload = (
        '{"title": "AI 写作入门", "summary": "三分钟学会", '
        '"body_markdown": "## 正文", "keywords": ["AI"]}'
    )
    return payload, []


@pytest.mark.asyncio
async def test_create_generation_returns_run(monkeypatch: pytest.MonkeyPatch) -> None:
    await _mem_session_factory(monkeypatch)
    _mock_keys(monkeypatch)
    monkeypatch.setattr(
        gen_mod, "_stream_llm", _fake_stream,
    )
    result = await generation_service.create_generation(
        user_id="u1",
        content_type="xiaohongshu",
        topic="AI 写作入门",
    )
    assert result["status"] in ("pending", "completed")
    assert result["run_id"]
    assert result["session_id"]


@pytest.mark.asyncio
async def test_create_generation_invalid_content_type(monkeypatch: pytest.MonkeyPatch) -> None:
    await _mem_session_factory(monkeypatch)
    with pytest.raises(ValueError):
        await generation_service.create_generation(
            user_id="u1", content_type="bogus", topic="x"
        )


@pytest.mark.asyncio
async def test_compose_card_returns_template_and_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    await _mem_session_factory(monkeypatch)
    from orm.infra import ComposeTemplateDB

    async def _seed() -> None:
        factory = get_session_factory()
        async with factory() as session:
            session.add(
                ComposeTemplateDB(
                    id="square", name="square",
                    layout_json={"canvas": {"ratio": "1:1"}}, is_default=False,
                )
            )
            await session.commit()
    await _seed()

    from repository.run_repo import create_run
    run_id = await create_run("主题", content_type="generic")

    result = await generation_service.compose_card(
        run_id, "square", title="标题", summary="摘要"
    )
    assert result["template"]["id"] == "square"
    assert result["fields"]["title"] == "标题"
    assert result["fields"]["summary"] == "摘要"


@pytest.mark.asyncio
async def test_compose_card_unknown_template(monkeypatch: pytest.MonkeyPatch) -> None:
    await _mem_session_factory(monkeypatch)
    from repository.run_repo import create_run
    run_id = await create_run("主题")
    with pytest.raises(ValueError):
        await generation_service.compose_card(run_id, "nope", title="t", summary="s")


@pytest.mark.asyncio
async def test_count_versions_counts_snapshots(monkeypatch: pytest.MonkeyPatch) -> None:
    await _mem_session_factory(monkeypatch)
    from repository.versions import count_versions, create_version

    factory = get_session_factory()
    async with factory() as session:
        await create_version(session, "generation", "run-1", {"title": "a"})
        await create_version(session, "generation", "run-1", {"title": "b"})
        await session.commit()

    assert await count_versions("generation", "run-1") == 2
    assert await count_versions("generation", "run-nope") == 0
