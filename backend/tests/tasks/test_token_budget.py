"""Tests for the per-user token budget enforcement (OWASP LLM10)."""

from unittest.mock import AsyncMock, patch

from tasks.agent_pipeline import _enforce_token_budget


class TestEnforceTokenBudget:
    async def test_disabled_budget_allows(self, monkeypatch):
        monkeypatch.delenv("USER_DAILY_TOKEN_BUDGET", raising=False)
        assert await _enforce_token_budget("u1", "r1") is True

    async def test_system_user_bypasses(self, monkeypatch):
        monkeypatch.setenv("USER_DAILY_TOKEN_BUDGET", "1")
        assert await _enforce_token_budget("system", "r1") is True

    async def test_under_budget_allows(self, monkeypatch):
        monkeypatch.setenv("USER_DAILY_TOKEN_BUDGET", "1000")
        with patch(
            "repository.keys_crud.sum_user_tokens_since",
            new_callable=AsyncMock,
            return_value=500,
        ):
            assert await _enforce_token_budget("u1", "r1") is True

    async def test_over_budget_fails_loud(self, monkeypatch):
        monkeypatch.setenv("USER_DAILY_TOKEN_BUDGET", "1000")
        with (
            patch(
                "repository.keys_crud.sum_user_tokens_since",
                new_callable=AsyncMock,
                return_value=1200,
            ),
            patch("tasks.agent_pipeline.update_run_status", new_callable=AsyncMock) as st,
            patch("tasks.agent_pipeline.publish_run_message", new_callable=AsyncMock) as pub,
        ):
            assert await _enforce_token_budget("u1", "r1") is False

        st.assert_awaited_once_with("r1", "error")
        pub.assert_awaited_once()
        assert pub.call_args[0][1]["type"] == "error"
        assert "用量已达上限" in pub.call_args[0][1]["message"]
