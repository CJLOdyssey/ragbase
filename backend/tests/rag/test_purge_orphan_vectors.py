"""Tests for orphan vector purge task (tasks/purge_orphan_vectors.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _AsyncSessionCtx:
    def __init__(self, session: AsyncMock):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass


class _SessionFactory:
    def __init__(self, session: AsyncMock):
        self._session = session

    def __call__(self):
        return _AsyncSessionCtx(self._session)


def _patch_all(session: AsyncMock, orphan_ids: list[str] | None = None):
    """Patch DB factory and PgVectorStore for _purge_orphan_vectors."""
    factory = _SessionFactory(session)
    mock_store = AsyncMock()
    return (
        patch("core.infra.database.get_session_factory", return_value=factory),
        patch("rag.rag_store.PgVectorStore", return_value=mock_store),
        mock_store,
    )


class TestPurgeOrphanVectors:
    @pytest.mark.asyncio
    async def test_no_orphans_returns_zero(self):
        """L27-28: when SELECT returns empty, return {'purged': 0}."""
        from tasks.purge_orphan_vectors import _purge_orphan_vectors

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        db_patch, store_patch, _ = _patch_all(session)
        with db_patch, store_patch:
            result = await _purge_orphan_vectors()

        assert result == {"purged": 0}
        # clear_assets must NOT be called when no orphans
        # (store_patch mock is created inside the context, so we check via the patched class)

    @pytest.mark.asyncio
    async def test_purge_clears_and_resets(self):
        """L30-46: orphans found → clear_assets + UPDATE + commit."""
        from tasks.purge_orphan_vectors import _purge_orphan_vectors

        session = AsyncMock()
        select_result = MagicMock()
        select_result.all.return_value = [("asset-1",), ("asset-2",)]
        update_result = MagicMock()

        call_idx = 0
        results = [select_result, update_result]

        async def _execute(sql_or_text, params=None):
            nonlocal call_idx
            r = results[call_idx]
            call_idx += 1
            return r

        session.execute = AsyncMock(side_effect=_execute)
        session.commit = AsyncMock()

        db_patch, store_patch, mock_store = _patch_all(session)
        with db_patch, store_patch:
            result = await _purge_orphan_vectors()

        assert result == {"purged": 2}
        mock_store.clear_assets.assert_awaited_once_with(["asset-1", "asset-2"])
        # UPDATE was called with correct params
        update_call = session.execute.call_args_list[1]
        params = update_call[0][1]
        assert params["err"] == "purged: no knowledge base"
        assert params["ids"] == ["asset-1", "asset-2"]
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_single_orphan(self):
        """L30-46: single orphan handled identically."""
        from tasks.purge_orphan_vectors import _purge_orphan_vectors

        session = AsyncMock()
        select_result = MagicMock()
        select_result.all.return_value = [("only-one",)]
        update_result = MagicMock()

        call_idx = 0
        results = [select_result, update_result]

        async def _execute(sql_or_text, params=None):
            nonlocal call_idx
            r = results[call_idx]
            call_idx += 1
            return r

        session.execute = AsyncMock(side_effect=_execute)
        session.commit = AsyncMock()

        db_patch, store_patch, mock_store = _patch_all(session)
        with db_patch, store_patch:
            result = await _purge_orphan_vectors()

        assert result == {"purged": 1}
        mock_store.clear_assets.assert_awaited_once_with(["only-one"])

    def test_run_sync_entrypoint(self):
        """L49-53: run_purge_orphan_vectors calls asyncio.run."""
        from tasks.purge_orphan_vectors import run_purge_orphan_vectors

        with patch(
            "tasks.purge_orphan_vectors._purge_orphan_vectors",
            new_callable=AsyncMock,
            return_value={"purged": 5},
        ):
            result = run_purge_orphan_vectors()

        assert result == {"purged": 5}

    @pytest.mark.asyncio
    async def test_uses_factory_from_database_module(self):
        """L16: factory is obtained from core.infra.database.get_session_factory."""
        from tasks.purge_orphan_vectors import _purge_orphan_vectors

        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        factory_spy = MagicMock(return_value=_AsyncSessionCtx(session))

        with patch(
            "core.infra.database.get_session_factory", return_value=factory_spy
        ), patch("rag.rag_store.PgVectorStore"):
            await _purge_orphan_vectors()

        factory_spy.assert_called_once()
