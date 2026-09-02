"""Unit tests for RunService parent-run version-chain inheritance (分支语义)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _patch_create_task():
    """Patch create_task without leaking unawaited coroutines (见 test_run_service)."""
    mock = MagicMock()

    def _capture(coro):
        coro.close()
        return MagicMock()

    mock.side_effect = _capture
    return patch("services.run_service.asyncio.create_task", mock)


def _create_run_patches():
    """Common patches for create_run: session creation, key resolve, dispatch."""
    return (
        patch("services.run_service.load_config"),
        patch("services.run_service.create_session"),
        patch("services.run_service.get_run_for_user", new_callable=AsyncMock),
        patch("services.run_resolve.get_api_key_for_model"),
        patch("services.run_resolve.get_default_api_key"),
        patch("services.run_service.buffer_run_messages"),
        _patch_create_task(),
        patch("services.run_service.update_session_title"),
        patch("repository.create_run"),
    )


class _PatchedRun:
    """Enter all create_run patches; exposes the key mocks as attributes."""

    def __init__(self):
        self.patches = _create_run_patches()

    def __enter__(self):
        started = [p.start() for p in self.patches]
        (self.load, self.create_session, self.parent, self.get_model,
         self.get_default) = started[:5]
        self.db_create_run = started[8]
        return self

    def __exit__(self, *exc):
        for p in reversed(self.patches):
            p.stop()
        return False


class TestCreateRunParentChain:
    @pytest.mark.asyncio
    async def test_create_run_parent_not_owned_does_not_inherit_versions(self):
        """parent_run_id 非本人 → 不继承其版本链（跨用户数据耦合防护）。"""
        from services.run_service import RunService

        svc = RunService()
        with _PatchedRun() as ctx:
            ctx.load.return_value.model = "gpt-4"
            mock_sess = MagicMock()
            mock_sess.id = "sess-p"
            ctx.create_session.return_value = mock_sess
            ctx.parent.return_value = None
            ctx.get_model.return_value = None
            ctx.get_default.return_value = {"api_key": "sk-test", "base_url": None}
            ctx.db_create_run.return_value = "run-p"

            result = await svc.create_run(
                requirement="child",
                session_id=None,
                user_id="user-1",
                parent_run_id="run-other",
            )
            assert result["run_id"] == "run-p"
            ctx.parent.assert_awaited_once_with("run-other", "user-1")
            assert ctx.db_create_run.await_args.kwargs["requirement_versions"] is None

    @pytest.mark.asyncio
    async def test_create_run_owned_parent_inherits_versions(self):
        """parent 为本人 run → 正常继承版本链（编辑分支语义保持）。"""
        from services.run_service import RunService

        svc = RunService()
        with _PatchedRun() as ctx:
            ctx.load.return_value.model = "gpt-4"
            mock_sess = MagicMock()
            mock_sess.id = "sess-own"
            ctx.create_session.return_value = mock_sess
            owned = MagicMock()
            owned.requirement_versions = '["v1"]'
            owned.requirement = "v1-text"
            ctx.parent.return_value = owned
            ctx.get_model.return_value = None
            ctx.get_default.return_value = {"api_key": "sk-test", "base_url": None}
            ctx.db_create_run.return_value = "run-own"

            result = await svc.create_run(
                requirement="child",
                session_id=None,
                user_id="user-1",
                parent_run_id="run-mine",
            )
            assert result["run_id"] == "run-own"
            assert ctx.db_create_run.await_args.kwargs["requirement_versions"] == ["v1", "child"]
