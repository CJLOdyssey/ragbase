"""Tests for knowledge_bases router."""

from datetime import UTC, datetime

import pytest
from core.infra.database import AssetDB, get_session_factory
from fastapi.testclient import TestClient


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
        json={"name": "Test KB", "description": "Test description"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test KB"
    assert data["description"] == "Test description"
    assert "id" in data
    assert "createdAt" in data
    assert "updatedAt" in data


@pytest.mark.asyncio
async def test_create_knowledge_base_truncates_name(client: TestClient):
    """Should truncate name to 256 characters."""
    long_name = "x" * 300
    response = client.post(
        "/api/knowledge-bases",
        json={"name": long_name, "description": "Test"}
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["name"]) == 256


@pytest.mark.asyncio
async def test_create_knowledge_base_strips_whitespace(client: TestClient):
    """Should strip whitespace from name."""
    response = client.post(
        "/api/knowledge-bases",
        json={"name": "  Test KB  ", "description": "Test"}
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
        json={"name": "Original", "description": "Original desc"}
    )
    kb_id = create_response.json()["id"]

    # Update it
    response = client.put(
        f"/api/knowledge-bases/{kb_id}",
        json={"name": "Updated", "description": "Updated desc"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["description"] == "Updated desc"


@pytest.mark.asyncio
async def test_update_knowledge_base_partial(client: TestClient):
    """Should update only provided fields."""
    # Create a KB first
    create_response = client.post(
        "/api/knowledge-bases",
        json={"name": "Original", "description": "Original desc"}
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
        json={"name": "To Delete", "description": "Test"}
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
        json={"name": "Test KB", "description": "Test"}
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
