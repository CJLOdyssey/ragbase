"""Tests for RAG vector store (backend/rag/rag_store.py)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rag.rag_chunking import Chunk
from rag.rag_store import PgVectorStore


class _AsyncSessionCtx:
    """Async context manager that yields a mock session."""

    def __init__(self, session: AsyncMock):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass


class _SessionFactory:
    """Mock factory: factory() returns an async context manager yielding session."""

    def __init__(self, session: AsyncMock):
        self._session = session

    def __call__(self):
        return _AsyncSessionCtx(self._session)


def _patch_db(session: AsyncMock):
    """Patch get_session_factory to return a factory yielding the given session."""
    factory = _SessionFactory(session)
    return patch("core.infra.database.get_session_factory", return_value=factory)


class TestPgVectorStore:
    def test_init(self):
        store = PgVectorStore()
        assert hasattr(store, "_initialized")
        assert store._initialized is False

    def test_ensure_table_exists(self):
        store = PgVectorStore()
        assert callable(store._ensure_table)

    # ── _ensure_table tests ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_ensure_table_initializes_once(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        with _patch_db(mock_session):
            await store._ensure_table()
            assert store._initialized is True
            call_count_before = mock_session.execute.call_count
            # Second call is a no-op
            await store._ensure_table()
            assert mock_session.execute.call_count == call_count_before

    @pytest.mark.asyncio
    async def test_ensure_table_creates_extension(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        with _patch_db(mock_session):
            await store._ensure_table()
            first_sql = str(mock_session.execute.call_args_list[0][0][0])
            assert "CREATE EXTENSION" in first_sql

    @pytest.mark.asyncio
    async def test_ensure_table_creates_table(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        with _patch_db(mock_session):
            await store._ensure_table()
            second_sql = str(mock_session.execute.call_args_list[1][0][0])
            assert "CREATE TABLE" in second_sql

    @pytest.mark.asyncio
    async def test_ensure_table_creates_index(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        with _patch_db(mock_session):
            await store._ensure_table()
            third_sql = str(mock_session.execute.call_args_list[2][0][0])
            assert "CREATE INDEX" in third_sql

    @pytest.mark.asyncio
    async def test_ensure_table_extension_failure_still_continues(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[Exception("no superuser"), None, None]
        )
        with _patch_db(mock_session):
            await store._ensure_table()
            assert store._initialized is True

    @pytest.mark.asyncio
    async def test_ensure_table_index_creation_fallback(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[None, None, Exception("HNSW not supported"), None]
        )
        with _patch_db(mock_session):
            await store._ensure_table()
            assert store._initialized is True

    @pytest.mark.asyncio
    async def test_ensure_table_both_indexes_fail(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            side_effect=[
                None, None,
                Exception("HNSW not supported"),
                Exception("IVFFlat not supported"),
            ]
        )
        with _patch_db(mock_session):
            await store._ensure_table()
            assert store._initialized is True

    # ── add() tests ────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_add_empty_chunks(self):
        store = PgVectorStore()
        await store.add([])
        assert store._initialized is False

    @pytest.mark.asyncio
    async def test_add_chunks_with_embeddings(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        chunks = [
            Chunk(id="c1", text="hello", session_id="s1", run_id="r1", embedding=[0.1] * 1024, tags=["test"]),
            Chunk(id="c2", text="world", session_id="s1", run_id="r1", embedding=[0.2] * 1024, tags=[]),
        ]
        with _patch_db(mock_session):
            await store.add(chunks)
            # 3 DDL + 2 INSERT
            assert mock_session.execute.call_count == 5

    @pytest.mark.asyncio
    async def test_add_chunks_without_embeddings_skipped(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        chunks = [
            Chunk(id="c1", text="hello", session_id="s1", run_id="r1", embedding=None),
            Chunk(id="c2", text="world", session_id="s1", run_id="r1"),
        ]
        with _patch_db(mock_session):
            await store.add(chunks)
            # 3 DDL + 0 INSERT (all skipped)
            assert mock_session.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_add_mixed_embeddings(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        chunks = [
            Chunk(id="c1", text="with emb", session_id="s1", run_id="r1", embedding=[0.1] * 1024),
            Chunk(id="c2", text="no emb", session_id="s1", run_id="r1"),
        ]
        with _patch_db(mock_session):
            await store.add(chunks)
            # 3 DDL + 1 INSERT
            assert mock_session.execute.call_count == 4

    @pytest.mark.asyncio
    async def test_add_vector_literal_format(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        chunk = Chunk(id="c1", text="test", session_id="s1", run_id="r1", embedding=[1.0, 2.0, 3.0])
        with _patch_db(mock_session):
            await store.add([chunk])
            insert_call = mock_session.execute.call_args_list[3]
            params = insert_call[0][1]
            assert params["emb"] == "[1.0,2.0,3.0]"

    @pytest.mark.asyncio
    async def test_add_tags_array_format(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        chunk = Chunk(id="c1", text="test", session_id="s1", run_id="r1",
                       embedding=[0.1] * 1024, tags=["python", "bug"])
        with _patch_db(mock_session):
            await store.add([chunk])
            insert_call = mock_session.execute.call_args_list[3]
            params = insert_call[0][1]
            assert params["tags"] == "{python,bug}"

    @pytest.mark.asyncio
    async def test_add_empty_tags_format(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        chunk = Chunk(id="c1", text="test", session_id="s1", run_id="r1", embedding=[0.1] * 1024, tags=[])
        with _patch_db(mock_session):
            await store.add([chunk])
            insert_call = mock_session.execute.call_args_list[3]
            params = insert_call[0][1]
            assert params["tags"] == "{}"

    @pytest.mark.asyncio
    async def test_add_run_id_none_defaults_empty(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        chunk = Chunk(id="c1", text="test", session_id="s1", run_id=None, embedding=[0.1] * 1024)
        with _patch_db(mock_session):
            await store.add([chunk])
            insert_call = mock_session.execute.call_args_list[3]
            params = insert_call[0][1]
            assert params["rid"] == ""

    # ── search() tests ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_search_basic(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("result text", ["tag1"], "s1", "r1", 0.95),
        ]
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            results = await store.search([0.1] * 1024, top_k=5)
            assert len(results) == 1
            assert results[0]["text"] == "result text"
            assert results[0]["tags"] == ["tag1"]
            assert results[0]["score"] == 0.95
            assert results[0]["session_id"] == "s1"
            assert results[0]["run_id"] == "r1"

    @pytest.mark.asyncio
    async def test_search_with_session_id(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            await store.search([0.1] * 1024, session_id="s1")
            search_call = mock_session.execute.call_args_list[3]
            query = str(search_call[0][0])
            assert "session_id = :sid" in query

    @pytest.mark.asyncio
    async def test_search_with_tag_filter(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            await store.search([0.1] * 1024, tag_filter=["python", "bug"])
            search_call = mock_session.execute.call_args_list[3]
            query = str(search_call[0][0])
            params = search_call[0][1]
            assert "ANY(tags)" in query
            assert params["tag0"] == "python"
            assert params["tag1"] == "bug"

    @pytest.mark.asyncio
    async def test_search_with_session_and_tags(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            await store.search([0.1] * 1024, session_id="s1", tag_filter=["python"])
            search_call = mock_session.execute.call_args_list[3]
            query = str(search_call[0][0])
            assert "session_id = :sid" in query
            assert "ANY(tags)" in query

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            results = await store.search([0.1] * 1024)
            assert results == []

    @pytest.mark.asyncio
    async def test_search_result_with_none_tags(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("text", None, "s1", "r1", 0.8)]
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            results = await store.search([0.1] * 1024)
            assert results[0]["tags"] == []

    @pytest.mark.asyncio
    async def test_search_no_filters(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            await store.search([0.1] * 1024)
            search_call = mock_session.execute.call_args_list[3]
            query = str(search_call[0][0])
            assert "TRUE" in query

    @pytest.mark.asyncio
    async def test_search_multiple_results(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            ("text1", ["tag1"], "s1", "r1", 0.95),
            ("text2", ["tag2"], "s2", "r2", 0.80),
            ("text3", [], "s3", "r3", 0.70),
        ]
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            results = await store.search([0.1] * 1024)
            assert len(results) == 3
            assert results[0]["text"] == "text1"
            assert results[2]["tags"] == []

    # ── clear_session() tests ──────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_clear_session(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        with _patch_db(mock_session):
            await store.clear_session("s1")
            # 3 DDL in _ensure_table + 1 DELETE in clear_session
            assert mock_session.execute.call_count == 4
            # _ensure_table commits + clear_session commits
            assert mock_session.commit.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_session_query(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        with _patch_db(mock_session):
            await store.clear_session("session-abc")
            delete_call = mock_session.execute.call_args_list[3]
            query = str(delete_call[0][0])
            params = delete_call[0][1]
            assert "DELETE FROM vector_chunks" in query
            assert params["sid"] == "session-abc"

    # ── ensure_table integration tests ─────────────────────────────────

    @pytest.mark.asyncio
    async def test_add_ensure_table_called(self):
        store = PgVectorStore()
        assert store._initialized is False
        mock_session = AsyncMock()
        chunk = Chunk(id="c1", text="test", session_id="s1", run_id="r1", embedding=[0.1] * 1024)
        with _patch_db(mock_session):
            await store.add([chunk])
            assert store._initialized is True

    @pytest.mark.asyncio
    async def test_search_ensure_table_called(self):
        store = PgVectorStore()
        assert store._initialized is False
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            await store.search([0.1] * 1024)
            assert store._initialized is True


class TestSearchFormat:
    def test_dimension_constant(self):
        from rag.rag_embedding import EMBEDDING_DIM
        assert EMBEDDING_DIM == 1024
