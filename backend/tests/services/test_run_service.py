"""Unit tests for RunService — create_run / continue_run / get_run / list_runs / dispatch."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _patch_create_task():
    """Patch services.run_service.asyncio.create_task without leaking coroutines.

    The real create_task hands the coroutine to the event loop; a plain
    MagicMock never awaits it, producing "coroutine was never awaited"
    RuntimeWarnings at GC. The side effect closes the coroutine so the
    ``create_task called`` assertion still holds without the leak.
    """
    mock = MagicMock()

    def _capture(coro):
        coro.close()
        return MagicMock()

    mock.side_effect = _capture
    return patch("services.run_service.asyncio.create_task", mock)


class TestRunService:
    """Test RunService class — constructor, create_run, continue_run, error handling."""

    @pytest.mark.asyncio
    async def test_import(self):
        from services.run_service import RunService, run_service

        assert RunService is not None
        assert run_service is not None
        assert isinstance(run_service, RunService)

    @pytest.mark.asyncio
    async def test_create_run_requires_requirement(self):
        from services.run_service import RunService

        svc = RunService()
        with pytest.raises(TypeError):
            await svc.create_run()  # type: ignore[call-arg]

    @pytest.mark.asyncio
    async def test_create_run_no_api_key_raises(self):
        from services.run_service import RunService

        svc = RunService()
        with (
            patch("services.run_service.load_config") as mock_load,
            patch("services.run_service.create_session") as mock_create_sess,
            patch("services.run_service.save_message", new_callable=AsyncMock),
            patch("services.run_resolve.get_api_key_for_use") as mock_get_key,
            patch("services.run_resolve.get_api_key_for_model") as mock_get_model,
            patch("services.run_resolve.get_default_api_key") as mock_get_default,
        ):
            mock_load.return_value.model = "gpt-4"
            mock_sess = MagicMock()
            mock_sess.id = "sess-123"
            mock_create_sess.return_value = mock_sess
            mock_get_key.return_value = None
            mock_get_model.return_value = None
            mock_get_default.return_value = None

            with pytest.raises(ValueError, match="API Key"):
                await svc.create_run(
                    requirement="test requirement",
                    session_id=None,
                    user_id="user-1",
                )

    @pytest.mark.asyncio
    async def test_create_run_with_key_id_success(self):
        from services.run_service import RunService

        svc = RunService()
        with (
            patch("services.run_service.load_config") as mock_load,
            patch("services.run_service.create_session") as mock_create_sess,
            patch("services.run_service.save_message", new_callable=AsyncMock),
            patch("services.run_resolve.get_api_key_for_use") as mock_get_key,
            patch("services.run_service.buffer_run_messages") as mock_buffer,
            _patch_create_task(),
            patch("services.run_service.get_session") as mock_get_sess,
            patch("services.run_service.update_session_title"),
            patch("repository.create_run") as mock_db_create_run,
        ):
            mock_load.return_value.model = "gpt-4"
            mock_sess = MagicMock()
            mock_sess.id = "sess-456"
            mock_create_sess.return_value = mock_sess
            mock_get_key.return_value = {"api_key": "sk-test", "base_url": None}
            mock_get_sess.return_value = mock_sess
            mock_db_create_run.return_value = "run-789"
            mock_buffer.return_value = None

            result = await svc.create_run(
                requirement="hello world",
                session_id=None,
                user_id="user-1",
                key_id="key-1",
            )
            assert result["run_id"] == "run-789"
            assert result["status"] == "pending"
            assert result["session_id"] == "sess-456"

    @pytest.mark.asyncio
    async def test_create_run_with_existing_session(self):
        from services.run_service import RunService

        svc = RunService()
        with (
            patch("services.run_service.load_config") as mock_load,
            patch("services.run_service.get_session") as mock_get_sess,
            patch("services.run_resolve.get_api_key_for_use"),
            patch("services.run_resolve.get_api_key_for_model") as mock_get_model,
            patch("services.run_resolve.get_default_api_key") as mock_get_default,
            patch("services.run_service.buffer_run_messages"),
            _patch_create_task(),
            patch("services.run_service.update_session_title"),
            patch("repository.create_run") as mock_db_create_run,
        ):
            mock_load.return_value.model = "gpt-4"
            existing = MagicMock()
            existing.id = "sess-existing"
            existing.title = "Existing Session"
            existing.user_id = "user-1"
            mock_get_sess.return_value = existing
            mock_get_model.return_value = None
            mock_get_default.return_value = {"api_key": "sk-test", "base_url": None}
            mock_db_create_run.return_value = "run-999"

            result = await svc.create_run(
                requirement="continue this",
                session_id="sess-existing",
                user_id="user-1",
            )
            assert result["run_id"] == "run-999"
            assert result["session_id"] == "sess-existing"

    @pytest.mark.asyncio
    async def test_create_run_session_not_found_creates_new(self):
        from services.run_service import RunService

        svc = RunService()
        with (
            patch("services.run_service.load_config") as mock_load,
            patch("services.run_service.get_session") as mock_get_sess,
            patch("services.run_service.create_session") as mock_create_sess,
            patch("services.run_service.save_message", new_callable=AsyncMock),
            patch("services.run_resolve.get_api_key_for_model") as mock_get_model,
            patch("services.run_resolve.get_default_api_key") as mock_get_default,
            patch("services.run_service.buffer_run_messages"),
            _patch_create_task(),
            patch("services.run_service.update_session_title"),
            patch("repository.create_run") as mock_db_create_run,
        ):
            mock_load.return_value.model = "gpt-4"
            mock_get_sess.return_value = None
            new_sess = MagicMock()
            new_sess.id = "sess-new"
            mock_create_sess.return_value = new_sess
            mock_get_model.return_value = None
            mock_get_default.return_value = {"api_key": "sk-test", "base_url": None}
            mock_db_create_run.return_value = "run-new"

            result = await svc.create_run(
                requirement="new session please",
                session_id="sess-nonexistent",
                user_id="user-1",
            )
            assert result["session_id"] == "sess-new"

    @pytest.mark.asyncio
    async def test_create_run_rejects_other_users_session(self):
        """禁止向他人会话追加 run —— 归属校验 (跨用户写防护)."""
        from services.run_service import RunService

        svc = RunService()
        with (
            patch("services.run_service.load_config") as mock_load,
            patch("services.run_service.get_session") as mock_get_sess,
        ):
            mock_load.return_value.model = "gpt-4"
            other = MagicMock()
            other.id = "sess-other"
            other.user_id = "user-2"
            mock_get_sess.return_value = other

            with pytest.raises(ValueError, match="无权访问"):
                await svc.create_run(
                    requirement="hi",
                    session_id="sess-other",
                    user_id="user-1",
                )

    @pytest.mark.asyncio
    async def test_continue_run_rejects_other_users_session(self):
        """禁止在他人会话中发起续写 —— 归属校验 (跨用户写防护)."""
        from services.run_service import RunService

        svc = RunService()
        with (
            patch("services.run_service.load_config") as mock_load,
            patch("services.run_service.get_session") as mock_get_sess,
        ):
            mock_load.return_value.model = "gpt-4"
            other = MagicMock()
            other.id = "sess-other"
            other.user_id = "user-2"
            mock_get_sess.return_value = other

            with pytest.raises(ValueError, match="无权访问"):
                await svc.continue_run(
                    content="keep going",
                    session_id="sess-other",
                    user_id="user-1",
                )

    @pytest.mark.asyncio
    async def test_get_run_with_user_id_uses_for_user(self):
        """user_id 传参 → 走 get_run_for_user 归属查询."""
        from services.run_service import RunService

        svc = RunService()
        with (
            patch("services.run_service.get_run_for_user", new_callable=AsyncMock) as mock_for_user,
            patch("services.run_service.get_messages", new_callable=AsyncMock) as mock_msgs,
        ):
            mock_for_user.return_value = None
            assert await svc.get_run("r-1", "user-1") is None
            mock_for_user.assert_awaited_once_with("r-1", "user-1")
            mock_msgs.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_list_runs_with_user_id_uses_for_user(self):
        """user_id 传参 → 走 get_runs_for_user 归属查询."""
        from services.run_service import RunService

        svc = RunService()
        with (
            patch("services.run_service.get_runs_for_user", new_callable=AsyncMock) as mock_for_user,
            patch("services.run_service.serialize_run"),
        ):
            mock_for_user.return_value = []
            result = await svc.list_runs(limit=10, user_id="user-1")
            assert result == []
            mock_for_user.assert_awaited_once_with("user-1", limit=10)

    @pytest.mark.asyncio
    async def test_create_run_db_error_raises(self):
        from services.run_service import RunService

        svc = RunService()
        with (
            patch("services.run_service.load_config") as mock_load,
            patch("services.run_service.create_session") as mock_create_sess,
            patch("services.run_service.save_message", new_callable=AsyncMock),
            patch("services.run_resolve.get_api_key_for_model") as mock_get_model,
            patch("services.run_resolve.get_default_api_key") as mock_get_default,
            patch("repository.create_run") as mock_db_create_run,
        ):
            mock_load.return_value.model = "gpt-4"
            mock_sess = MagicMock()
            mock_sess.id = "sess-err"
            mock_create_sess.return_value = mock_sess
            mock_get_model.return_value = None
            mock_get_default.return_value = {"api_key": "sk-test", "base_url": None}
            mock_db_create_run.side_effect = Exception("DB down")

            with pytest.raises(Exception, match="DB down"):
                await svc.create_run(
                    requirement="fail",
                    session_id=None,
                    user_id="user-1",
                )

    @pytest.mark.asyncio
    async def test_continue_run_creates_session_when_none(self):
        from services.run_service import RunService

        svc = RunService()
        with (
            patch("services.run_service.load_config") as mock_load,
            patch("services.run_service.create_session") as mock_create_sess,
            patch("services.run_service.save_message", new_callable=AsyncMock),
            patch("services.run_resolve.get_api_key_for_model") as mock_get_model,
            patch("services.run_resolve.get_default_api_key") as mock_get_default,
            patch("services.run_service.buffer_run_messages"),
            _patch_create_task(),
            patch("repository.create_run") as mock_db_create_run,
        ):
            mock_load.return_value.model = "gpt-4"
            mock_sess = MagicMock()
            mock_sess.id = "sess-cont"
            mock_create_sess.return_value = mock_sess
            mock_get_model.return_value = None
            mock_get_default.return_value = {"api_key": "sk-test", "base_url": None}
            mock_db_create_run.return_value = "run-cont"

            result = await svc.continue_run(
                content="keep going",
                session_id=None,
                user_id="user-1",
            )
            assert result["run_id"] == "run-cont"
            assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_continue_run_no_api_key_raises(self):
        from services.run_service import RunService

        svc = RunService()
        with (
            patch("services.run_service.load_config"),
            patch("services.run_service.get_session") as mock_get_sess,
            patch("services.run_resolve.get_api_key_for_model") as mock_get_model,
            patch("services.run_resolve.get_default_api_key") as mock_get_default,
        ):
            owned = MagicMock()
            owned.user_id = "user-1"
            mock_get_sess.return_value = owned
            mock_get_model.side_effect = Exception("vault down")
            mock_get_default.side_effect = Exception("vault down")

            with pytest.raises(ValueError, match="API Key"):
                await svc.continue_run(
                    content="continue",
                    session_id="sess-1",
                    user_id="user-1",
                )

    @pytest.mark.asyncio
    async def test_get_run_returns_none_when_missing(self):
        from services.run_service import RunService

        svc = RunService()
        with patch("services.run_service.get_run") as mock_get_run:
            mock_get_run.return_value = None
            result = await svc.get_run("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_run_with_messages(self):
        from services.run_service import RunService

        svc = RunService()
        with (
            patch("services.run_service.get_run") as mock_get_run,
            patch("services.run_service.get_messages") as mock_get_msgs,
        ):
            mock_run = MagicMock()
            mock_run.id = "run-1"
            mock_run.session_id = "sess-1"
            mock_run.requirement = "test"
            mock_run.pm_document = None
            mock_run.code = None
            mock_run.review = None
            mock_run.approved = False
            mock_run.status = "completed"
            mock_run.created_at = datetime(2025, 1, 1, tzinfo=UTC)
            mock_run.updated_at = datetime(2025, 1, 2, tzinfo=UTC)
            mock_get_run.return_value = mock_run

            mock_msg = MagicMock()
            mock_msg.id = "msg-1"
            mock_msg.role = "user"
            mock_msg.agent_name = None
            mock_msg.content = "hello"
            mock_msg.thinking = None
            mock_msg.round_number = 1
            mock_msg.created_at = datetime(2025, 1, 1, tzinfo=UTC)
            mock_get_msgs.return_value = [mock_msg]

            result = await svc.get_run("run-1")
            assert result["id"] == "run-1"
            assert len(result["messages"]) == 1
            assert result["messages"][0]["content"] == "hello"

    @pytest.mark.asyncio
    async def test_list_runs_returns_list(self):
        from services.run_service import RunService

        svc = RunService()
        with patch("services.run_service.get_runs") as mock_get_runs:
            mock_run = MagicMock()
            mock_run.id = "run-list"
            mock_run.session_id = "sess-1"
            mock_run.requirement = "list test"
            mock_run.pm_document = None
            mock_run.code = None
            mock_run.review = None
            mock_run.approved = False
            mock_run.status = "completed"
            mock_run.created_at = datetime(2025, 1, 1, tzinfo=UTC)
            mock_run.updated_at = datetime(2025, 1, 2, tzinfo=UTC)
            mock_get_runs.return_value = [mock_run]

            result = await svc.list_runs(limit=10)
            assert len(result) == 1
            assert result[0]["id"] == "run-list"

    @pytest.mark.asyncio
    async def test_list_runs_enforces_max_limit(self):
        from services.run_service import RunService

        svc = RunService()
        with patch("services.run_service.get_runs") as mock_get_runs:
            mock_get_runs.return_value = []
            await svc.list_runs(limit=999)
            mock_get_runs.assert_called_once_with(limit=100)

    @pytest.mark.asyncio
    async def test_create_run_dispatches_agent_to_celery_when_enabled(self, monkeypatch):
        """RUN_DISPATCH=celery → run_agent.delay, no in-process create_task."""
        from services import run_service as rs
        from tasks import registry as _reg

        monkeypatch.setenv("RUN_DISPATCH", "celery")
        monkeypatch.setattr(rs, "RUN_DISPATCH", "celery")

        captured: dict = {}
        monkeypatch.setattr(
            _reg, "run_agent",
            type("FakeTask", (), {"delay": lambda *a, **kw: captured.update(kw) or None})(),
        )

        svc = rs.RunService()
        with (
            patch("services.run_service.load_config") as mock_load,
            patch("services.run_service.create_session") as mock_create_sess,
            patch("services.run_service.save_message", new_callable=AsyncMock),
            patch("services.run_resolve.get_api_key_for_use") as mock_get_key,
            patch("services.run_service.buffer_run_messages"),
            _patch_create_task() as mock_create_task,
            patch("services.run_service.get_session") as mock_get_sess,
            patch("services.run_service.update_session_title"),
            patch("repository.create_run") as mock_db_create_run,
        ):
            mock_load.return_value.model = "gpt-4"
            mock_sess = MagicMock()
            mock_sess.id = "sess-celery"
            mock_sess.user_id = "user-1"
            mock_create_sess.return_value = mock_sess
            mock_get_key.return_value = {"api_key": "sk-test", "base_url": None}
            mock_get_sess.return_value = mock_sess
            mock_db_create_run.return_value = "run-celery"

            result = await svc.create_run(
                requirement="hi",
                session_id=None,
                user_id="user-1",
                key_id="key-1",
            )

        assert result == {"run_id": "run-celery", "status": "pending", "session_id": "sess-celery"}
        assert captured["user_id"] == "user-1"
        assert captured["model"] == "gpt-4"
        assert captured["run_id"] == "run-celery"
        mock_create_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_run_uses_in_process_task_by_default(self):
        """RUN_DISPATCH 缺省 thread → asyncio.create_task, no .delay()."""
        from services import run_service as rs

        assert rs.RUN_DISPATCH == "thread"
        svc = rs.RunService()
        with (
            patch("services.run_service.load_config") as mock_load,
            patch("services.run_service.create_session") as mock_create_sess,
            patch("services.run_service.save_message", new_callable=AsyncMock),
            patch("services.run_resolve.get_api_key_for_use") as mock_get_key,
            patch("services.run_service.buffer_run_messages"),
            _patch_create_task() as mock_create_task,
            patch("services.run_service.get_session") as mock_get_sess,
            patch("services.run_service.update_session_title"),
            patch("repository.create_run") as mock_db_create_run,
        ):
            mock_load.return_value.model = "gpt-4"
            mock_sess = MagicMock()
            mock_sess.id = "sess-thread"
            mock_sess.user_id = "user-1"
            mock_create_sess.return_value = mock_sess
            mock_get_key.return_value = {"api_key": "sk-test", "base_url": None}
            mock_get_sess.return_value = mock_sess
            mock_db_create_run.return_value = "run-thread"

            result = await svc.create_run(
                requirement="hi",
                session_id=None,
                user_id="user-1",
                key_id="key-1",
            )

        assert result == {"run_id": "run-thread", "status": "pending", "session_id": "sess-thread"}
        mock_create_task.assert_called_once()
