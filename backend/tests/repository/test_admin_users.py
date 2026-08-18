"""Admin users router tests."""

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
