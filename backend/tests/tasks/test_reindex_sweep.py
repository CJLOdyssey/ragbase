"""Tests for the periodic reindex sweep (backend/tasks/reindex_sweep.py)."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from tasks.reindex_sweep import _reindex_sweep


@pytest.fixture(autouse=True)
def _no_inflight():
    """Keep the in-flight guard offline by default (no Redis in unit tests)."""
    with patch("tasks.reindex_sweep.is_index_in_flight", new=AsyncMock(return_value=False)):
        yield


def _asset(asset_id: str, user_id: str, path: str, indexed: bool, updated_at: datetime):
    a = MagicMock()
    a.id = asset_id
    a.user_id = user_id
    a.storage_path = path
    a.indexed = indexed
    a.updated_at = updated_at
    a.created_at = updated_at
    return a


class TestReindexSweep:
    @pytest.mark.asyncio
    async def test_skips_inflight_asset(self, tmp_path):
        """并发防重：索引任务在飞的资产不入队（手动触发与 sweep 竞争时）。"""
        f = tmp_path / "doc.md"
        f.write_text("v1", encoding="utf-8")
        asset = _asset("a1", "u1", str(f), indexed=False, updated_at=datetime.now(UTC))

        session = _session_with_assets([asset])
        with (
            patch("core.infra.database.get_session_factory", return_value=lambda: _SessionCtx(session)),
            patch("tasks.registry.index_asset") as task,
            patch("tasks.reindex_sweep.is_index_in_flight", new=AsyncMock(return_value=True)),
        ):
            result = await _reindex_sweep()

        assert result == {"queued": 0}
        task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_reindexes_changed_file(self, tmp_path):
        """File mtime newer than updated_at → queued."""
        f = tmp_path / "doc.md"
        f.write_text("v1", encoding="utf-8")
        # Simulate an external replacement: file is newer than the DB row.
        future = datetime.now(UTC) + timedelta(minutes=5)
        os.utime(f, (future.timestamp(), future.timestamp()))
        asset = _asset("a1", "u1", str(f), indexed=True, updated_at=datetime.now(UTC))

        session = _session_with_assets([asset])
        with (
            patch("core.infra.database.get_session_factory", return_value=lambda: _SessionCtx(session)),
            patch("tasks.registry.index_asset") as task,
        ):
            result = await _reindex_sweep()

        assert result == {"queued": 1}
        task.delay.assert_called_once_with("a1", "u1")

    @pytest.mark.asyncio
    async def test_skips_unchanged_indexed(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("v1", encoding="utf-8")
        asset = _asset("a1", "u1", str(f), indexed=True, updated_at=datetime.now(UTC))

        session = _session_with_assets([asset])
        with (
            patch("core.infra.database.get_session_factory", return_value=lambda: _SessionCtx(session)),
            patch("tasks.registry.index_asset") as task,
        ):
            result = await _reindex_sweep()
        assert result == {"queued": 0}
        task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_retries_unindexed(self, tmp_path):
        """A failed first index (indexed=False) is retried."""
        f = tmp_path / "doc.md"
        f.write_text("v1", encoding="utf-8")
        asset = _asset("a1", "u1", str(f), indexed=False, updated_at=datetime.now(UTC))

        session = _session_with_assets([asset])
        with (
            patch("core.infra.database.get_session_factory", return_value=lambda: _SessionCtx(session)),
            patch("tasks.registry.index_asset") as task,
        ):
            result = await _reindex_sweep()
        assert result == {"queued": 1}
        task.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_missing_file(self, tmp_path):
        asset = _asset("a1", "u1", str(tmp_path / "gone.md"), indexed=False, updated_at=datetime.now(UTC))
        session = _session_with_assets([asset])
        with (
            patch("core.infra.database.get_session_factory", return_value=lambda: _SessionCtx(session)),
            patch("tasks.registry.index_asset") as task,
        ):
            result = await _reindex_sweep()
        assert result == {"queued": 0}
        task.delay.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_created_at_when_updated_at_missing(self, tmp_path):
        """updated_at is None → falls back to created_at for mtime comparison."""
        f = tmp_path / "doc.md"
        f.write_text("v1", encoding="utf-8")
        past = datetime.now(UTC) - timedelta(minutes=10)
        asset = _asset("a1", "u1", str(f), indexed=True, updated_at=None)
        asset.created_at = past

        session = _session_with_assets([asset])
        with (
            patch("core.infra.database.get_session_factory", return_value=lambda: _SessionCtx(session)),
            patch("tasks.registry.index_asset") as task,
        ):
            result = await _reindex_sweep()
        assert result == {"queued": 1}  # file (now) newer than created_at (10m ago) -> reindex
        task.delay.assert_called_once()

    def test_run_reindex_sweep_sync_wrapper(self, tmp_path):
        """Sync entrypoint delegates to the async sweep."""
        f = tmp_path / "doc.md"
        f.write_text("v1", encoding="utf-8")
        asset = _asset("a1", "u1", str(f), indexed=False, updated_at=datetime.now(UTC))

        session = _session_with_assets([asset])
        with (
            patch("core.infra.database.get_session_factory", return_value=lambda: _SessionCtx(session)),
            patch("tasks.registry.index_asset") as task,
        ):
            from tasks.reindex_sweep import run_reindex_sweep

            result = run_reindex_sweep()
        assert result == {"queued": 1}
        task.delay.assert_called_once()



def _session_with_assets(assets):
    """Session whose execute -> .all() chain returns projected rows synchronously.

    The sweep selects explicit columns, so rows come back as Row-like objects;
    MagicMock assets stand in for them (attribute access only).
    """
    result_mock = MagicMock()
    result_mock.all.return_value = assets
    session = AsyncMock()
    session.execute.return_value = result_mock
    return session


class _SessionCtx:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass
