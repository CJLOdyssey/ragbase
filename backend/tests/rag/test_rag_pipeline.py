"""Tests for RAG pipeline (backend/rag/rag_pipeline.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rag import rag_pipeline
from rag.rag_chunking import Chunk


class TestRagPipeline:
    def test_get_rag_pipeline(self):
        p, store = rag_pipeline.get_rag_pipeline()
        assert store is not None

    def test_ensure_embedding_provider_set(self):
        rag_pipeline.ensure_embedding_provider(api_key="sk-test")
        p, _ = rag_pipeline.get_rag_pipeline()
        assert p is not None
        # Cleanup
        rag_pipeline.ensure_embedding_provider(api_key=None)

    def test_ensure_embedding_provider_none(self):
        rag_pipeline.ensure_embedding_provider(api_key="sk")
        rag_pipeline.ensure_embedding_provider(api_key=None)
        p, _ = rag_pipeline.get_rag_pipeline()
        assert p is None

    @pytest.mark.asyncio
    async def test_ingest_empty_messages(self):
        with patch.object(rag_pipeline._vector_store, "add", new_callable=AsyncMock):
            await rag_pipeline.ingest_session_messages("s1", "r1", [])
            rag_pipeline._vector_store.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_ingest_no_embedding_provider(self):
        rag_pipeline.ensure_embedding_provider(api_key=None)
        with patch.object(rag_pipeline._vector_store, "add", new_callable=AsyncMock):
            await rag_pipeline.ingest_session_messages(
                "s1", "r1", [{"content": "hello"}]
            )
            rag_pipeline._vector_store.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_retrieve_no_embedding_provider(self):
        rag_pipeline.ensure_embedding_provider(api_key=None)
        result = await rag_pipeline.retrieve_context("query", user_id="u1")
        assert result == ""

    @pytest.mark.asyncio
    async def test_retrieve_empty_results(self):
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "search", new_callable=AsyncMock, return_value=[]):
                result = await rag_pipeline.retrieve_context("query", user_id="u1")
                assert result == ""

    @pytest.mark.asyncio
    async def test_ingest_messages_success(self):
        provider = MagicMock()
        provider.embed = AsyncMock(return_value=[[0.1] * 1024, [0.2] * 1024])
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "add", new_callable=AsyncMock) as mock_add:
                messages = [
                    {"content": "Hello world"},
                    {"content": "This is a test message"},
                ]
                await rag_pipeline.ingest_session_messages("s1", "r1", messages, user_id="u1")
                mock_add.assert_called_once()
                assert mock_add.call_args.kwargs["user_id"] == "u1"
                chunks = mock_add.call_args[0][0]
                assert len(chunks) > 0
                assert all(isinstance(c, Chunk) for c in chunks)
                assert all(c.session_id == "s1" for c in chunks)
                assert all(c.run_id == "r1" for c in chunks)

    @pytest.mark.asyncio
    async def test_ingest_messages_with_empty_content(self):
        provider = MagicMock()
        provider.embed = AsyncMock(return_value=[[0.1] * 1024])
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "add", new_callable=AsyncMock) as mock_add:
                messages = [
                    {"content": ""},
                    {"content": None},
                    {"content": "Valid content here"},
                ]
                await rag_pipeline.ingest_session_messages("s1", "r1", messages)
                mock_add.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_messages_without_content_key(self):
        provider = MagicMock()
        provider.embed = AsyncMock(return_value=[[0.1] * 1024])
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "add", new_callable=AsyncMock) as mock_add:
                messages = [
                    {"role": "user"},  # no content key
                    {"role": "assistant", "content": "Valid content"},
                ]
                await rag_pipeline.ingest_session_messages("s1", "r1", messages)
                mock_add.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_with_results(self):
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        search_results = [
            {
                "text": "Result one",
                "similarity": 0.95,
                "tags": ["python", "test"],
                "session_id": "s1",
                "run_id": "r1",
                "asset_id": None,
                "metadata": {},
            },
            {
                "text": "Result two",
                "similarity": 0.80,
                "tags": [],
                "session_id": "s1",
                "run_id": "r1",
                "asset_id": None,
                "metadata": {},
            },
        ]
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "search", new_callable=AsyncMock, return_value=search_results):
                result = await rag_pipeline.retrieve_context("test query", user_id="u1", session_id="s1")
                assert "Result one" in result
                assert "Result two" in result
                assert "0.95" in result
                assert "0.80" in result
                assert "[python, test]" in result

    @pytest.mark.asyncio
    async def test_retrieve_includes_asset_trace(self):
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        search_results = [
            {
                "text": "Result from asset",
                "similarity": 0.90,
                "tags": [],
                "session_id": "asset:a1",
                "run_id": None,
                "asset_id": "a1",
                "metadata": {"asset_name": "运维手册"},
            },
        ]
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "search", new_callable=AsyncMock, return_value=search_results):
                result = await rag_pipeline.retrieve_context("query", user_id="u1")
                assert "Result from asset" in result
                assert "[素材: 运维手册]" in result

    @pytest.mark.asyncio
    async def test_retrieve_with_tags_filter(self):
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "search", new_callable=AsyncMock, return_value=[]) as mock_search:
                await rag_pipeline.retrieve_context("query", user_id="u1", tags=["python", "bug"])
                mock_search.assert_called_once()
                call_kwargs = mock_search.call_args[1]
                assert call_kwargs["user_id"] == "u1"
                assert call_kwargs["tag_filter"] == ["python", "bug"]

    @pytest.mark.asyncio
    async def test_retrieve_with_top_k(self):
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "search", new_callable=AsyncMock, return_value=[]) as mock_search:
                await rag_pipeline.retrieve_context("query", user_id="u1", top_k=10)
                call_kwargs = mock_search.call_args[1]
                assert call_kwargs["top_k"] == 10

    @pytest.mark.asyncio
    async def test_ingest_messages_chunk_embeddings_assigned(self):
        provider = MagicMock()
        provider.embed = AsyncMock(return_value=[[0.1] * 1024])
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "add", new_callable=AsyncMock) as mock_add:
                await rag_pipeline.ingest_session_messages("s1", "r1", [{"content": "test"}])
                chunks = mock_add.call_args[0][0]
                for chunk in chunks:
                    assert chunk.embedding is not None
                    assert len(chunk.embedding) == 1024

    @pytest.mark.asyncio
    async def test_retrieve_single_result_no_tags(self):
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        search_results = [
            {
                "text": "Single result",
                "similarity": 0.90,
                "tags": [],
                "session_id": "s1",
                "run_id": "r1",
                "asset_id": None,
                "metadata": {},
            },
        ]
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "search", new_callable=AsyncMock, return_value=search_results):
                result = await rag_pipeline.retrieve_context("query", user_id="u1")
                assert "Single result" in result
                assert "0.90" in result
                # No tags bracket for empty tags
                assert "[" not in result.split("---")[0] or result.count("[") == 0

    @pytest.mark.asyncio
    async def test_ingest_whole_text_too_short_for_chunks(self):
        provider = MagicMock()
        provider.embed = AsyncMock(return_value=[[0.1] * 1024])
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "add", new_callable=AsyncMock) as mock_add:
                # Messages with only whitespace content get filtered, empty result
                messages = [{"content": ""}]
                await rag_pipeline.ingest_session_messages("s1", "r1", messages)
                mock_add.assert_not_called()

    @pytest.mark.asyncio
    async def test_ingest_whitespace_only_content_returns_early(self):
        provider = MagicMock()
        provider.embed = AsyncMock(return_value=[[0.1] * 1024])
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "add", new_callable=AsyncMock) as mock_add:
                messages = [{"content": "   "}, {"content": "\n\t"}]
                await rag_pipeline.ingest_session_messages("s1", "r1", messages)
                mock_add.assert_not_called()
                provider.embed.assert_not_called()
