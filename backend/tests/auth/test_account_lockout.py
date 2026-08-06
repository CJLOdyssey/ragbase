"""Tests for account lockout feature (REQ-AUTH-008).

Tests the lockout mechanism after 5 failed login attempts:
- increment_failed_logins increments counter
- Account locks after 5 failures
- Locked account returns appropriate error
- Successful login resets failed attempts
- reset_failed_logins unlocks account
"""

from datetime import UTC, datetime, timedelta

import pytest
from repository.auth import (
    create_user,
    get_user_by_email,
    increment_failed_logins,
    reset_failed_logins,
)


@pytest.mark.requirement("REQ-AUTH-008")
class TestAccountLockout:
    """Test account lockout after multiple failed login attempts."""

    async def test_increment_failed_logins(self, db_engine):
        """Failed login counter increments on each failure."""
        await create_user(
            email="lockout_test@example.com",
            password_hash="hashed_password",
            is_verified=True,
        )

        count = await increment_failed_logins("lockout_test@example.com")
        assert count == 1

        count = await increment_failed_logins("lockout_test@example.com")
        assert count == 2

        count = await increment_failed_logins("lockout_test@example.com")
        assert count == 3

    async def test_lockout_after_5_failures(self, db_engine):
        """Account locks after 5 failed login attempts."""
        await create_user(
            email="lockout5@example.com",
            password_hash="hashed_password",
            is_verified=True,
        )

        # Simulate 5 failed attempts
        for _i in range(5):
            count = await increment_failed_logins("lockout5@example.com")

        assert count == 5

        # Verify account is locked
        locked_user = await get_user_by_email("lockout5@example.com")
        assert locked_user is not None
        assert locked_user.locked_until is not None
        # The locked_until should be in the future (15 minutes from now)
        # SQLite stores naive datetimes, so compare with naive datetime
        # locked_until is stored as UTC, so add UTC offset for comparison
        locked_until_utc = locked_user.locked_until.replace(tzinfo=UTC) if locked_user.locked_until.tzinfo is None else locked_user.locked_until
        assert locked_until_utc > datetime.now(UTC)

    async def test_lockout_duration_is_15_minutes(self, db_engine):
        """Locked account remains locked for 15 minutes."""
        await create_user(
            email="lockout15@example.com",
            password_hash="hashed_password",
            is_verified=True,
        )

        # Trigger lockout
        for _ in range(5):
            await increment_failed_logins("lockout15@example.com")

        locked_user = await get_user_by_email("lockout15@example.com")
        assert locked_user is not None
        assert locked_user.locked_until is not None

        # Check that lockout is approximately 15 minutes from now
        # Add UTC timezone to locked_until for proper comparison
        locked_until_utc = locked_user.locked_until.replace(tzinfo=UTC) if locked_user.locked_until.tzinfo is None else locked_user.locked_until
        time_diff = locked_until_utc - datetime.now(UTC)
        assert 14 * 60 <= time_diff.total_seconds() <= 16 * 60

    async def test_successful_login_resets_failed_attempts(self, db_engine):
        """Successful login resets failed login counter to 0."""
        await create_user(
            email="reset_test@example.com",
            password_hash="hashed_password",
            is_verified=True,
        )

        # Simulate 3 failed attempts
        for _ in range(3):
            await increment_failed_logins("reset_test@example.com")

        # Verify counter is 3
        user_before = await get_user_by_email("reset_test@example.com")
        assert user_before.failed_login_attempts == 3

        # Simulate successful login (resets counter)
        await reset_failed_logins("reset_test@example.com")

        # Verify counter is reset
        user_after = await get_user_by_email("reset_test@example.com")
        assert user_after.failed_login_attempts == 0

    async def test_reset_failed_logins_unlocks_account(self, db_engine):
        """reset_failed_logins unlocks a locked account."""
        await create_user(
            email="unlock_test@example.com",
            password_hash="hashed_password",
            is_verified=True,
        )

        # Trigger lockout
        for _ in range(5):
            await increment_failed_logins("unlock_test@example.com")

        # Verify account is locked
        locked_user = await get_user_by_email("unlock_test@example.com")
        assert locked_user.locked_until is not None

        # Unlock account
        await reset_failed_logins("unlock_test@example.com")

        # Verify account is unlocked
        unlocked_user = await get_user_by_email("unlock_test@example.com")
        assert unlocked_user.locked_until is None
        assert unlocked_user.failed_login_attempts == 0

    async def test_increment_for_nonexistent_user(self, db_engine):
        """Incrementing failed logins for nonexistent user returns 0."""
        count = await increment_failed_logins("nonexistent@example.com")
        assert count == 0

    async def test_reset_for_nonexistent_user(self, db_engine):
        """Resetting failed logins for nonexistent user doesn't raise."""
        # Should not raise
        await reset_failed_logins("nonexistent@example.com")

    async def test_failed_attempts_not_locked_until_4(self, db_engine):
        """Account is not locked with only 4 failed attempts."""
        await create_user(
            email="not_locked@example.com",
            password_hash="hashed_password",
            is_verified=True,
        )

        for _ in range(4):
            await increment_failed_logins("not_locked@example.com")

        user_not_locked = await get_user_by_email("not_locked@example.com")
        assert user_not_locked.failed_login_attempts == 4
        assert user_not_locked.locked_until is None


@pytest.mark.integration
@pytest.mark.requirement("REQ-AUTH-008")
class TestLoginWithLockout:
    """Test login endpoint with lockout behavior."""

    async def test_login_returns_locked_error(self, test_client):
        """Login returns error when account is locked."""
        # This test requires the full app setup with database
        # The lockout check happens in the login endpoint
        from repository.auth import create_user

        await create_user(
            email="locked_login@example.com",
            password_hash="hashed_password",
            is_verified=True,
        )

        # Manually lock the account
        from core.infra.database import get_session_factory
        from orm.auth import UserDB
        from sqlalchemy import update

        factory = get_session_factory()
        async with factory() as session:
            await session.execute(
                update(UserDB)
                .where(UserDB.email == "locked_login@example.com")
                .values(
                    failed_login_attempts=5,
                    locked_until=datetime.now(UTC) + timedelta(minutes=15),
                )
            )
            await session.commit()

        # Try to login
        response = await test_client.post(
            "/api/auth/login",
            json={"email": "locked_login@example.com", "password": "wrong_password"},
        )

        # Should return lockout error (423 Locked)
        assert response.status_code == 423
        data = response.json()
        # Check for lockout message in nested error structure
        assert "锁定" in str(data)
