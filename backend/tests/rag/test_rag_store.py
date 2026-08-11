"""Tests for RAG vector store (backend/rag/rag_store.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rag.rag_chunking import Chunk
from rag.rag_store import PgVectorStore, _rrf_fuse


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


def _row(row_id: str, text: str, similarity: float, **extra: object) -> tuple[object, ...]:
    """Build a search result row: (id, text, tags, session_id, run_id, asset_id, metadata, similarity)."""
    return (
        row_id,
        text,
        extra.get("tags", ["tag1"]),
        extra.get("session_id", "s1"),
        extra.get("run_id", "r1"),
        extra.get("asset_id"),
        extra.get("metadata", {}),
        similarity,
    )


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
        await store.add([], user_id="u1")
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
            await store.add(chunks, user_id="u1")
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
            await store.add(chunks, user_id="u1")
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
            await store.add(chunks, user_id="u1")
            # 3 DDL + 1 INSERT
            assert mock_session.execute.call_count == 4

    @pytest.mark.asyncio
    async def test_add_vector_literal_format(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        chunk = Chunk(id="c1", text="test", session_id="s1", run_id="r1", embedding=[1.0, 2.0, 3.0])
        with _patch_db(mock_session):
            await store.add([chunk], user_id="u1")
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
            await store.add([chunk], user_id="u1")
            insert_call = mock_session.execute.call_args_list[3]
            params = insert_call[0][1]
            assert params["tags"] == ["python", "bug"]

    @pytest.mark.asyncio
    async def test_add_empty_tags_format(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        chunk = Chunk(id="c1", text="test", session_id="s1", run_id="r1", embedding=[0.1] * 1024, tags=[])
        with _patch_db(mock_session):
            await store.add([chunk], user_id="u1")
            insert_call = mock_session.execute.call_args_list[3]
            params = insert_call[0][1]
            assert params["tags"] == []

    @pytest.mark.asyncio
    async def test_add_run_id_none_defaults_empty(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        chunk = Chunk(id="c1", text="test", session_id="s1", run_id=None, embedding=[0.1] * 1024)
        with _patch_db(mock_session):
            await store.add([chunk], user_id="u1")
            insert_call = mock_session.execute.call_args_list[3]
            params = insert_call[0][1]
            assert params["rid"] == ""

    @pytest.mark.asyncio
    async def test_add_user_id_and_asset_metadata(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        chunk = Chunk(
            id="c1", text="test", session_id="s1", run_id=None,
            embedding=[0.1] * 1024,
            metadata={"asset_id": "a1", "asset_name": "手册"},
        )
        with _patch_db(mock_session):
            await store.add([chunk], user_id="u1")
            insert_call = mock_session.execute.call_args_list[3]
            params = insert_call[0][1]
            assert params["uid"] == "u1"
            assert params["aid"] == "a1"
            assert '"asset_name"' in params["meta"]

    # ── search() tests ─────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_search_basic(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [_row("c1", "result text", 0.95)]
        # 3 DDL + vector leg only (short query skips the lexical leg)
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            results = await store.search([0.1] * 1024, query_text="hi", user_id="u1", top_k=5)
            assert len(results) == 1
            assert results[0]["text"] == "result text"
            assert results[0]["tags"] == ["tag1"]
            assert results[0]["similarity"] == 0.95
            assert results[0]["session_id"] == "s1"
            assert results[0]["run_id"] == "r1"

    @pytest.mark.asyncio
    async def test_search_user_id_always_filtered(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            await store.search([0.1] * 1024, query_text="hi", user_id="u-42")
            search_call = mock_session.execute.call_args_list[3]
            query = str(search_call[0][0])
            params = search_call[0][1]
            assert "user_id = :uid" in query
            assert params["uid"] == "u-42"

    @pytest.mark.asyncio
    async def test_search_with_session_id(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            await store.search([0.1] * 1024, query_text="hi", user_id="u1", session_id="s1")
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
            await store.search([0.1] * 1024, query_text="hi", user_id="u1", tag_filter=["python", "bug"])
            search_call = mock_session.execute.call_args_list[3]
            query = str(search_call[0][0])
            params = search_call[0][1]
            assert "ANY(tags)" in query
            assert params["tag0"] == "python"
            assert params["tag1"] == "bug"

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            results = await store.search([0.1] * 1024, query_text="hi", user_id="u1")
            assert results == []

    @pytest.mark.asyncio
    async def test_search_with_min_score_appends_floor(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            await store.search(
                [0.1] * 1024, query_text="hi", user_id="u1", min_score=0.6
            )
            search_call = mock_session.execute.call_args_list[3]
            query = str(search_call[0][0])
            params = search_call[0][1]
            assert "min_score" in query
            assert params["min_score"] == 0.6
            # floor bound to the vector similarity expression, not bare column
            assert "(1 - (embedding <=> CAST(:emb AS vector))) >= :min_score" in query

    @pytest.mark.asyncio
    async def test_search_without_min_score_omits_floor(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            await store.search([0.1] * 1024, query_text="hi", user_id="u1")
            search_call = mock_session.execute.call_args_list[3]
            assert "min_score" not in str(search_call[0][0])

    @pytest.mark.asyncio
    async def test_search_result_with_none_tags(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [_row("c1", "text", 0.8, tags=None)]
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            results = await store.search([0.1] * 1024, query_text="hi", user_id="u1")
            assert results[0]["tags"] == []

    @pytest.mark.asyncio
    async def test_search_carries_asset_trace(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            _row("c1", "text", 0.9, asset_id="a1", metadata={"asset_name": "手册"})
        ]
        mock_session.execute = AsyncMock(side_effect=[None, None, None, mock_result])
        with _patch_db(mock_session):
            results = await store.search([0.1] * 1024, query_text="hi", user_id="u1")
            assert results[0]["asset_id"] == "a1"
            assert results[0]["metadata"]["asset_name"] == "手册"

    # ── hybrid search (lexical leg + RRF) tests ────────────────────────

    @pytest.mark.asyncio
    async def test_search_runs_lexical_leg_for_long_query(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        vec_result = MagicMock()
        vec_result.fetchall.return_value = [_row("c1", "text", 0.9)]
        lex_result = MagicMock()
        lex_result.fetchall.return_value = [_row("c2", "text", 0.7)]
        # 3 DDL + vec leg + SET LOCAL + lex leg
        mock_session.execute = AsyncMock(
            side_effect=[None, None, None, vec_result, None, lex_result]
        )
        with _patch_db(mock_session):
            results = await store.search([0.1] * 1024, query_text="SKU-2024-001", user_id="u1")
            lex_call = mock_session.execute.call_args_list[5]
            query = str(lex_call[0][0])
            assert "word_similarity" in query
            assert "text <% :q" in query
            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_search_skips_lexical_leg_for_short_query(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        vec_result = MagicMock()
        vec_result.fetchall.return_value = []
        mock_session.execute = AsyncMock(side_effect=[None, None, None, vec_result])
        with _patch_db(mock_session):
            await store.search([0.1] * 1024, query_text="hi", user_id="u1")
            # No 5th/6th execute: lexical leg skipped
            assert mock_session.execute.call_count == 4

    @pytest.mark.asyncio
    async def test_rrf_fuses_legs_by_rank(self):
        vec_leg = [
            {"id": "a", "text": "a", "similarity": 0.9},
            {"id": "b", "text": "b", "similarity": 0.8},
        ]
        lex_leg = [
            {"id": "b", "text": "b", "similarity": 0.7},
            {"id": "c", "text": "c", "similarity": 0.6},
        ]
        fused = _rrf_fuse([vec_leg, lex_leg], top_k=2)
        ids = [r["id"] for r in fused]
        # b appears in both legs -> highest RRF score
        assert ids == ["b", "a"]

    def test_rrf_respects_top_k(self):
        legs = [[{"id": f"c{i}", "text": str(i)} for i in range(10)]]
        fused = _rrf_fuse(legs, top_k=3)
        assert len(fused) == 3

    # ── clear_asset() / clear_session() tests ──────────────────────────

    @pytest.mark.asyncio
    async def test_clear_asset(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        with _patch_db(mock_session):
            await store.clear_asset("a1")
            delete_call = mock_session.execute.call_args_list[3]
            query = str(delete_call[0][0])
            params = delete_call[0][1]
            assert "DELETE FROM vector_chunks" in query
            assert "asset_id = :aid" in query
            assert params["aid"] == "a1"

    @pytest.mark.asyncio
    async def test_clear_session(self):
        store = PgVectorStore()
        mock_session = AsyncMock()
        with _patch_db(mock_session):
            await store.clear_session("s1")
            # 3 DDL in _ensure_table + 1 DELETE in clear_session
            assert mock_session.execute.call_count == 4
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
            await store.add([chunk], user_id="u1")
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
            await store.search([0.1] * 1024, query_text="hi", user_id="u1")
            assert store._initialized is True


class TestSearchFormat:
    def test_dimension_constant(self):
        from rag.rag_embedding import EMBEDDING_DIM
        assert EMBEDDING_DIM == 1024
