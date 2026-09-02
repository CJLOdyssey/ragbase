"""Tests for backend.tasks.pipeline_utils — shared pipeline helpers."""

from unittest.mock import MagicMock

from tasks.pipeline_utils import (
    _build_session_context,
    _is_balance_error,
    _parse_json_field,
)


class TestBuildSessionContext:

    def test_merges_memories(self):
        m1 = MagicMock()
        m1.content_type = "code"
        m1.agent_role = "agent"
        m1.summary = "wrote hello world"
        m2 = MagicMock()
        m2.content_type = "review"
        m2.agent_role = "agent"
        m2.summary = "checked style"

        ctx = _build_session_context([m1, m2])
        assert "历史上下文" in ctx
        assert "wrote hello world" in ctx
        assert "checked style" in ctx

    def test_empty(self):
        assert _build_session_context([]) == ""


class TestParseJsonField:

    def test_string(self):
        assert _parse_json_field('[{"a": 1}]') == [{"a": 1}]
        assert _parse_json_field('') == []
        assert _parse_json_field('invalid') == []

    def test_list(self):
        assert _parse_json_field([1, 2, 3]) == [1, 2, 3]
        assert _parse_json_field(None) == []


class TestIsBalanceError:

    def test_balance_messages_flagged(self):
        assert _is_balance_error(Exception("insufficient_quota"))
        assert _is_balance_error(Exception("余额不足"))
        assert _is_balance_error(Exception("402 Payment Required"))

    def test_non_balance_messages_not_flagged(self):
        assert not _is_balance_error(Exception("rate limit exceeded"))
        assert not _is_balance_error(Exception("generic error"))
