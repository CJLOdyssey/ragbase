"""Tests for RAG embedding provider (backend/rag/rag_embedding.py).

Contract: embedding failures RAISE — zero-vector fallback is forbidden because
it silently poisons the vector store with fake embeddings.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from rag.rag_embedding import EMBEDDING_DIM, EmbeddingProvider


class TestEmbeddingProvider:
    def test_init_defaults(self):
        # 没有默认值：model 未配置就是 None，绝不隐式假设供应商
        p = EmbeddingProvider(api_key="sk-test")
        assert p.api_key == "sk-test"
        assert p.model is None

    def test_embed_sync_without_model_raises(self):
        p = EmbeddingProvider(api_key="sk-test")
        with pytest.raises(RuntimeError, match="EMBEDDING_MODEL"):
            p._embed_sync(["hello"])

    def test_init_custom_model(self):
        p = EmbeddingProvider(api_key="sk", model="custom-model")
        assert p.model == "custom-model"

    def test_init_base_url(self):
        p = EmbeddingProvider(api_key="sk")
        assert p.base_url is None

    def test_default_dashscope_endpoint_constant(self):
        from rag.rag_embedding import DASHSCOPE_EMBEDDING_URL
        assert "dashscope.aliyuncs.com" in DASHSCOPE_EMBEDDING_URL

    def test_init_openai_compat_base_url(self):
        p = EmbeddingProvider(api_key="sk", base_url="https://api.siliconflow.cn/v1")
        assert p.base_url == "https://api.siliconflow.cn/v1"

    def test_embed_sync_openai_compat_request(self):
        """base_url set → OpenAI-compatible: POST {base}/embeddings, input list."""
        p = EmbeddingProvider(
            api_key="sk-test", model="BAAI/bge-m3", base_url="https://api.siliconflow.cn/v1"
        )
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "data": [{"embedding": [0.1] * EMBEDDING_DIM}]
        }).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("rag.rag_embedding.urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
            result = p._embed_sync(["hello"])
            req = mock_urlopen.call_args[0][0]
            assert req.full_url == "https://api.siliconflow.cn/v1/embeddings"
            body = json.loads(req.data.decode("utf-8"))
            assert body["model"] == "BAAI/bge-m3"
            assert body["input"] == ["hello"]
            assert "text_type" not in body
        assert len(result[0]) == EMBEDDING_DIM

    def test_embed_sync_openai_compat_missing_data_raises(self):
        p = EmbeddingProvider(api_key="sk", model="test-model", base_url="https://api.siliconflow.cn/v1")
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"data": []}).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("rag.rag_embedding.urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(RuntimeError, match="missing embeddings"):
                p._embed_sync(["text"])

    @pytest.mark.asyncio
    async def test_embed_no_api_key_raises(self):
        p = EmbeddingProvider(api_key="")
        with pytest.raises(RuntimeError, match="API key"):
            await p.embed(["hello", "world"])

    @pytest.mark.asyncio
    async def test_embed_query_no_api_key_raises(self):
        p = EmbeddingProvider(api_key="")
        with pytest.raises(RuntimeError, match="API key"):
            await p.embed_query("hello")

    @pytest.mark.asyncio
    async def test_embed_raises_on_exception(self):
        p = EmbeddingProvider(api_key="sk-test")
        with patch.object(p, "_embed_sync", side_effect=Exception("API down")):
            with pytest.raises(Exception, match="API down"):
                await p.embed(["test"])

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
        p = EmbeddingProvider(api_key="sk-test", model="test-model")
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

    def test_embed_sync_missing_output_key_raises(self):
        p = EmbeddingProvider(api_key="sk-test", model="test-model")
        response_data = {"output": {}}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("rag.rag_embedding.urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(RuntimeError, match="missing embeddings"):
                p._embed_sync(["text"])

    def test_embed_sync_missing_embeddings_key_raises(self):
        p = EmbeddingProvider(api_key="sk-test", model="test-model")
        response_data = {"output": {"other_key": "value"}}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("rag.rag_embedding.urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(RuntimeError, match="missing embeddings"):
                p._embed_sync(["text"])

    def test_embed_sync_empty_output_raises(self):
        p = EmbeddingProvider(api_key="sk-test", model="test-model")
        response_data = {"output": None}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(response_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("rag.rag_embedding.urllib.request.urlopen", return_value=mock_response):
            with pytest.raises(RuntimeError, match="missing embeddings"):
                p._embed_sync(["text"])

    def test_embed_sync_request_headers(self):
        p = EmbeddingProvider(api_key="sk-test-key", model="test-model")
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
        p = EmbeddingProvider(api_key="sk-test", model="test-model")
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
