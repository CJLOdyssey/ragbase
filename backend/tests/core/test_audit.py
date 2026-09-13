"""Unit tests for core.audit — audit entry logging facade."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLogAudit:
    @patch("repository.audit.get_session_factory")
    @pytest.mark.asyncio
    async def test_log_audit_creates_entry(self, mock_get_factory):
        from core.audit import log_audit

        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_get_factory.return_value = mock_factory

        await log_audit("create", "agent", "my-agent", "创建成功")

        from orm import AuditLogDB

        mock_session.add.assert_called_once()
        added = mock_session.add.call_args[0][0]
        assert isinstance(added, AuditLogDB)
        assert added.action == "create"
        assert added.entity_type == "agent"
        assert added.entity_name == "my-agent"
        assert added.detail == "创建成功"
        mock_session.commit.assert_awaited_once()

    @patch("repository.audit.get_session_factory")
    @pytest.mark.asyncio
    async def test_log_audit_minimal_args(self, mock_get_factory):
        from core.audit import log_audit

        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_get_factory.return_value = mock_factory

        await log_audit("delete", "tool")

        added = mock_session.add.call_args[0][0]
        assert added.action == "delete"
        assert added.entity_type == "tool"
        assert added.entity_name == ""
        assert added.detail == ""

    @patch("repository.audit.get_session_factory")
    @pytest.mark.asyncio
    async def test_log_audit_fills_request_context(self, mock_get_factory):
        """AuthMiddleware 经 set_audit_context 填充的 user/IP/UA/rid 自动写入条目。"""
        from core.audit import log_audit, set_audit_context

        mock_factory = MagicMock()
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_get_factory.return_value = mock_factory

        set_audit_context(
            user_name="alice",
            client_ip="203.0.113.9",
            user_agent="pytest/1.0",
            request_id="rid-123",
        )
        try:
            await log_audit("update", "prompt", "p1")
        finally:
            # 清理 ContextVar，避免污染同 worker 的其他测试
            set_audit_context()

        added = mock_session.add.call_args[0][0]
        assert added.user_name == "alice"
        assert added.client_ip == "203.0.113.9"
        assert added.user_agent == "pytest/1.0"
        assert added.request_id == "rid-123"


