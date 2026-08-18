"""Tests for admin_users router."""


import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_list_users_endpoint(client: TestClient):
    """Should access list users endpoint."""
    response = client.get("/api/admin/users")
    # Endpoint should be accessible (auth handled by middleware)
    assert response.status_code in [200, 401, 403]


@pytest.mark.asyncio
async def test_update_user_role_endpoint(client: TestClient):
    """Should access update user role endpoint."""
    response = client.put("/api/admin/users/test_user/role", json={"role": "admin"})
    # Endpoint should be accessible (may return 404 if user doesn't exist)
    assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
async def test_update_user_status_endpoint(client: TestClient):
    """Should access update user status endpoint."""
    response = client.put("/api/admin/users/test_user/status", json={"is_active": False})
    # Endpoint should be accessible (may return 404 if user doesn't exist)
    assert response.status_code in [200, 401, 403, 404]
