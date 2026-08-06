"""Tests for RAG embedding provider (backend/rag/rag_embedding.py)."""

import json
from unittest.mock import MagicMock, patch

import pytest
from rag.rag_embedding import EMBEDDING_DIM, EmbeddingProvider, _fallback_embed


class TestEmbeddingProvider:
    def test_init_defaults(self):
        p = EmbeddingProvider(api_key="sk-test")
        assert p.api_key == "sk-test"
        assert p.model == "text-embedding-v3"

    def test_init_custom_model(self):
        p = EmbeddingProvider(api_key="sk", model="custom-model")
        assert p.model == "custom-model"

    def test_init_base_url(self):
        p = EmbeddingProvider(api_key="sk")
        assert "dashscope.aliyuncs.com" in p._base_url

    @pytest.mark.asyncio
    async def test_embed_no_api_key_fallback(self):
        p = EmbeddingProvider(api_key="")
        result = await p.embed(["hello", "world"])
        assert len(result) == 2
        assert len(result[0]) == EMBEDDING_DIM
        assert result[0] == [0.0] * EMBEDDING_DIM

    @pytest.mark.asyncio
    async def test_embed_query_no_api_key(self):
        p = EmbeddingProvider(api_key="")
        result = await p.embed_query("hello")
        assert len(result) == EMBEDDING_DIM

    def test__fallback_embed(self):
        result = _fallback_embed(["a", "b"])
        assert len(result) == 2
        assert len(result[0]) == EMBEDDING_DIM

    def test__fallback_embed_empty(self):
        result = _fallback_embed([])
        assert result == []

    @pytest.mark.asyncio
    async def test_embed_falls_back_on_exception(self):
        p = EmbeddingProvider(api_key="sk-test")
        with patch.object(p, "_embed_sync", side_effect=Exception("API down")):
            result = await p.embed(["test"])
            assert len(result) == 1
            assert result[0] == [0.0] * EMBEDDING_DIM

    @pytest.mark.asyncio
    async def test_embed_success(self):
        p = EmbeddingProvider(api_key="sk-test")
        fake_vectors = [[0.1] * EMBEDDING_DIM, [0.2] * EMBEDDING_DIM]
        with patch.object(p, "_embed_sync", return_value=fake_vectors):
            result = await p.embed(["hello", "world"])
            assert len(result) == 2
            assert result[0] == [0.1] * EMBEDDING_DIM
            assert result[1] == [0.2] * EMBEDDING_DIM

    @pytest.mark.asyncio
    async def test_embed_query_success(self):
        p = EmbeddingProvider(api_key="sk-test")
        fake_vector = [0.5] * EMBEDDING_DIM
        with patch.object(p, "_embed_sync", return_value=[fake_vector]):
            result = await p.embed_query("test query")
            assert result == fake_vector

    @pytest.mark.asyncio
    async def test_embed_single_text(self):
        p = EmbeddingProvider(api_key="sk-test")
        fake_vector = [0.3] * EMBEDDING_DIM
        with patch.object(p, "_embed_sync", return_value=[fake_vector]):
            result = await p.embed(["single text"])
            assert len(result) == 1
            assert result[0] == fake_vector

    def test_embed_sync_success(self):
        p = EmbeddingProvider(api_key="sk-test")
        response_data = {
            "output": {
                "embeddings": [
                    {"embedding": [0.1] * EMBEDDING_DIM},
                    {"embedding": [0.2] * EMBEDDING_DIM},
                ]
            }
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("rag.rag_embedding.urllib.request.urlopen", return_value=mock_response):
            result = p._embed_sync(["hello", "world"])
            assert len(result) == 2
            assert len(result[0]) == EMBEDDING_DIM
            assert result[0] == [0.1] * EMBEDDING_DIM

    def test_embed_sync_missing_output_key_fallback(self):
        p = EmbeddingProvider(api_key="sk-test")
        response_data = {"output": {}}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("rag.rag_embedding.urllib.request.urlopen", return_value=mock_response):
            result = p._embed_sync(["text"])
            assert len(result) == 1
            assert result[0] == [0.0] * EMBEDDING_DIM

    def test_embed_sync_missing_embeddings_key_fallback(self):
        p = EmbeddingProvider(api_key="sk-test")
        response_data = {"output": {"other_key": "value"}}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("rag.rag_embedding.urllib.request.urlopen", return_value=mock_response):
            result = p._embed_sync(["text"])
            assert len(result) == 1
            assert result[0] == [0.0] * EMBEDDING_DIM

    def test_embed_sync_empty_output_fallback(self):
        p = EmbeddingProvider(api_key="sk-test")
        response_data = {"output": None}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("rag.rag_embedding.urllib.request.urlopen", return_value=mock_response):
            result = p._embed_sync(["text"])
            assert len(result) == 1
            assert result[0] == [0.0] * EMBEDDING_DIM

    def test_embed_sync_request_headers(self):
        p = EmbeddingProvider(api_key="sk-test-key")
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "output": {"embeddings": [{"embedding": [0.1] * EMBEDDING_DIM}]}
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("rag.rag_embedding.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            p._embed_sync(["text"])
            req = mock_urlopen.call_args[0][0]
            assert req.get_header("Authorization") == "Bearer sk-test-key"
            assert req.get_header("Content-type") == "application/json"

    def test_embed_sync_exception_propagates(self):
        p = EmbeddingProvider(api_key="sk-test")
        with patch("rag.rag_embedding.urllib.request.urlopen", side_effect=Exception("network error")):
            with pytest.raises(Exception, match="network error"):
                p._embed_sync(["text"])

    @pytest.mark.asyncio
    async def test_embed_multiple_texts(self):
        p = EmbeddingProvider(api_key="sk-test")
        texts = [f"text_{i}" for i in range(5)]
        fake_vectors = [[float(i)] * EMBEDDING_DIM for i in range(5)]
        with patch.object(p, "_embed_sync", return_value=fake_vectors):
            result = await p.embed(texts)
            assert len(result) == 5

    def test_embed_sync_request_body(self):
        p = EmbeddingProvider(api_key="sk", model="custom-model")
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "output": {"embeddings": [{"embedding": [0.0] * EMBEDDING_DIM}]}
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("rag.rag_embedding.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            p._embed_sync(["hello"])
            req = mock_urlopen.call_args[0][0]
            body = json.loads(req.data.decode("utf-8"))
            assert body["model"] == "custom-model"
            assert body["input"]["texts"] == ["hello"]
            assert body["parameters"]["text_type"] == "document"
