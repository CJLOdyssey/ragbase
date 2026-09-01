"""Admin 前置依赖的仓储函数测试。

本文件覆盖 admin 用户管理路由依赖的 repository.auth 基础函数
（create_user/get_user_by_id）；管理员特有操作（用户列表、角色变更）
由 routers 层 admin 路由测试覆盖（B4 阶段）。
"""

import pytest

pytestmark = pytest.mark.unit

from repository.auth import create_user, get_user_by_id


class TestAdminUsersRepository:
    async def test_create_user(self):
        """Should create a user."""
        user = await create_user(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
        )

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"

    async def test_get_user_by_id(self):
        """Should get user by id."""
        user = await create_user(
            email="test@example.com",
            username="testuser",
            password_hash="hashed_password",
        )

        retrieved = await get_user_by_id(user.id)
        assert retrieved is not None
        assert retrieved.email == "test@example.com"

    async def test_get_user_by_id_not_found(self):
        """Should return None when user not found."""
        retrieved = await get_user_by_id("nonexistent_id")
        assert retrieved is None
