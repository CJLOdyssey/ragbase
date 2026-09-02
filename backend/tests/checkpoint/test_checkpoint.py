"""Unit tests for backend/checkpoint/ (factory, models, repository)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestCheckpointerFactoryCore:
    @patch("checkpoint.factory.MemorySaver")
    def test_memory_backend(self, mock_memory):
        from checkpoint.factory import create_checkpointer

        result = create_checkpointer(backend="memory")
        mock_memory.assert_called_once()
        assert result == mock_memory.return_value

    @patch("checkpoint.factory.os.environ", {"CHECKPOINTER_BACKEND": "memory"})
    @patch("checkpoint.factory.MemorySaver")
    def test_memory_backend_from_env(self, mock_memory):
        from checkpoint.factory import create_checkpointer

        create_checkpointer()
        mock_memory.assert_called_once()

    def test_resolve_backend_defaults(self):
        from checkpoint.factory import _resolve_backend

        with patch("checkpoint.factory.os.environ", {}):
            backend, dsn = _resolve_backend(None, None)
            assert backend == "sqlite"
            assert dsn is None

    def test_resolve_backend_from_env(self):
        from checkpoint.factory import _resolve_backend

        env = {"CHECKPOINTER_BACKEND": "memory", "CHECKPOINTER_DSN": "/data/cp.db"}
        with patch("checkpoint.factory.os.environ", env):
            backend, dsn = _resolve_backend(None, None)
            assert backend == "memory"
            assert dsn == "/data/cp.db"

    def test_resolve_backend_explicit_overrides_env(self):
        from checkpoint.factory import _resolve_backend

        env = {"CHECKPOINTER_BACKEND": "memory", "CHECKPOINTER_DSN": "/data/cp.db"}
        with patch("checkpoint.factory.os.environ", env):
            backend, dsn = _resolve_backend("postgres", "pg://local")
            assert backend == "postgres"
            assert dsn == "pg://local"


class TestCheckpointDB:
    def test_orm_model_attributes(self):
        from checkpoint.models import CheckpointDB

        assert CheckpointDB.__tablename__ == "agent_checkpoints"
        cols = {c.name: c for c in CheckpointDB.__table__.columns}
        assert "id" in cols
        assert "session_id" in cols
        assert "run_id" in cols
        assert "step_index" in cols
        assert "agent_state" in cols
        assert "created_at" in cols

    def test_id_auto_generated(self):
        from checkpoint.models import CheckpointDB

        obj = CheckpointDB(session_id="sess-1", agent_state="{}", id="auto-id")
        assert obj.id is not None
        assert len(obj.id) > 0

    def test_default_step_index(self):
        from checkpoint.models import CheckpointDB

        obj = CheckpointDB(session_id="sess-1", agent_state="{}", step_index=0)
        assert obj.step_index == 0


class TestAgentCheckpoint:
    def test_dataclass_defaults(self):
        from checkpoint.models import AgentCheckpoint

        cp = AgentCheckpoint(session_id="sess-1", run_id=None, step_index=0)
        assert cp.system_prompt == ""
        assert cp.user_input == ""
        assert cp.messages == []
        assert cp.react_steps == []

    def test_to_json_roundtrip(self):
        from checkpoint.models import AgentCheckpoint

        cp = AgentCheckpoint(
            session_id="sess-1",
            run_id="run-1",
            step_index=3,
            system_prompt="You are a helpful assistant.",
            user_input="Hello",
            messages=[{"role": "user", "content": "Hi"}],
            react_steps=[{"tool": "search", "result": "ok"}],
        )
        json_str = cp.to_json()
        restored = AgentCheckpoint.from_json(json_str)
        assert restored.session_id == "sess-1"
        assert restored.run_id == "run-1"
        assert restored.step_index == 3
        assert restored.system_prompt == "You are a helpful assistant."
        assert restored.user_input == "Hello"
        assert restored.messages == [{"role": "user", "content": "Hi"}]
        assert restored.react_steps == [{"tool": "search", "result": "ok"}]

    def test_from_json_preserves_unicode(self):
        from checkpoint.models import AgentCheckpoint

        cp = AgentCheckpoint(session_id="sess-1", run_id=None, step_index=0, system_prompt="你好世界")
        json_str = cp.to_json()
        restored = AgentCheckpoint.from_json(json_str)
        assert restored.system_prompt == "你好世界"

    def test_to_json_ensure_ascii_false(self):
        from checkpoint.models import AgentCheckpoint

        cp = AgentCheckpoint(session_id="s-1", run_id=None, step_index=0, system_prompt="こんにちは")
        json_str = cp.to_json()
        assert "こんにちは" in json_str
        assert "\\u" not in json_str


@pytest.fixture
def mock_async_session():
    """AsyncSession double: sync add() + async commit/refresh/execute.

    Using a plain MagicMock for add() matters: AsyncMock makes EVERY method
    a coroutine, so the un-awaited ``session.add(obj)`` would leak a
    "coroutine was never awaited" RuntimeWarning into the test output.
    """
    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


class TestCheckpointRepository:
    @patch("checkpoint.repository.get_session_factory")
    @pytest.mark.asyncio
    async def test_save_checkpoint(self, mock_get_factory, mock_async_session):
        from checkpoint.models import AgentCheckpoint
        from checkpoint.repository import save_checkpoint

        mock_factory = MagicMock()
        mock_factory.return_value.__aenter__.return_value = mock_async_session
        mock_get_factory.return_value = mock_factory

        cp = AgentCheckpoint(session_id="sess-1", run_id="run-1", step_index=2)
        result_id = await save_checkpoint(cp)

        mock_async_session.add.assert_called_once()
        added = mock_async_session.add.call_args[0][0]
        assert added.session_id == "sess-1"
        assert added.run_id == "run-1"
        assert added.step_index == 2
        mock_async_session.commit.assert_awaited_once()
        mock_async_session.refresh.assert_awaited_once()
        assert result_id == added.id

    @patch("checkpoint.repository.get_session_factory")
    @pytest.mark.asyncio
    async def test_load_latest_checkpoint_found(self, mock_get_factory, mock_async_session):
        from checkpoint.models import AgentCheckpoint
        from checkpoint.repository import load_latest_checkpoint

        mock_factory = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock(
            agent_state=AgentCheckpoint(
                session_id="sess-1", run_id="run-1", step_index=5
            ).to_json()
        )
        mock_async_session.execute.return_value = mock_result
        mock_factory.return_value.__aenter__.return_value = mock_async_session
        mock_get_factory.return_value = mock_factory

        result = await load_latest_checkpoint("sess-1")
        assert result is not None
        assert result.session_id == "sess-1"
        assert result.step_index == 5

    @patch("checkpoint.repository.get_session_factory")
    @pytest.mark.asyncio
    async def test_load_latest_checkpoint_not_found(self, mock_get_factory, mock_async_session):
        from checkpoint.repository import load_latest_checkpoint

        mock_factory = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_async_session.execute.return_value = mock_result
        mock_factory.return_value.__aenter__.return_value = mock_async_session
        mock_get_factory.return_value = mock_factory

        result = await load_latest_checkpoint("nonexistent")
        assert result is None

    @patch("checkpoint.repository.get_session_factory")
    @pytest.mark.asyncio
    async def test_list_checkpoints(self, mock_get_factory, mock_async_session):
        from checkpoint.models import AgentCheckpoint
        from checkpoint.repository import list_checkpoints

        mock_factory = MagicMock()
        mock_result = MagicMock()

        class _ScalarResult:
            def __init__(self, items):
                self._items = items

            def __iter__(self):
                return iter(self._items)

        cp1 = MagicMock(agent_state=AgentCheckpoint(session_id="sess-1", run_id=None, step_index=0).to_json())
        cp2 = MagicMock(agent_state=AgentCheckpoint(session_id="sess-1", run_id=None, step_index=1).to_json())
        mock_result.scalars.return_value = _ScalarResult([cp1, cp2])
        mock_async_session.execute.return_value = mock_result
        mock_factory.return_value.__aenter__.return_value = mock_async_session
        mock_get_factory.return_value = mock_factory

        results = await list_checkpoints("sess-1")
        assert len(results) == 2
        assert all(c.session_id == "sess-1" for c in results)
