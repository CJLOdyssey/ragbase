"""Tests for continue generation feature (REQ-RUN-006).

Tests the "继续生成" (resume after interruption) functionality:
- continue_run creates a new run
- continue_run requires API key
- continue_run with session_id uses existing session
- continue_run without session_id creates new session
- continue_run dispatches background pipeline
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.run_service import RunService


@pytest.mark.requirement("REQ-RUN-006")
class TestContinueRun:
    """Test the continue_run functionality."""

    @pytest.mark.asyncio
    async def test_continue_run_creates_new_session_when_none(self):
        """continue_run creates a new session when session_id is None."""
        run_service = RunService()

        with (
            patch("services.run_service.load_config") as mock_config,
            patch("services.run_resolve.get_api_key_for_model", return_value=None),
            patch("services.run_resolve.get_default_api_key") as mock_key,
            patch("services.run_service.create_session") as mock_create_sess,
            patch("services.run_service.save_message", new_callable=AsyncMock),
            patch("repository.create_run") as mock_create_run,
            patch("services.run_service.buffer_run_messages"),
            patch("asyncio.create_task"),
        ):
            mock_config.return_value = MagicMock(model="test-model")
            mock_key.return_value = {"api_key": "test-key", "base_url": "http://test.com"}
            mock_create_sess.return_value = MagicMock(id="new-session-id")
            mock_create_run.return_value = "run-123"

            result = await run_service.continue_run(
                content="继续生成内容",
                session_id=None,
                user_id="user-1",
            )

            assert result["session_id"] == "new-session-id"
            mock_create_sess.assert_called_once()

    @pytest.mark.asyncio
    async def test_continue_run_uses_existing_session(self):
        """continue_run uses existing session when session_id is provided."""
        run_service = RunService()

        with (
            patch("services.run_service.load_config") as mock_config,
            patch("services.run_resolve.get_api_key_for_model", return_value=None),
            patch("services.run_resolve.get_default_api_key") as mock_key,
            patch("services.run_service.create_session") as mock_create_sess,
            patch("services.run_service.save_message", new_callable=AsyncMock),
            patch("repository.create_run") as mock_create_run,
            patch("services.run_service.buffer_run_messages"),
            patch("asyncio.create_task"),
        ):
            mock_config.return_value = MagicMock(model="test-model")
            mock_key.return_value = {"api_key": "test-key", "base_url": "http://test.com"}
            mock_create_run.return_value = "run-456"

            result = await run_service.continue_run(
                content="继续生成内容",
                session_id="existing-session-id",
                user_id="user-1",
            )

            assert result["session_id"] == "existing-session-id"
            mock_create_sess.assert_not_called()

    @pytest.mark.asyncio
    async def test_continue_run_requires_api_key(self):
        """continue_run raises ValueError when no API key is available."""
        run_service = RunService()

        with (
            patch("services.run_service.load_config") as mock_config,
            patch("services.run_resolve.get_api_key_for_model", return_value=None),
            patch("services.run_resolve.get_default_api_key") as mock_key,
        ):
            mock_config.return_value = MagicMock(model="test-model")
            mock_key.return_value = None

            with pytest.raises(ValueError, match="请先在设置中配置 API Key"):
                await run_service.continue_run(
                    content="继续生成内容",
                    session_id="session-1",
                    user_id="user-1",
                )

    @pytest.mark.asyncio
    async def test_continue_run_returns_running_status(self):
        """continue_run returns 'running' status."""
        run_service = RunService()

        with (
            patch("services.run_service.load_config") as mock_config,
            patch("services.run_resolve.get_api_key_for_model", return_value=None),
            patch("services.run_resolve.get_default_api_key") as mock_key,
            patch("services.run_service.save_message", new_callable=AsyncMock),
            patch("repository.create_run") as mock_create_run,
            patch("services.run_service.buffer_run_messages"),
            patch("asyncio.create_task"),
        ):
            mock_config.return_value = MagicMock(model="test-model")
            mock_key.return_value = {"api_key": "test-key", "base_url": "http://test.com"}
            mock_create_run.return_value = "run-789"

            result = await run_service.continue_run(
                content="继续生成内容",
                session_id="session-1",
                user_id="user-1",
            )

            assert result["status"] == "running"
            assert result["run_id"] == "run-789"

    @pytest.mark.asyncio
    async def test_continue_run_dispatches_background_pipeline(self):
        """continue_run dispatches background pipeline via asyncio.create_task."""
        run_service = RunService()

        with (
            patch("services.run_service.load_config") as mock_config,
            patch("services.run_resolve.get_api_key_for_model", return_value=None),
            patch("services.run_resolve.get_default_api_key") as mock_key,
            patch("services.run_service.save_message", new_callable=AsyncMock),
            patch("repository.create_run") as mock_create_run,
            patch("services.run_service.buffer_run_messages"),
            patch("asyncio.create_task") as mock_create_task,
        ):
            mock_config.return_value = MagicMock(model="test-model")
            mock_key.return_value = {"api_key": "test-key", "base_url": "http://test.com"}
            mock_create_run.return_value = "run-dispatch"

            await run_service.continue_run(
                content="继续生成内容",
                session_id="session-1",
                user_id="user-1",
            )

            mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_continue_run_with_thinking(self):
        """continue_run passes thinking parameter to pipeline."""
        run_service = RunService()

        with (
            patch("services.run_service.load_config") as mock_config,
            patch("services.run_resolve.get_api_key_for_model", return_value=None),
            patch("services.run_resolve.get_default_api_key") as mock_key,
            patch("services.run_service.save_message", new_callable=AsyncMock),
            patch("repository.create_run") as mock_create_run,
            patch("services.run_service.buffer_run_messages"),
            patch("asyncio.create_task") as mock_create_task,
        ):
            mock_config.return_value = MagicMock(model="test-model")
            mock_key.return_value = {"api_key": "test-key", "base_url": "http://test.com"}
            mock_create_run.return_value = "run-thinking"

            await run_service.continue_run(
                content="继续生成内容",
                session_id="session-1",
                user_id="user-1",
                thinking="之前的思考内容",
            )

            # Verify task was created
            mock_create_task.assert_called_once()


@pytest.mark.requirement("REQ-RUN-006")
class TestCompleteRunEndpoint:
    """Test the /api/runs/complete endpoint."""

    @pytest.fixture(autouse=True)
    async def _authenticated_client(self, test_client):
        """登录墙恒开：为 session 级 test_client 注入有效身份令牌。"""
        from unittest.mock import patch as _patch

        with _patch("auth.auth_middleware.decode_jwt",
                    return_value={"sub": "tester"}), \
             _patch("repository.auth.get_user_by_id", return_value=object()):
            test_client.headers["Authorization"] = "Bearer t"
            yield test_client
            test_client.headers.pop("Authorization", None)

    @pytest.mark.asyncio
    async def test_complete_run_endpoint_success(self, test_client):
        """POST /api/runs/complete returns run response."""
        with patch("routers.run_continue.run_service") as mock_service:
            mock_service.continue_run = AsyncMock(
                return_value={
                    "run_id": "run-123",
                    "status": "running",
                    "session_id": "session-1",
                }
            )

            response = await test_client.post(
                "/api/runs/complete",
                json={
                    "content": "继续生成内容",
                    "session_id": "session-1",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["run_id"] == "run-123"
            assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_complete_run_endpoint_empty_content(self, test_client):
        """POST /api/runs/complete handles empty content."""
        with patch("routers.run_continue.run_service") as mock_service:
            mock_service.continue_run = AsyncMock(
                return_value={
                    "run_id": "run-456",
                    "status": "running",
                    "session_id": "session-2",
                }
            )

            response = await test_client.post(
                "/api/runs/complete",
                json={
                    "content": "",
                    "session_id": "session-2",
                },
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_complete_run_endpoint_with_thinking(self, test_client):
        """POST /api/runs/complete accepts thinking parameter."""
        with patch("routers.run_continue.run_service") as mock_service:
            mock_service.continue_run = AsyncMock(
                return_value={
                    "run_id": "run-789",
                    "status": "running",
                    "session_id": "session-3",
                }
            )

            response = await test_client.post(
                "/api/runs/complete",
                json={
                    "content": "继续生成内容",
                    "session_id": "session-3",
                    "thinking": "之前的思考",
                },
            )

            assert response.status_code == 200
            # Verify thinking was passed
            call_kwargs = mock_service.continue_run.call_args.kwargs
            assert call_kwargs["thinking"] == "之前的思考"
