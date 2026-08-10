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
    async def test_creates_row(self):
        session = AsyncMock()
        with _patch_db(session):
            result = await create_feedback("run-1", "u1", "good")
        assert result["rating"] == "good"
        assert result["run_id"] == "run-1"
        session.add.assert_called_once()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rejects_invalid_rating(self):
        with pytest.raises(ValueError, match="rating"):
            await create_feedback("run-1", "u1", "meh")


class TestListFeedback:
    @pytest.mark.asyncio
    async def test_lists_own_feedback(self):
        row = MagicMock()
        row.id = "f1"
        row.run_id = "run-1"
        row.rating = "bad"
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
        query = str(session.execute.call_args[0][0])
        assert "user_id" in query
