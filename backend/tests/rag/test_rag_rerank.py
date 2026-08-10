"""Tests for cross-encoder reranking (backend/rag/rag_rerank.py + pipeline hook)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from rag.rag_rerank import RerankProvider


def _mock_response(payload: dict) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = json.dumps(payload).encode("utf-8")
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestRerankProvider:
    def test_rerank_request_shape(self):
        p = RerankProvider(api_key="sk", base_url="https://api.siliconflow.cn/v1")
        resp = _mock_response({"results": [{"index": 1, "relevance_score": 0.9}]})
        with patch("rag.rag_rerank.urllib.request.urlopen", return_value=resp) as mock_urlopen:
            indices = p._rerank_sync("q", ["a", "b"], top_n=1)
        assert indices == [1]
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://api.siliconflow.cn/v1/rerank"
        body = json.loads(req.data.decode("utf-8"))
        assert body["model"] == "BAAI/bge-reranker-v2-m3"
        assert body["query"] == "q"
        assert body["documents"] == ["a", "b"]
        assert body["top_n"] == 1

    def test_rerank_missing_results_raises(self):
        p = RerankProvider(api_key="sk", base_url="https://x/v1")
        resp = _mock_response({"results": []})
        with patch("rag.rag_rerank.urllib.request.urlopen", return_value=resp):
            with pytest.raises(RuntimeError, match="missing results"):
                p._rerank_sync("q", ["a"], 1)

    @pytest.mark.asyncio
    async def test_rerank_empty_documents_noop(self):
        p = RerankProvider(api_key="sk", base_url="https://x/v1")
        assert await p.rerank("q", [], 5) == []


class TestPipelineRerank:
    @pytest.mark.asyncio
    async def test_rerank_results_reorders(self):
        from rag.rag_pipeline import _rerank_results

        results = [
            {"text": "a", "similarity": 0.9},
            {"text": "b", "similarity": 0.8},
            {"text": "c", "similarity": 0.7},
        ]
        cfg = {
            "api_key": "sk",
            "base_url": "https://api.siliconflow.cn/v1",
            "model": "BAAI/bge-reranker-v2-m3",
        }
        with (
            patch("repository.keys.get_rerank_config", AsyncMock(return_value=cfg)),
            patch("rag.rag_rerank.RerankProvider") as provider_cls,
        ):
            provider_cls.return_value.rerank = AsyncMock(return_value=[2, 0])
            out = await _rerank_results("q", results, top_k=2)
        assert [r["text"] for r in out] == ["c", "a"]

    @pytest.mark.asyncio
    async def test_rerank_no_config_keeps_order(self):
        from rag.rag_pipeline import _rerank_results

        results = [{"text": "a"}, {"text": "b"}]
        with patch("repository.keys.get_rerank_config", AsyncMock(return_value=None)):
            out = await _rerank_results("q", results, top_k=1)
        assert [r["text"] for r in out] == ["a", "b"]
