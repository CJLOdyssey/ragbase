"""Tests for RAG quality feedback (repository/feedback.py + routes)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from repository.feedback import create_feedback, list_feedback


class _Ctx:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass


def _patch_db(session):
    return patch("repository.feedback.get_session_factory", return_value=lambda: _Ctx(session))


class TestCreateFeedback:
    @pytest.mark.asyncio
    async def test_creates_row_with_snapshot(self):
        session = AsyncMock()
        snapshot = ("问题?", "回答。", [{"asset_id": "a1", "text": "…", "similarity": 0.9}])
        with _patch_db(session), patch(
            "repository.feedback._snapshot_for_run", new_callable=AsyncMock, return_value=snapshot
        ):
            result = await create_feedback("run-1", "u1", "good")
        assert result["rating"] == "good"
        assert result["run_id"] == "run-1"
        assert result["query"] == "问题?"
        assert result["answer"] == "回答。"
        assert result["sources"][0]["asset_id"] == "a1"
        session.add.assert_called_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_creates_row_without_snapshot(self):
        session = AsyncMock()
        with _patch_db(session), patch(
            "repository.feedback._snapshot_for_run", new_callable=AsyncMock, return_value=(None, None, [])
        ):
            result = await create_feedback("run-1", "u1", "good")
        assert result["query"] is None
        assert result["sources"] == []

    @pytest.mark.asyncio
    async def test_rejects_invalid_rating(self):
        with pytest.raises(ValueError, match="rating"):
            await create_feedback("run-1", "u1", "meh")


class TestSnapshotForRun:
    @pytest.mark.asyncio
    async def test_captures_latest_agent_answer_and_sources(self):
        from repository.feedback import _snapshot_for_run

        run = MagicMock()
        run.requirement = "问题?"
        session = AsyncMock()
        session.get = AsyncMock(return_value=run)
        with _patch_db(session), patch(
            "repository.feedback.get_messages",
            new_callable=AsyncMock,
            return_value=[
                MagicMock(role="user", content="问题?"),
                MagicMock(role="agent", content="回答。", sources=None),
                MagicMock(role="agent", content="最终回答", sources='[{"asset_id": "a1"}]'),
            ],
        ):
            query, answer, sources = await _snapshot_for_run("run-1")
        assert query == "问题?"
        assert answer == "最终回答"
        assert sources == [{"asset_id": "a1"}]

    @pytest.mark.asyncio
    async def test_handles_malformed_sources_json(self):
        from repository.feedback import _snapshot_for_run

        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        with _patch_db(session), patch(
            "repository.feedback.get_messages",
            new_callable=AsyncMock,
            return_value=[MagicMock(role="agent", content="x", sources="{bad")],
        ):
            query, answer, sources = await _snapshot_for_run("run-1")
        assert query is None
        assert answer == "x"
        assert sources == []


class TestListFeedback:
    @pytest.mark.asyncio
    async def test_lists_own_feedback(self):
        row = MagicMock()
        row.id = "f1"
        row.run_id = "run-1"
        row.rating = "bad"
        row.query = "问题?"
        row.answer = None
        row.sources = None
        row.created_at = None
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [row]
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        session = AsyncMock()
        session.execute.return_value = result_mock
        with _patch_db(session):
            rows = await list_feedback("u1")
        assert rows[0]["rating"] == "bad"
        assert rows[0]["query"] == "问题?"
        assert rows[0]["sources"] == []
        query = str(session.execute.call_args[0][0])
        assert "user_id" in query
