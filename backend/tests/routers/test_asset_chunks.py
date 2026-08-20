"""Asset chunks preview API tests (unit, in-memory sqlite).

Uses the shared routers/conftest.py fixtures.
"""

from types import SimpleNamespace
from unittest.mock import patch

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

    async def test_unindexed_asset_returns_empty(self, client):
        with patch(
            "routers.assets.get_asset_for_user",
            return_value=_fake_asset(indexed=False),
        ):
            response = client.get("/api/assets/asset-1/chunks")
        assert response.status_code == 200
        assert response.json() == []

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
        assert mock_list.await_args_list[0].args == ("asset-1", "anonymous")
