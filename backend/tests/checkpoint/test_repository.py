"""Integration tests for backend/checkpoint/repository.py.

Uses a real in-memory SQLite database — no mocks.
"""

import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from unittest.mock import patch

from checkpoint.models import AgentCheckpoint, CheckpointDB
from checkpoint.repository import (
    save_checkpoint,
    load_latest_checkpoint,
    list_checkpoints,
)
from core.base import Base


@pytest.fixture
async def db_session_factory():
    """Set up an in-memory SQLite engine, create tables, patch get_session_factory."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)

    with patch(
        "checkpoint.repository.get_session_factory",
        return_value=factory,
    ):
        yield factory

    await engine.dispose()


@pytest.fixture
def make_checkpoint():
    """Factory fixture to create AgentCheckpoint instances with defaults."""

    def _make(
        session_id: str = "sess-1",
        run_id: str | None = "run-1",
        step_index: int = 0,
        system_prompt: str = "",
        user_input: str = "",
        messages: list[dict[str, object]] | None = None,
        react_steps: list[dict[str, object]] | None = None,
    ) -> AgentCheckpoint:
        return AgentCheckpoint(
            session_id=session_id,
            run_id=run_id,
            step_index=step_index,
            system_prompt=system_prompt,
            user_input=user_input,
            messages=messages or [],
            react_steps=react_steps or [],
        )

    return _make


class TestSaveCheckpoint:
    async def test_saves_and_returns_id(self, db_session_factory, make_checkpoint):
        cp = make_checkpoint(session_id="sess-save", step_index=0)
        cp_id = await save_checkpoint(cp)

        assert cp_id is not None
        assert isinstance(cp_id, str)
        assert len(cp_id) > 0

    async def test_saved_data_is_queryable(self, db_session_factory, make_checkpoint):
        cp = make_checkpoint(session_id="sess-q", step_index=3, run_id="run-x")
        cp_id = await save_checkpoint(cp)

        factory = db_session_factory
        async with factory() as session:
            from sqlalchemy import select

            stmt = select(CheckpointDB).where(CheckpointDB.id == cp_id)
            result = await session.execute(stmt)
            row = result.scalar_one()

            assert row.session_id == "sess-q"
            assert row.run_id == "run-x"
            assert row.step_index == 3

    async def test_multiple_saves_increment_rows(self, db_session_factory, make_checkpoint):
        await save_checkpoint(make_checkpoint(session_id="sess-multi", step_index=0))
        await save_checkpoint(make_checkpoint(session_id="sess-multi", step_index=1))
        await save_checkpoint(make_checkpoint(session_id="sess-multi", step_index=2))

        factory = db_session_factory
        async with factory() as session:
            from sqlalchemy import func, select

            stmt = select(func.count()).select_from(CheckpointDB).where(
                CheckpointDB.session_id == "sess-multi"
            )
            result = await session.execute(stmt)
            assert result.scalar() == 3

    async def test_agent_state_is_valid_json(self, db_session_factory, make_checkpoint):
        cp = make_checkpoint(
            session_id="sess-json",
            step_index=1,
            system_prompt="You are helpful",
            user_input="Hello",
            messages=[{"role": "user", "content": "Hi"}],
        )
        cp_id = await save_checkpoint(cp)

        factory = db_session_factory
        async with factory() as session:
            from sqlalchemy import select

            stmt = select(CheckpointDB).where(CheckpointDB.id == cp_id)
            result = await session.execute(stmt)
            row = result.scalar_one()

            restored = AgentCheckpoint.from_json(row.agent_state)
            assert restored.system_prompt == "You are helpful"
            assert restored.user_input == "Hello"
            assert restored.messages == [{"role": "user", "content": "Hi"}]


class TestLoadLatestCheckpoint:
    async def test_returns_none_when_no_checkpoints(self, db_session_factory):
        result = await load_latest_checkpoint("nonexistent-session")
        assert result is None

    async def test_returns_single_checkpoint(self, db_session_factory, make_checkpoint):
        cp = make_checkpoint(session_id="sess-load", step_index=5)
        await save_checkpoint(cp)

        result = await load_latest_checkpoint("sess-load")
        assert result is not None
        assert result.session_id == "sess-load"
        assert result.step_index == 5

    async def test_returns_most_recent(self, db_session_factory, make_checkpoint):
        await save_checkpoint(make_checkpoint(session_id="sess-recent", step_index=1))
        await asyncio.sleep(0.01)
        await save_checkpoint(make_checkpoint(session_id="sess-recent", step_index=5))
        await asyncio.sleep(0.01)
        await save_checkpoint(make_checkpoint(session_id="sess-recent", step_index=10))

        result = await load_latest_checkpoint("sess-recent")
        assert result is not None
        assert result.step_index == 10

    async def test_does_not_cross_session_boundary(self, db_session_factory, make_checkpoint):
        await save_checkpoint(make_checkpoint(session_id="sess-a", step_index=100))
        await save_checkpoint(make_checkpoint(session_id="sess-b", step_index=1))

        result = await load_latest_checkpoint("sess-b")
        assert result is not None
        assert result.step_index == 1
        assert result.session_id == "sess-b"


class TestListCheckpoints:
    async def test_empty_session_returns_empty_list(self, db_session_factory):
        result = await list_checkpoints("empty-session")
        assert result == []

    async def test_returns_all_ordered_by_created_at(self, db_session_factory, make_checkpoint):
        for i in [3, 1, 5, 2, 4]:
            await save_checkpoint(make_checkpoint(session_id="sess-list", step_index=i))
            await asyncio.sleep(0.01)

        result = await list_checkpoints("sess-list")
        assert len(result) == 5
        steps = [c.step_index for c in result]
        assert steps == [3, 1, 5, 2, 4]

    async def test_does_not_mix_sessions(self, db_session_factory, make_checkpoint):
        await save_checkpoint(make_checkpoint(session_id="s1", step_index=1))
        await save_checkpoint(make_checkpoint(session_id="s2", step_index=10))
        await save_checkpoint(make_checkpoint(session_id="s1", step_index=2))

        result = await list_checkpoints("s1")
        assert len(result) == 2
        assert all(c.session_id == "s1" for c in result)

    async def test_preserves_full_state(self, db_session_factory, make_checkpoint):
        cp = make_checkpoint(
            session_id="sess-full",
            step_index=7,
            run_id="run-full",
            system_prompt="test prompt",
            user_input="test input",
            messages=[{"role": "assistant", "content": "reply"}],
            react_steps=[{"tool": "search", "result": "found"}],
        )
        await save_checkpoint(cp)

        result = await list_checkpoints("sess-full")
        assert len(result) == 1
        restored = result[0]
        assert restored.session_id == "sess-full"
        assert restored.run_id == "run-full"
        assert restored.step_index == 7
        assert restored.system_prompt == "test prompt"
        assert restored.user_input == "test input"
        assert restored.messages == [{"role": "assistant", "content": "reply"}]
        assert restored.react_steps == [{"tool": "search", "result": "found"}]


class TestUnicodeHandling:
    async def test_save_and_load_chinese_characters(self, db_session_factory, make_checkpoint):
        cp = make_checkpoint(
            session_id="sess-unicode",
            step_index=1,
            system_prompt="你是一个有帮助的助手",
            user_input="你好，请帮我写一段代码",
            messages=[{"role": "user", "content": "这是一个测试消息"}],
        )
        cp_id = await save_checkpoint(cp)

        result = await load_latest_checkpoint("sess-unicode")
        assert result is not None
        assert result.system_prompt == "你是一个有帮助的助手"
        assert result.user_input == "你好，请帮我写一段代码"
        assert result.messages == [{"role": "user", "content": "这是一个测试消息"}]

    async def test_unicode_in_list(self, db_session_factory, make_checkpoint):
        prompts = ["你好世界", "こんにちは", "🌍🎉", "Ünïcödé"]
        for i, p in enumerate(prompts):
            await save_checkpoint(
                make_checkpoint(session_id="sess-uni-list", step_index=i, system_prompt=p)
            )

        result = await list_checkpoints("sess-uni-list")
        assert len(result) == 4
        restored_prompts = [c.system_prompt for c in result]
        assert restored_prompts == prompts

    async def test_unicode_roundtrip_via_json(self, db_session_factory, make_checkpoint):
        cp = make_checkpoint(
            session_id="sess-roundtrip",
            step_index=0,
            system_prompt="中文系统提示",
            user_input="中文用户输入",
        )
        await save_checkpoint(cp)

        loaded = await load_latest_checkpoint("sess-roundtrip")
        json_str = loaded.to_json()
        restored = AgentCheckpoint.from_json(json_str)
        assert restored.system_prompt == "中文系统提示"
        assert restored.user_input == "中文用户输入"
