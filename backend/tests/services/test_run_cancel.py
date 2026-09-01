"""Tests for RunService.cancel_run — in-flight run cancellation (REQ-RUN-006)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.run_service import RunService


@pytest.mark.requirement("REQ-RUN-006")
class TestCancelRun:
    @pytest.mark.asyncio
    async def test_cancels_registered_task_and_marks_cancelled(self):
        service = RunService()
        task = MagicMock(done=MagicMock(return_value=False))
        service._tasks["run-1"] = task

        with (
            patch("services.run_service.update_run_status", new_callable=AsyncMock) as mock_update,
        ):
            result = await service.cancel_run("run-1")

        task.cancel.assert_called_once()
        mock_update.assert_awaited_once_with("run-1", "cancelled")
        assert result == {"run_id": "run-1", "status": "cancelled", "cancelled": True}

    @pytest.mark.asyncio
    async def test_cancel_await_propagates_cancellation(self):
        """task.cancel() 后 await task 传播 CancelledError（suppress 后仍标记 cancelled）。"""
        service = RunService()

        async def _never_finishes() -> None:
            while True:
                await asyncio.sleep(1)

        import asyncio

        task = asyncio.create_task(_never_finishes())
        service._tasks["run-2"] = task
        task.add_done_callback(lambda _t: service._tasks.pop("run-2", None))

        with patch("services.run_service.update_run_status", new_callable=AsyncMock) as mock_update:
            result = await service.cancel_run("run-2")

        assert result["cancelled"] is True
        assert result["status"] == "cancelled"
        mock_update.assert_awaited_once_with("run-2", "cancelled")
        assert task.cancelled() is True

    @pytest.mark.asyncio
    async def test_unknown_run_returns_current_status(self):
        service = RunService()

        with patch("services.run_service.get_run", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(status="converged")
            result = await service.cancel_run("done-1")

        assert result == {"run_id": "done-1", "status": "converged", "cancelled": False}

    @pytest.mark.asyncio
    async def test_cancel_run_requires_ownership(self):
        """user_id 传参时非本人 run → not_found，绝不取消他人任务 (BOLA 防护)."""
        service = RunService()
        with patch("services.run_service.get_run_for_user", new_callable=AsyncMock) as mock_for_user:
            mock_for_user.return_value = None
            result = await service.cancel_run("run-other", user_id="user-1")

        assert result == {"run_id": "run-other", "status": "not_found", "cancelled": False}

    @pytest.mark.asyncio
    async def test_cancel_run_owner_cancels_task(self):
        """归属校验通过后正常取消自己名下的 in-flight run."""
        service = RunService()
        task = MagicMock(done=MagicMock(return_value=False))
        service._tasks["run-mine"] = task

        with (
            patch("services.run_service.get_run_for_user", new_callable=AsyncMock) as mock_for_user,
            patch("services.run_service.update_run_status", new_callable=AsyncMock) as mock_update,
        ):
            mock_for_user.return_value = MagicMock(status="pending")
            result = await service.cancel_run("run-mine", user_id="user-1")

        task.cancel.assert_called_once()
        mock_update.assert_awaited_once_with("run-mine", "cancelled")
        assert result == {"run_id": "run-mine", "status": "cancelled", "cancelled": True}

    @pytest.mark.asyncio
    async def test_celery_mode_revokes(self):
        service = RunService()

        with (
            patch("services.run_service.RUN_DISPATCH", "celery"),
            patch("services.run_service.update_run_status", new_callable=AsyncMock) as mock_update,
            patch("broker.celery_app.control.revoke") as mock_revoke,
        ):
            result = await service.cancel_run("celery-1")

        mock_revoke.assert_called_once_with("celery-1", terminate=False)
        assert result["cancelled"] is True
        mock_update.assert_awaited_once_with("celery-1", "cancelled")

    @pytest.mark.asyncio
    async def test_done_task_is_not_cancelled_twice(self):
        service = RunService()
        task = MagicMock(done=MagicMock(return_value=True))
        service._tasks["run-3"] = task

        with patch("services.run_service.get_run", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(status="converged")
            result = await service.cancel_run("run-3")

        task.cancel.assert_not_called()
        assert result["cancelled"] is False
