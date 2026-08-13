"""Unit tests for database seeding (backend/core/seed.py)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from core.seed import resolve_admin_password, seed_default_roles_and_admin

# =============================================================================
# resolve_admin_password
# =============================================================================


class TestResolveAdminPassword:
    def test_env_set_wins_in_any_environment(self, monkeypatch):
        monkeypatch.setenv("SEED_ADMIN_PASSWORD", "S3cureProdPass!")
        monkeypatch.setenv("RAGBASE_ENV", "production")
        assert resolve_admin_password() == "S3cureProdPass!"

    def test_production_without_env_raises(self, monkeypatch):
        monkeypatch.delenv("SEED_ADMIN_PASSWORD", raising=False)
        monkeypatch.setenv("RAGBASE_ENV", "production")
        with pytest.raises(RuntimeError, match="SEED_ADMIN_PASSWORD"):
            resolve_admin_password()

    def test_dev_without_env_uses_default(self, monkeypatch):
        monkeypatch.delenv("SEED_ADMIN_PASSWORD", raising=False)
        monkeypatch.setenv("RAGBASE_ENV", "development")
        assert resolve_admin_password() == "admin123"

    def test_env_unset_defaults_to_development(self, monkeypatch):
        monkeypatch.delenv("SEED_ADMIN_PASSWORD", raising=False)
        monkeypatch.delenv("RAGBASE_ENV", raising=False)
        assert resolve_admin_password() == "admin123"


# =============================================================================
# seed_default_roles_and_admin
# =============================================================================


def _make_mock_role_result(existing_names: list[str]) -> MagicMock:
    """Return a mock that returns a role row only for names in existing_names."""
    result = MagicMock()
    row = MagicMock()
    if len(existing_names) > 0:
        row.name = existing_names[0]
    result.scalar_one_or_none.return_value = row if existing_names else None
    return result


class TestSeedDefaultRolesAndAdmin:
    @pytest.mark.asyncio
    async def test_creates_roles_and_admin_when_empty(self):
        """When no roles/users exist, both are created."""
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()))

        # Every select returns no existing rows
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

        with (
            patch("core.seed.get_session_factory", return_value=mock_factory),
            patch("core.seed.select", side_effect=lambda *a: MagicMock()),
            patch("bcrypt.hashpw", return_value=b"$2b$12$hashedpassword"),
            patch("bcrypt.gensalt", return_value=b"$2b$12$globalsalt"),
        ):
            await seed_default_roles_and_admin()

        # Should have added admin role, member role, and admin user
        assert mock_session.add.call_count >= 3
        assert mock_session.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_idempotent_when_roles_and_admin_exist(self):
        """When roles and admin user already exist, nothing new is added."""
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()))

        # Simulate existing admin role, member role, and admin user
        existing_role = MagicMock()
        existing_role.name = "admin"
        mock_session.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=existing_role))

        with (
            patch("core.seed.get_session_factory", return_value=mock_factory),
            patch("core.seed.select", side_effect=lambda *a: MagicMock()),
        ):
            await seed_default_roles_and_admin()

        # No new adds (roles exist, user exists)
        mock_session.add.assert_not_called()
        assert mock_session.commit.call_count >= 1

    @pytest.mark.asyncio
    async def test_creates_admin_user_when_roles_exist_but_user_missing(self):
        """Roles exist but admin user does not — user gets created."""
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()))

        existing_role = MagicMock()
        existing_role.name = "admin"
        existing_role.id = 42

        # First two execute calls: admin role exists, member role exists
        # Third call: admin user doesn't exist
        # Fourth call: fetch admin role for FK assignment
        mock_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_role)),  # admin role
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_role)),  # member role
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # admin user (missing)
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_role)),  # admin role for FK
        ]

        with (
            patch("core.seed.get_session_factory", return_value=mock_factory),
            patch("core.seed.select", side_effect=lambda *a: MagicMock()),
            patch("bcrypt.hashpw", return_value=b"$2b$12$hashed"),
            patch("bcrypt.gensalt", return_value=b"$2b$12$salt"),
        ):
            await seed_default_roles_and_admin()

        # Admin user added + UserRoleDB link added
        add_calls = mock_session.add.call_args_list
        assert len(add_calls) >= 2  # user + user_role

    @pytest.mark.asyncio
    async def test_uses_seed_admin_password_env_when_set(self, monkeypatch):
        """Admin password comes from SEED_ADMIN_PASSWORD env, not the hardcoded default."""
        monkeypatch.setenv("SEED_ADMIN_PASSWORD", "S3cureProdPass!")
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()))

        # admin role exists, member role exists, admin user missing, admin role for FK
        existing_role = MagicMock()
        existing_role.name = "admin"
        existing_role.id = 42
        mock_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_role)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_role)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_role)),
        ]

        hashed = b"$2b$12$envpassword"
        with (
            patch("core.seed.get_session_factory", return_value=mock_factory),
            patch("core.seed.select", side_effect=lambda *a: MagicMock()),
            patch("bcrypt.hashpw", return_value=hashed) as mock_hashpw,
            patch("bcrypt.gensalt", return_value=b"$2b$12$salt"),
        ):
            await seed_default_roles_and_admin()

        mock_hashpw.assert_called_once_with(b"S3cureProdPass!", b"$2b$12$salt")

    @pytest.mark.asyncio
    async def test_defaults_to_admin123_when_env_unset(self, monkeypatch):
        """Without SEED_ADMIN_PASSWORD, the dev default admin123 is used."""
        monkeypatch.delenv("SEED_ADMIN_PASSWORD", raising=False)
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()))

        existing_role = MagicMock()
        existing_role.name = "admin"
        existing_role.id = 42
        mock_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_role)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_role)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=existing_role)),
        ]

        with (
            patch("core.seed.get_session_factory", return_value=mock_factory),
            patch("core.seed.select", side_effect=lambda *a: MagicMock()),
            patch("bcrypt.hashpw", return_value=b"$2b$12$default") as mock_hashpw,
            patch("bcrypt.gensalt", return_value=b"$2b$12$salt"),
        ):
            await seed_default_roles_and_admin()

        mock_hashpw.assert_called_once_with(b"admin123", b"$2b$12$salt")

    @pytest.mark.asyncio
    async def test_no_role_fk_when_admin_role_not_found(self):
        """Admin role doesn't exist after creation — user is added without FK link."""
        mock_session = AsyncMock()
        mock_factory = MagicMock(return_value=MagicMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()))

        # admin role doesn't exist → created, member role doesn't exist → created
        # admin user doesn't exist → created, admin role lookup returns None
        mock_session.execute.side_effect = [
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # admin role
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # member role
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # admin user
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),  # admin role for FK (not found)
        ]

        with (
            patch("core.seed.get_session_factory", return_value=mock_factory),
            patch("core.seed.select", side_effect=lambda *a: MagicMock()),
            patch("bcrypt.hashpw", return_value=b"$2b$12$hashed"),
            patch("bcrypt.gensalt", return_value=b"$2b$12$salt"),
        ):
            await seed_default_roles_and_admin()

        # Roles + user added, but no UserRoleDB link (admin_role_db is None)
        add_calls = mock_session.add.call_args_list
        assert len(add_calls) == 3  # admin role + member role + user
        from orm.auth import UserRoleDB

        for call in add_calls:
            assert not isinstance(call[0][0], UserRoleDB)
