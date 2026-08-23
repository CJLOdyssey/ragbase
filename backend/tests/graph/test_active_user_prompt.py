"""Tests for graph.helpers.load_active_user_prompt — prompt lifecycle gate.

启用(active)提示词才可作为对话人设注入；草稿/不存在/查询异常一律返回空串
（fail-open），保证聊天永不因提示词加载失败而中断。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from graph.helpers import load_active_user_prompt


def _prompt(status: str = "active", content: str = "你是测试助手。"):
    p = MagicMock()
    p.status = status
    p.content = content
    return p


class TestLoadActiveUserPrompt:
    @pytest.mark.asyncio
    async def test_returns_content_for_active_prompt(self):
        with patch(
            "repository.prompts.get_prompt",
            new=AsyncMock(return_value=_prompt("active")),
        ):
            assert await load_active_user_prompt("p1") == "你是测试助手。"

    @pytest.mark.asyncio
    async def test_draft_prompt_is_never_injected(self):
        with patch(
            "repository.prompts.get_prompt",
            new=AsyncMock(return_value=_prompt("draft")),
        ):
            assert await load_active_user_prompt("p1") == ""

    @pytest.mark.asyncio
    async def test_missing_prompt_returns_empty(self):
        with patch(
            "repository.prompts.get_prompt",
            new=AsyncMock(return_value=None),
        ):
            assert await load_active_user_prompt("missing") == ""

    @pytest.mark.asyncio
    async def test_lookup_failure_fails_open(self):
        with patch(
            "repository.prompts.get_prompt",
            new=AsyncMock(side_effect=RuntimeError("db down")),
        ):
            assert await load_active_user_prompt("p1") == ""
