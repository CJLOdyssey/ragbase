"""Supplementary tests for admin_users router — coverage gap fill.

Tests search, pagination, role update, last-admin protection, and status toggle.
"""

import bcrypt
from core.infra.database import (
    RoleDB,
    UserDB,
    UserRoleDB,
    get_session_factory,
)
from fastapi.testclient import TestClient
from sqlalchemy import select

import pytest

pytestmark = pytest.mark.unit


async def _create_user(user_id: str, email: str, is_active: bool = True) -> None:
    factory = get_session_factory()
    async with factory() as session:
        existing = await session.execute(select(UserDB).where(UserDB.id == user_id))
        if existing.scalar_one_or_none():
            return
        session.add(
            UserDB(
                id=user_id,
                username=user_id,
                email=email,
                password_hash=bcrypt.hashpw(b"pass123", bcrypt.gensalt()).decode(),
                is_active=is_active,
                is_verified=True,
            )
        )
        await session.commit()


async def _assign_role(user_id: str, role_name: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        role = (
            await session.execute(select(RoleDB).where(RoleDB.name == role_name))
        ).scalar_one_or_none()
        if role is None:
            return
        existing = await session.execute(
            select(UserRoleDB).where(
                UserRoleDB.user_id == user_id, UserRoleDB.role_id == role.id
            )
        )
        if not existing.scalar_one_or_none():
            session.add(UserRoleDB(user_id=user_id, role_id=role.id))
            await session.commit()


async def _remove_role(user_id: str, role_name: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        role = (
            await session.execute(select(RoleDB).where(RoleDB.name == role_name))
        ).scalar_one_or_none()
        if role is None:
            return
        await session.execute(
            select(UserRoleDB).where(
                UserRoleDB.user_id == user_id, UserRoleDB.role_id == role.id
            )
        )
        from sqlalchemy import delete as sa_delete

        await session.execute(
            sa_delete(UserRoleDB).where(
                UserRoleDB.user_id == user_id, UserRoleDB.role_id == role.id
            )
        )
        await session.commit()


class TestListUsersSearch:
    async def test_search_by_email(self, client: TestClient):
        await _create_user("search-user", "findme@test.com")
        resp = client.get("/api/admin/users", params={"search": "findme"})
        assert resp.status_code == 200
        users = resp.json()["users"]
        assert any(u["email"] == "findme@test.com" for u in users)

    async def test_search_no_match(self, client: TestClient):
        resp = client.get("/api/admin/users", params={"search": "nonexistent_xyz"})
        assert resp.status_code == 200
        assert resp.json()["users"] == []

    async def test_pagination(self, client: TestClient):
        for i in range(5):
            await _create_user(f"page-u{i}", f"page{i}@test.com")
        resp = client.get("/api/admin/users", params={"page": 1, "page_size": 2})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["users"]) == 2
        assert body["total"] >= 5


class TestUpdateUserRole:
    async def test_role_not_found(self, client: TestClient):
        await _create_user("role-target", "rt@test.com")
        resp = client.put(
            "/api/admin/users/role-target/role",
            json={"role": "nonexistent_role_xyz"},
        )
        assert resp.status_code == 400

    async def test_demote_last_admin(self, client: TestClient):
        """The last admin cannot be demoted (OWASP A01/A07)."""
        # Ensure exactly 1 admin role assignment exists
        factory = get_session_factory()
        async with factory() as session:
            admin_role = (
                await session.execute(select(RoleDB).where(RoleDB.name == "admin"))
            ).scalar_one_or_none()
            # Remove any extra admin role assignments
            from sqlalchemy import delete as sa_delete

            if admin_role is not None:
                await session.execute(
                    sa_delete(UserRoleDB).where(
                        UserRoleDB.role_id == admin_role.id,
                        UserRoleDB.user_id != "admin-login",
                    )
                )
            await session.commit()

        resp = client.put(
            "/api/admin/users/admin-login/role",
            json={"role": "member"},
        )
        assert resp.status_code == 400
        assert "管理员" in resp.json()["detail"]
        # Restore admin role
        await _assign_role("admin-login", "admin")

    async def test_demote_admin_when_other_admins_exist(self, client: TestClient):
        """Admin can be demoted if another admin exists."""
        await _create_user("other-admin", "oa@test.com")
        await _assign_role("other-admin", "admin")
        resp = client.put(
            "/api/admin/users/admin-login/role",
            json={"role": "member"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "member"
        # Restore admin role
        await _assign_role("admin-login", "admin")

    async def test_promote_member_to_admin(self, client: TestClient):
        await _create_user("promote-target", "pt@test.com")
        resp = client.put(
            "/api/admin/users/promote-target/role",
            json={"role": "admin"},
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"


class TestUpdateUserStatus:
    async def test_deactivate_non_admin(self, client: TestClient):
        await _create_user("deact-target", "dt@test.com")
        resp = client.put(
            "/api/admin/users/deact-target/status",
            json={"is_active": False},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_deactivate_last_admin(self, client: TestClient):
        """The last active admin cannot be deactivated."""
        # Ensure exactly 1 active admin exists
        factory = get_session_factory()
        async with factory() as session:
            admin_role = (
                await session.execute(select(RoleDB).where(RoleDB.name == "admin"))
            ).scalar_one_or_none()
            from sqlalchemy import delete as sa_delete

            # Remove extra admin role assignments
            if admin_role is not None:
                await session.execute(
                    sa_delete(UserRoleDB).where(
                        UserRoleDB.role_id == admin_role.id,
                        UserRoleDB.user_id != "admin-login",
                    )
                )
            # Ensure admin-login is active
            user = await session.get(UserDB, "admin-login")
            if user:
                user.is_active = True
            await session.commit()

        resp = client.put(
            "/api/admin/users/admin-login/status",
            json={"is_active": False},
        )
        assert resp.status_code == 400
        assert "管理员" in resp.json()["detail"]
        # Restore active status
        factory = get_session_factory()
        async with factory() as session:
            user = await session.get(UserDB, "admin-login")
            if user:
                user.is_active = True
            await session.commit()

    async def test_deactivate_admin_when_other_active_admins_exist(
        self, client: TestClient
    ):
        await _create_user("admin2", "a2@test.com")
        await _assign_role("admin2", "admin")
        resp = client.put(
            "/api/admin/users/admin-login/status",
            json={"is_active": False},
        )
        assert resp.status_code == 200
        # Restore
        factory = get_session_factory()
        async with factory() as session:
            user = await session.get(UserDB, "admin-login")
            if user:
                user.is_active = True
            await session.commit()

    async def test_activate_user(self, client: TestClient):
        await _create_user("activate-target", "at@test.com", is_active=False)
        resp = client.put(
            "/api/admin/users/activate-target/status",
            json={"is_active": True},
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True
