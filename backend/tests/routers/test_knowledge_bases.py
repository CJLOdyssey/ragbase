"""Tests for knowledge_bases router."""

from datetime import UTC, datetime

import pytest
from core.infra.database import AssetDB, get_session_factory
from fastapi.testclient import TestClient
from routers.models import ModelInfo


@pytest.fixture(autouse=True)
def _fake_embedding_models(monkeypatch):
    """Seed one embedding-capable model for embed-model validation."""

    async def fake_get_user_models(user_id: str) -> list[ModelInfo]:
        return [
            ModelInfo(
                id="bge-m3", label="bge-m3", provider="siliconflow", type="embedding"
            )
        ]

    monkeypatch.setattr("routers.models.get_user_models", fake_get_user_models)


@pytest.mark.asyncio
async def test_list_knowledge_bases_empty(client: TestClient):
    """Should return empty list when no knowledge bases exist."""
    response = client.get("/api/knowledge-bases")
    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_create_knowledge_base(client: TestClient):
    """Should create a new knowledge base."""
    response = client.post(
        "/api/knowledge-bases",
        json={
            "name": "Test KB",
            "description": "Test description",
            "embedModel": "bge-m3",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test KB"
    assert data["description"] == "Test description"
    assert data["embedModel"] == "bge-m3"
    assert "id" in data
    assert "createdAt" in data
    assert "updatedAt" in data


@pytest.mark.asyncio
async def test_create_knowledge_base_requires_embed_model(client: TestClient):
    """Missing embed_model should be rejected (422)."""
    response = client.post(
        "/api/knowledge-bases", json={"name": "No Model KB"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_knowledge_base_rejects_unknown_model(client: TestClient):
    """A model not declared on any active key must be rejected (400)."""
    response = client.post(
        "/api/knowledge-bases",
        json={"name": "KB", "embedModel": "not-a-real-model"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_knowledge_base_truncates_name(client: TestClient):
    """Should truncate name to 256 characters."""
    long_name = "x" * 300
    response = client.post(
        "/api/knowledge-bases",
        json={"name": long_name, "description": "Test", "embedModel": "bge-m3"},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["name"]) == 256


@pytest.mark.asyncio
async def test_create_knowledge_base_strips_whitespace(client: TestClient):
    """Should strip whitespace from name."""
    response = client.post(
        "/api/knowledge-bases",
        json={"name": "  Test KB  ", "description": "Test", "embedModel": "bge-m3"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test KB"


@pytest.mark.asyncio
async def test_update_knowledge_base(client: TestClient):
    """Should update knowledge base name and description."""
    # Create a KB first
    create_response = client.post(
        "/api/knowledge-bases",
        json={"name": "Original", "description": "Original desc", "embedModel": "bge-m3"},
    )
    kb_id = create_response.json()["id"]

    # Update it
    response = client.put(
        f"/api/knowledge-bases/{kb_id}",
        json={"name": "Updated", "description": "Updated desc"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["description"] == "Updated desc"
    assert data["embedModel"] == "bge-m3"


@pytest.mark.asyncio
async def test_update_knowledge_base_partial(client: TestClient):
    """Should update only provided fields."""
    # Create a KB first
    create_response = client.post(
        "/api/knowledge-bases",
        json={"name": "Original", "description": "Original desc", "embedModel": "bge-m3"},
    )
    kb_id = create_response.json()["id"]

    # Update only name
    response = client.put(
        f"/api/knowledge-bases/{kb_id}",
        json={"name": "Updated"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["description"] == "Original desc"


@pytest.mark.asyncio
async def test_update_knowledge_base_not_found(client: TestClient):
    """Should return 404 when updating non-existent KB."""
    response = client.put(
        "/api/knowledge-bases/nonexistent",
        json={"name": "Updated"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_knowledge_base(client: TestClient):
    """Should delete knowledge base."""
    # Create a KB first
    create_response = client.post(
        "/api/knowledge-bases",
        json={"name": "To Delete", "description": "Test", "embedModel": "bge-m3"},
    )
    kb_id = create_response.json()["id"]

    # Delete it
    response = client.delete(f"/api/knowledge-bases/{kb_id}")
    assert response.status_code == 200
    data = response.json()
    assert data == {"deleted": True}

    # Verify it's gone
    list_response = client.get("/api/knowledge-bases")
    kbs = list_response.json()
    assert not any(kb["id"] == kb_id for kb in kbs)


@pytest.mark.asyncio
async def test_delete_knowledge_base_not_found(client: TestClient):
    """Should return 404 when deleting non-existent KB."""
    response = client.delete("/api/knowledge-bases/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assign_asset_to_knowledge_base(client: TestClient):
    """Should assign an asset to a knowledge base."""
    # Create a KB
    kb_response = client.post(
        "/api/knowledge-bases",
        json={"name": "Test KB", "description": "Test", "embedModel": "bge-m3"},
    )
    kb_id = kb_response.json()["id"]

    # Create an asset

    factory = get_session_factory()
    async with factory() as session:
        asset = AssetDB(
            id="test-asset-123",
            user_id="admin-login",
            name="Test Asset",
            asset_type="text",
            storage_path="/tmp/test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(asset)
        await session.commit()

    # Assign asset to KB
    response = client.post(
        "/api/assets/test-asset-123/assign-kb",
        json={"knowledgeBaseId": kb_id}
    )
    assert response.status_code == 200
    data = response.json()
    assert data == {"assigned": True}


@pytest.mark.asyncio
async def test_unassign_asset_from_knowledge_base(client: TestClient):
    """Should unassign an asset from knowledge base (set to null)."""
    # Create an asset

    factory = get_session_factory()
    async with factory() as session:
        asset = AssetDB(
            id="test-asset-456",
            user_id="admin-login",
            name="Test Asset",
            asset_type="text",
            storage_path="/tmp/test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(asset)
        await session.commit()

    # Unassign asset (set knowledge_base_id to null)
    response = client.post(
        "/api/assets/test-asset-456/assign-kb",
        json={"knowledgeBaseId": None}
    )
    assert response.status_code == 200
    data = response.json()
    assert data == {"assigned": True}


@pytest.mark.asyncio
async def test_assign_asset_not_found(client: TestClient):
    """Should return 404 when assigning non-existent asset."""
    response = client.post(
        "/api/assets/nonexistent/assign-kb",
        json={"knowledgeBaseId": "some-kb-id"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_knowledge_base_with_parser_config(client: TestClient):
    """parserConfig round-trips through create → response."""
    response = client.post(
        "/api/knowledge-bases",
        json={
            "name": "Cfg KB",
            "embedModel": "bge-m3",
            "parserConfig": {"chunkSize": 256, "overlap": 32},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["parserConfig"] == {"chunk_size": 256, "overlap": 32}


@pytest.mark.asyncio
async def test_create_knowledge_base_rejects_bad_parser_config(client: TestClient):
    """Out-of-range chunking params must be rejected (422)."""
    response = client.post(
        "/api/knowledge-bases",
        json={
            "name": "Bad Cfg",
            "embedModel": "bge-m3",
            "parserConfig": {"chunkSize": 10, "overlap": 5},
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_assign_assets_kb_batch(client: TestClient):
    """Should assign many assets to one KB in one request."""
    kb_response = client.post(
        "/api/knowledge-bases",
        json={"name": "Batch KB", "embedModel": "bge-m3"},
    )
    kb_id = kb_response.json()["id"]

    factory = get_session_factory()
    async with factory() as session:
        for i in range(3):
            session.add(
                AssetDB(
                    id=f"batch-asset-{i}",
                    user_id="admin-login",
                    name=f"Asset {i}",
                    asset_type="text",
                    storage_path="/tmp/test",
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
            )
        await session.commit()

    response = client.post(
        "/api/assets/assign-kb/batch",
        json={
            "assetIds": ["batch-asset-0", "batch-asset-1", "batch-asset-2"],
            "knowledgeBaseId": kb_id,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["assignedCount"] == 3
    assert data["skippedCount"] == 0


@pytest.mark.asyncio
async def test_assign_assets_kb_batch_skips_foreign_assets(client: TestClient):
    """Assets not owned by the caller are skipped and reported."""
    kb_response = client.post(
        "/api/knowledge-bases",
        json={"name": "Batch KB 2", "embedModel": "bge-m3"},
    )
    kb_id = kb_response.json()["id"]

    factory = get_session_factory()
    async with factory() as session:
        session.add(
            AssetDB(
                id="mine-1",
                user_id="admin-login",
                name="Mine",
                asset_type="text",
                storage_path="/tmp/test",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        await session.commit()

    response = client.post(
        "/api/assets/assign-kb/batch",
        json={
            "assetIds": ["mine-1", "nonexistent", "foreign-asset"],
            "knowledgeBaseId": kb_id,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["assignedCount"] == 1
    assert data["skippedCount"] == 2
    assert set(data["skippedIds"]) == {"nonexistent", "foreign-asset"}


@pytest.mark.asyncio
async def test_assign_assets_kb_batch_unknown_kb(client: TestClient):
    """Unknown KB id must 404."""
    response = client.post(
        "/api/assets/assign-kb/batch",
        json={"assetIds": ["a-1"], "knowledgeBaseId": "no-such-kb"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assign_assets_kb_batch_rejects_empty(client: TestClient):
    """Empty asset_ids must be rejected (422)."""
    response = client.post(
        "/api/assets/assign-kb/batch",
        json={"assetIds": [], "knowledgeBaseId": "kb-x"},
    )
    assert response.status_code == 422
