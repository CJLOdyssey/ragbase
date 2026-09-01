"""Tests for admin_users router.

client 以 admin-login（admin 角色）登录：断言真实权限语义——
管理员可列出用户、对不存在用户的操作返回 404，而不是恒真状态集合。
"""

from fastapi.testclient import TestClient


def test_list_users_endpoint(client: TestClient):
    """管理员可访问用户列表，且返回结构含 users 字段。"""
    response = client.get("/api/admin/users")
    assert response.status_code == 200
    assert "users" in response.json()


def test_update_user_role_endpoint(client: TestClient):
    """对不存在的用户修改角色 → 404（路由层契约）。"""
    response = client.put("/api/admin/users/test_user/role", json={"role": "admin"})
    assert response.status_code == 404


def test_update_user_status_endpoint(client: TestClient):
    """对不存在的用户修改状态 → 404（路由层契约）。"""
    response = client.put(
        "/api/admin/users/test_user/status", json={"is_active": False}
    )
    assert response.status_code == 404
