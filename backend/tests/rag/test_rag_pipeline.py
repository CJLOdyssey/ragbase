"""Tests for RAG pipeline (backend/rag/rag_pipeline.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rag import rag_pipeline
from rag.rag_chunking import Chunk


@pytest.fixture(autouse=True)
def _stub_embed_model_groups(monkeypatch):
    """Keep retrieval tests off the DB: default scope has one legacy cohort.

    Tests using a MagicMock store set their own ``embed_model_groups`` and
    therefore shadow this class-level stub.
    """
    monkeypatch.setattr(
        rag_pipeline.PgVectorStore,
        "embed_model_groups",
        AsyncMock(return_value=[None]),
        raising=True,
    )


@pytest.fixture(autouse=True)
def _reset_embedding_provider():
    """_embedding_provider 是模块级单例：断言中途失败也不能泄漏到同 worker 后续用例。"""
    yield
    rag_pipeline.ensure_embedding_provider(api_key=None)


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
    async def test_search_results_reranks_when_over_top_k(self):
        """_search_results: rerank=True with more results than top_k → rerank."""
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        store = MagicMock()
        store.embed_model_groups = AsyncMock(return_value=[None])
        store.search = AsyncMock(
            return_value=[
                {"asset_id": f"a-{i}", "metadata": {}, "score": 1 / (60 + i + 1)}
                for i in range(3)
            ]
        )
        with (
            patch.object(rag_pipeline, "_embedding_provider", provider),
            patch.object(rag_pipeline, "_vector_store", store),
            patch.object(rag_pipeline, "_rerank_results", new_callable=AsyncMock) as m_rerank,
        ):
            out = await rag_pipeline._search_results(
                "query", user_id="u1", top_k=2, rerank=True
            )
        m_rerank.assert_awaited_once_with("query", store.search.return_value, 2)
        assert out is m_rerank.return_value

    @pytest.mark.asyncio
    async def test_search_results_skips_rerank_within_top_k(self):
        """rerank=True but results ≤ top_k → no rerank call."""
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        store = MagicMock()
        store.embed_model_groups = AsyncMock(return_value=[None])
        store.search = AsyncMock(return_value=[{"asset_id": "a-1"}])
        with (
            patch.object(rag_pipeline, "_embedding_provider", provider),
            patch.object(rag_pipeline, "_vector_store", store),
            patch.object(rag_pipeline, "_rerank_results", new_callable=AsyncMock) as m_rerank,
        ):
            await rag_pipeline._search_results("query", user_id="u1", top_k=5, rerank=True)
        m_rerank.assert_not_awaited()

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
    async def test_retrieve_sources_structured(self):
        """retrieve_sources：结构化来源（asset_id/asset_name/text/similarity）供引文 UI。"""
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        search_results = [
            {
                "asset_id": "a1",
                "metadata": {"asset_name": "手册"},
                "text": "chunk text",
                "similarity": 0.9,
                "tags": [],
            },
        ]
        with (
            patch.object(rag_pipeline, "_embedding_provider", provider),
            patch.object(
                rag_pipeline._vector_store,
                "search",
                new_callable=AsyncMock,
                return_value=search_results,
            ),
        ):
            sources = await rag_pipeline.retrieve_sources(
                "query", user_id="u1", retrieval_method="lexical"
            )

        assert sources == [
            {"asset_id": "a1", "asset_name": "手册", "text": "chunk text", "similarity": 0.9}
        ]

    @pytest.mark.asyncio
    async def test_search_multi_cohort_merges_by_score(self):
        """多 embedding cohort：逐模型取配置/embed/检索，按 score 合并排序。"""
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        store = MagicMock()
        store.embed_model_groups = AsyncMock(return_value=["model-a", "model-b"])
        store.search = AsyncMock(
            side_effect=[
                [{"asset_id": "a1", "metadata": {}, "score": 0.8, "similarity": 0.8}],
                [{"asset_id": "b1", "metadata": {}, "score": 0.6, "similarity": 0.6}],
            ]
        )
        cfg = {"api_key": "k", "model": "model-a", "base_url": "https://x"}
        provider_inst = MagicMock()
        provider_inst.embed_query = AsyncMock(return_value=[0.1] * 1024)
        provider_factory = MagicMock(return_value=provider_inst)
        with (
            patch.object(rag_pipeline, "_embedding_provider", provider),
            patch.object(rag_pipeline, "_vector_store", store),
            patch("repository.keys.get_embedding_config", new=AsyncMock(return_value=cfg)),
            patch.object(rag_pipeline, "EmbeddingProvider", provider_factory),
        ):
            out = await rag_pipeline._search_results("query", user_id="u1")

        assert [r["asset_id"] for r in out] == ["a1", "b1"]
        assert store.search.await_count == 2
        # 每个 cohort 独立检索（向量只在自身模型空间内比较）。
        search_kwargs = [c.kwargs for c in store.search.await_args_list]
        assert search_kwargs[0]["embed_model"] == "model-a"
        assert search_kwargs[1]["embed_model"] == "model-b"

    @pytest.mark.asyncio
    async def test_search_multi_cohort_skips_missing_config(self):
        """某 cohort 无 embedding 配置 → 跳过该组，其余正常合并。"""
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        store = MagicMock()
        store.embed_model_groups = AsyncMock(return_value=["model-a", "model-b"])
        store.search = AsyncMock(
            return_value=[{"asset_id": "b1", "metadata": {}, "score": 0.6}]
        )
        cfg = {"api_key": "k", "model": "model-a", "base_url": "https://x"}
        provider_inst = MagicMock()
        provider_inst.embed_query = AsyncMock(return_value=[0.1] * 1024)
        provider_factory = MagicMock(return_value=provider_inst)
        with (
            patch.object(rag_pipeline, "_embedding_provider", provider),
            patch.object(rag_pipeline, "_vector_store", store),
            # model-a 无配置被跳过；model-b 有配置正常检索。
            patch(
                "repository.keys.get_embedding_config",
                new=AsyncMock(side_effect=[None, cfg]),
            ),
            patch.object(rag_pipeline, "EmbeddingProvider", provider_factory),
        ):
            out = await rag_pipeline._search_results("query", user_id="u1")

        assert [r["asset_id"] for r in out] == ["b1"]
        store.search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_multi_cohort_embedding_failure_skips_group(self):
        """某 cohort embed 失败 → 该组跳过，不中断整体检索。"""
        store = MagicMock()
        store.embed_model_groups = AsyncMock(return_value=["model-a", "model-b"])
        store.search = AsyncMock(
            return_value=[{"asset_id": "b1", "metadata": {}, "score": 0.6}]
        )
        cfg = {"api_key": "k", "model": "model-a", "base_url": "https://x"}
        provider_inst = MagicMock()
        provider_inst.embed_query = AsyncMock(
            side_effect=[RuntimeError("embed down"), [0.1] * 1024]
        )
        provider_factory = MagicMock(return_value=provider_inst)
        with (
            patch.object(rag_pipeline, "_vector_store", store),
            patch("repository.keys.get_embedding_config", new=AsyncMock(return_value=cfg)),
            patch.object(rag_pipeline, "EmbeddingProvider", provider_factory),
        ):
            out = await rag_pipeline._search_results("query", user_id="u1")

        assert [r["asset_id"] for r in out] == ["b1"]
        store.search.assert_awaited_once()

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
    async def test_retrieve_default_min_score_applied(self):
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "search", new_callable=AsyncMock, return_value=[]) as mock_search:
                await rag_pipeline.retrieve_context("query", user_id="u1")
                call_kwargs = mock_search.call_args[1]
                assert call_kwargs["min_score"] == rag_pipeline.DEFAULT_MIN_SCORE

    @pytest.mark.asyncio
    async def test_retrieve_explicit_min_score_override(self):
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "search", new_callable=AsyncMock, return_value=[]) as mock_search:
                await rag_pipeline.retrieve_context("query", user_id="u1", min_score=0.7)
                call_kwargs = mock_search.call_args[1]
                assert call_kwargs["min_score"] == 0.7

    @pytest.mark.asyncio
    async def test_retrieve_min_score_disabled(self):
        provider = MagicMock()
        provider.embed_query = AsyncMock(return_value=[0.1] * 1024)
        with patch.object(rag_pipeline, "_embedding_provider", provider):
            with patch.object(rag_pipeline._vector_store, "search", new_callable=AsyncMock, return_value=[]) as mock_search:
                await rag_pipeline.retrieve_context("query", user_id="u1", min_score=None)
                call_kwargs = mock_search.call_args[1]
                assert call_kwargs["min_score"] is None

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
                # 空 tags：不渲染 tag 段（相似度标签本身含方括号，故不能断言不含 "["）。
                assert "[python, test]" not in result

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
