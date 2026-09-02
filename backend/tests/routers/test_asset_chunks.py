"""Asset chunks preview API tests (unit, in-memory sqlite).

Uses the shared routers/conftest.py fixtures.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.unit


def _fake_asset(indexed: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        id="asset-1",
        name="产品手册.pdf",
        asset_type="document",
        indexed=indexed,
    )


class TestAssetChunks:
    async def test_missing_asset_returns_404(self, client):
        with patch("routers.assets.get_asset_for_user", return_value=None):
            response = client.get("/api/assets/asset-1/chunks")
        assert response.status_code == 404

    async def test_unindexed_asset_lists_manual_chunks(self, client):
        """Manual/QA chunks exist regardless of auto-index state."""
        with (
            patch(
                "routers.assets.get_asset_for_user",
                return_value=_fake_asset(indexed=False),
            ),
            patch(
                "rag.rag_store.PgVectorStore.list_asset_chunks",
                new_callable=AsyncMock,
                return_value=[
                    {
                        "id": "c1",
                        "enabled": True,
                        "text": "Q: 支持哪些部署?\nA: 云端与私有化",
                        "tags": [],
                        "metadata": {"qa": True},
                    }
                ],
            ),
        ):
            response = client.get("/api/assets/asset-1/chunks")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["text"] == "Q: 支持哪些部署?\nA: 云端与私有化"
        assert body[0]["metadata"]["qa"] is True

    async def test_returns_chunks_owner_scoped(self, client):
        mock_chunks = [
            {"text": "支持三种部署模式", "tags": ["spec"], "metadata": {"asset_name": "产品手册.pdf"}},
            {"text": "私有化部署需 4 核 8G", "tags": [], "metadata": {}},
        ]
        with (
            patch(
                "routers.assets.get_asset_for_user",
                return_value=_fake_asset(),
            ),
            patch(
                "rag.rag_store.PgVectorStore.list_asset_chunks",
                return_value=mock_chunks,
            ) as mock_list,
        ):
            response = client.get("/api/assets/asset-1/chunks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["text"] == "支持三种部署模式"
        assert data[0]["tags"] == ["spec"]
        assert data[1]["text"] == "私有化部署需 4 核 8G"
        assert mock_list.await_args_list[0].args == ("asset-1", "admin-login")


class TestQaBatchImport:
    async def test_batch_qa_imports_and_embeds(self, client):
        """Valid pairs embed once and store N manual chunks."""
        with (
            patch("routers.assets.get_asset_for_user", return_value=_fake_asset()),
            patch(
                "routers.assets._embed_for_asset",
                new_callable=AsyncMock,
                return_value=([[0.1] * 1024, [0.2] * 1024], "bge-m3"),
            ),
            patch(
                "rag.rag_store.PgVectorStore.add_manual_chunk",
                new_callable=AsyncMock,
                side_effect=["cid-1", "cid-2"],
            ),
        ):
            response = client.post(
                "/api/assets/asset-1/chunks/batch-qa",
                json={
                    "pairs": [
                        {"question": "支持哪些部署方式？", "answer": "云端与私有化"},
                        {"question": "最低配置？", "answer": "4 核 8G"},
                    ]
                },
            )
        assert response.status_code == 201
        assert response.json() == {"created": 2}

    async def test_batch_qa_rejects_empty_pair(self, client):
        response = client.post(
            "/api/assets/asset-1/chunks/batch-qa",
            json={"pairs": [{"question": "", "answer": "x"}]},
        )
        assert response.status_code == 422

    async def test_batch_qa_requires_owner(self, client):
        with patch("routers.assets.get_asset_for_user", return_value=None):
            response = client.post(
                "/api/assets/asset-1/chunks/batch-qa",
                json={"pairs": [{"question": "q", "answer": "a"}]},
            )
        assert response.status_code == 404


class TestAssetTags:
    async def test_tags_roundtrip(self, client):
        """Sanitized tags replace the asset's set (owner-scoped)."""
        from unittest.mock import AsyncMock

        asset = SimpleNamespace(
            id="asset-9",
            user_id="admin-login",
            name="手册.pdf",
            asset_type="document",
            indexed=True,
            tags=[],
            knowledge_base_id=None,
            source="upload",
            source_ref=None,
            updated_at=None,
            usage_count=0,
            size_bytes=1,
            storage_path="/tmp/x",
        )
        with (
            patch("routers.assets.get_asset_for_user", return_value=asset),
            patch(
                "repository.assets.update_asset_tags",
                new_callable=AsyncMock,
                side_effect=lambda aid, uid, tags: SimpleNamespace(
                    **{**asset.__dict__, "tags": tags}
                ),
            ),
            patch("routers.assets._chunk_counts_for", new_callable=AsyncMock, return_value={}),
        ):
            response = client.put(
                "/api/assets/asset-9/tags",
                json={"tags": ["API", "部署 ", "api"]},
            )
        assert response.status_code == 200
        body = response.json()
        assert body["tags"] == ["api", "部署"]
