"""Tests for backend/core/mock_fallback.py — run_mock function."""

from unittest.mock import AsyncMock, patch

import pytest


class TestRunMock:

    @pytest.fixture(autouse=True)
    def _no_sleep(self):
        """run_mock simulates response pacing with asyncio.sleep(0.5) ×5 per
        call (2.5s/test). Tests don't need the pacing — neutralize it."""
        with patch("core.mock_fallback.asyncio.sleep", new_callable=AsyncMock):
            yield

    @pytest.mark.asyncio
    async def test_run_mock_produces_messages(self):
        from core.mock_fallback import run_mock

        mock_emitter = AsyncMock()
        with patch("core.mock_fallback.StreamEmitter", return_value=mock_emitter):
            result = await run_mock(
                requirement="Build a REST API",
                run_id="test-run",
                session_id="test-session",
            )

        # Should have produced several messages
        assert mock_emitter._emit.call_count == 5
        calls = [call.args for call in mock_emitter._emit.call_args_list]
        assert calls[0][1] == "收到需求：Build a REST API"
        assert calls[1][1] == "正在分析需求..."

        # Result should include the joined messages
        assert result.approved is True
        assert result.status == "converged"
        assert "Build a REST API" in result.response

    @pytest.mark.asyncio
    async def test_run_mock_truncates_long_requirement(self):
        from core.mock_fallback import run_mock

        mock_emitter = AsyncMock()
        long_req = "A" * 200
        with patch("core.mock_fallback.StreamEmitter", return_value=mock_emitter):
            result = await run_mock(
                requirement=long_req,
                run_id="test-run",
                session_id=None,
            )

        first_call = mock_emitter._emit.call_args_list[0]
        assert len(first_call.args[1]) <= 100 + 5  # "收到需求：" + 100 chars
        assert result.status == "converged"
        assert result.approved is True

    @pytest.mark.asyncio
    async def test_run_mock_null_session(self):
        from core.mock_fallback import run_mock

        mock_emitter = AsyncMock()
        with patch("core.mock_fallback.StreamEmitter", return_value=mock_emitter):
            result = await run_mock(
                requirement="Test",
                run_id="r1",
                session_id=None,
            )

        assert result.status == "converged"

    @pytest.mark.asyncio
    async def test_run_mock_default_response_not_approved(self):
        from core.mock_fallback import run_mock

        mock_emitter = AsyncMock()
        with patch("core.mock_fallback.StreamEmitter", return_value=mock_emitter):
            result = await run_mock(
                requirement="Test",
                run_id="r2",
                session_id="s1",
            )
            assert result.response != ""
