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


