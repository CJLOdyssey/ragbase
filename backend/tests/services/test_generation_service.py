"""GenerationService orchestration tests."""

import asyncio
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


async def _run_for_user(user_id: str, topic: str = "主题", **kwargs: object) -> str:
    from repository import create_session
    from repository.run_repo import create_run

    sess = await create_session(title=topic[:64], user_id=user_id, kind="normal")
    return await create_run(topic, session_id=sess.id, **kwargs)  # type: ignore[arg-type]


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
    assert result["status"] == "pending"
    run_id = result["run_id"]
    assert run_id
    assert result["session_id"]

    gen = None
    for _ in range(40):
        gen = await generation_service.get_generation(run_id, "u1")
        if gen and gen["status"] == "completed":
            break
        await asyncio.sleep(0.05)
    assert gen is not None
    assert gen["status"] == "completed"
    assert gen["result"]["title"] == "AI 写作入门"
    assert gen["result"]["body_markdown"] == "## 正文"


@pytest.mark.asyncio
async def test_create_generation_invalid_content_type(monkeypatch: pytest.MonkeyPatch) -> None:
    await _mem_session_factory(monkeypatch)
    with pytest.raises(ValueError):
        await generation_service.create_generation(
            user_id="u1", content_type="bogus", topic="x"
        )


@pytest.mark.asyncio
async def test_create_generation_invalid_mode() -> None:
    with pytest.raises(ValueError, match="generation_mode"):
        await generation_service.create_generation(
            user_id="u1", content_type="xiaohongshu", topic="x", generation_mode="bogus"
        )


@pytest.mark.asyncio
async def test_create_generation_extra_requirements_too_long() -> None:
    with pytest.raises(ValueError, match="附加要求"):
        await generation_service.create_generation(
            user_id="u1", content_type="xiaohongshu", topic="x", additional_requirements="长" * 2001
        )


@pytest.mark.asyncio
async def test_continue_generation_missing_run(monkeypatch: pytest.MonkeyPatch) -> None:
    await _mem_session_factory(monkeypatch)
    with pytest.raises(ValueError, match="run 不存在"):
        await generation_service.continue_generation("run-nope", "补充", "u1")


@pytest.mark.asyncio
async def test_create_variations_missing_run(monkeypatch: pytest.MonkeyPatch) -> None:
    await _mem_session_factory(monkeypatch)
    with pytest.raises(ValueError, match="run 不存在"):
        await generation_service.create_variations("run-nope", "u1")


@pytest.mark.asyncio
async def test_compose_card_missing_run(monkeypatch: pytest.MonkeyPatch) -> None:
    await _mem_session_factory(monkeypatch)
    with pytest.raises(ValueError, match="run 不存在"):
        await generation_service.compose_card("run-nope", "square", title="t", summary="s", user_id="u1")


@pytest.mark.asyncio
async def test_get_generation_returns_none_for_foreign_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _mem_session_factory(monkeypatch)
    run_id = await _run_for_user("u2")
    assert await generation_service.get_generation(run_id, "u1") is None
    assert await generation_service.get_generation(run_id, "u2") is not None


@pytest.mark.asyncio
async def test_build_asset_context(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    async def _fake_get_asset(asset_id: str, user_id: str) -> SimpleNamespace | None:
        if asset_id == "foreign":
            return None
        return SimpleNamespace(name="logo", storage_path="s3://bucket/logo.png")

    async def _fake_increment(asset_id: str) -> None:
        return None

    async def _no_rag(user_id: str, query: str) -> str:
        return ""

    monkeypatch.setattr(gen_mod, "get_asset_for_user", _fake_get_asset)
    monkeypatch.setattr(gen_mod, "increment_asset_usage", _fake_increment)
    monkeypatch.setattr(generation_service, "_retrieve_rag_context", _no_rag)

    context = await generation_service._build_asset_context("u1", ["a1", "foreign"], "主题")
    assert "logo" in context
    assert "s3://bucket/logo.png" in context


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

    run_id = await _run_for_user("u1", content_type="generic")

    result = await generation_service.compose_card(
        run_id, "square", title="标题", summary="摘要", user_id="u1"
    )
    assert result["template"]["id"] == "square"
    assert result["fields"]["title"] == "标题"
    assert result["fields"]["summary"] == "摘要"


@pytest.mark.asyncio
async def test_compose_card_unknown_template(monkeypatch: pytest.MonkeyPatch) -> None:
    await _mem_session_factory(monkeypatch)
    run_id = await _run_for_user("u1")
    with pytest.raises(ValueError):
        await generation_service.compose_card(run_id, "nope", title="t", summary="s", user_id="u1")


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


@pytest.mark.asyncio
async def test_create_variations_limit_via_parent_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    await _mem_session_factory(monkeypatch)

    parent_id = await _run_for_user("u1", content_type="xiaohongshu")
    from repository.run_repo import create_run

    for _ in range(3):
        await create_run("变体", parent_run_id=parent_id)

    monkeypatch.setattr(
        generation_service, "create_generation",
        lambda **kwargs: {"run_id": "new", "status": "pending", "session_id": "s"},
    )
    with pytest.raises(ValueError, match="最多生成"):
        await generation_service.create_variations(parent_id, "u1")


@pytest.mark.asyncio
async def test_create_variations_passes_parent_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    await _mem_session_factory(monkeypatch)

    parent_id = await _run_for_user("u1", content_type="xiaohongshu")

    calls: list[dict] = []

    async def _fake_generation(**kwargs: object) -> dict:
        calls.append(kwargs)
        return {"run_id": "new", "status": "pending", "session_id": "s"}

    monkeypatch.setattr(generation_service, "create_generation", _fake_generation)
    result = await generation_service.create_variations(parent_id, "u1")
    assert result["run_id"] == "new"
    assert len(calls) == 1
    assert calls[0]["parent_run_id"] == parent_id
    assert calls[0]["generation_mode"] == "variations"


@pytest.mark.asyncio
async def test_continue_generation_passes_content(monkeypatch: pytest.MonkeyPatch) -> None:
    await _mem_session_factory(monkeypatch)

    run_id = await _run_for_user("u1", content_type="xiaohongshu", topic="主题")

    calls: list[dict] = []

    async def _fake_generation(**kwargs: object) -> dict:
        calls.append(kwargs)
        return {"run_id": "rewritten", "status": "pending", "session_id": "s"}

    monkeypatch.setattr(generation_service, "create_generation", _fake_generation)
    await generation_service.continue_generation(run_id, "补充要求", "u1")
    assert len(calls) == 1
    assert calls[0]["additional_requirements"] == "补充要求"
    assert calls[0]["generation_mode"] == "rewrite"
