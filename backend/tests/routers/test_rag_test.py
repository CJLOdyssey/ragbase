"""RAG test-retrieval API tests (unit, in-memory sqlite).

Uses the shared routers/conftest.py fixtures.
"""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


class TestRagTestRetrieval:
    async def test_empty_query_rejected(self, client):
        response = client.post("/api/rag/test-retrieval", json={"query": "  "})
        assert response.status_code == 400

    async def test_no_embedding_returns_empty(self, client):
        """Without an embedding provider the pipeline yields no hits."""
        with patch(
            "routers.rag_test.retrieve_sources",
            return_value=[],
        ):
            response = client.post(
                "/api/rag/test-retrieval",
                json={"query": "产品支持哪些部署方式？"},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["originalQuery"] == "产品支持哪些部署方式？"
        assert data["query"] == "产品支持哪些部署方式？"
        assert data["hitCount"] == 0
        assert data["embeddingConfigured"] is False
        assert data["sources"] == []

    async def test_returns_structured_sources(self, client):
        mock_sources = [
            {
                "asset_id": "asset-1",
                "asset_name": "产品手册.pdf",
                "text": "支持私有化部署",
                "similarity": 0.72,
            },
        ]
        with patch(
            "routers.rag_test.retrieve_sources",
            return_value=mock_sources,
        ):
            response = client.post(
                "/api/rag/test-retrieval",
                json={"query": "支持哪些部署方式？", "top_k": 3},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["hitCount"] == 1
        assert data["sources"][0]["assetId"] == "asset-1"
        assert data["sources"][0]["assetName"] == "产品手册.pdf"
        assert data["sources"][0]["similarity"] == 0.72

    async def test_kb_scope_passes_asset_ids(self, client):
        """knowledgeBaseId resolves to asset ids forwarded to retrieve_sources."""
        with (
            patch(
                "routers.rag_test.list_asset_ids_by_kb",
                return_value=["asset-1", "asset-2"],
            ) as mock_kb,
            patch(
                "routers.rag_test.retrieve_sources",
                return_value=[],
            ) as mock_rs,
        ):
            response = client.post(
                "/api/rag/test-retrieval",
                json={"query": "部署方式", "knowledgeBaseId": "kb-1"},
            )
        assert response.status_code == 200
        mock_kb.assert_awaited_once_with("kb-1", "anonymous")
        mock_rs.assert_awaited_once()
        kwargs = mock_rs.await_args_list[0].kwargs
        assert kwargs is not None
        assert kwargs["asset_ids"] == ["asset-1", "asset-2"]
        assert kwargs["user_id"] == "anonymous"

    async def test_rewrite_applies(self, client):
        """rewrite=true rewrites before retrieval."""
        with (
            patch(
                "routers.rag_test.rewrite_query",
                return_value="私有化部署需要什么硬件？",
            ),
            patch(
                "routers.rag_test.retrieve_sources",
                return_value=[],
            ) as mock_rs,
        ):
            response = client.post(
                "/api/rag/test-retrieval",
                json={"query": "需要什么硬件？", "rewrite": True},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["originalQuery"] == "需要什么硬件？"
        assert data["query"] == "私有化部署需要什么硬件？"
        kwargs = mock_rs.await_args_list[0].kwargs
        assert kwargs is not None
        assert kwargs["query"] == "私有化部署需要什么硬件？"
