"""Repository tests for memory and auth CRUD operations.

Uses conftest fixtures (db_engine) against in-memory SQLite.
"""

import uuid

from core.infra.database import RoleDB, get_session_factory
from repository.auth import (
    consume_refresh_token,
    create_refresh_token,
    create_user,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
    get_user_roles,
    increment_failed_logins,
    mark_user_verified,
    merge_guest_data,
    reset_failed_logins,
    revoke_all_user_tokens,
    revoke_token_family,
    update_password,
)
from repository.memory_repo import (
    clear_session_memories,
    create_memory_entry,
    delete_memory_entry,
    get_session_memories,
)
from repository.session_repo import create_session
from sqlalchemy import select

# ── Memory Tests ───────────────────────────────────────────────────────


class TestMemoryRepo:
    async def _create_test_data(self, db_engine):
        """Helper: create session and memory entry, return (session_id, memory)."""
        sess = await create_session(title="Mem Session")
        mem = await create_memory_entry(
            session_id=sess.id,
            run_id=str(uuid.uuid4()),
            agent_role="developer",
            content_type="decision",
            summary="Use FastAPI",
            details="Chose FastAPI over Flask for performance",
        )
        return sess.id, mem

    async def test_create_memory_entry(self, db_engine):
        sess = await create_session(title="Mem Test")
        mem = await create_memory_entry(
            session_id=sess.id,
            run_id=str(uuid.uuid4()),
            agent_role="pm",
            content_type="requirement",
            summary="Build login feature",
        )
        assert mem.id is not None
        assert mem.summary == "Build login feature"
        assert mem.agent_role == "pm"

    async def test_get_session_memories(self, db_engine):
        sess_id, _ = await self._create_test_data(db_engine)
        # Add another
        await create_memory_entry(
            session_id=sess_id,
            run_id=str(uuid.uuid4()),
            agent_role="developer",
            content_type="decision",
            summary="Second memory",
        )
        memories = await get_session_memories(sess_id)
        assert len(memories) == 2
        assert memories[0].summary == "Use FastAPI"

    async def test_get_session_memories_empty(self, db_engine):
        memories = await get_session_memories("nonexistent")
        assert memories == []

    async def test_delete_memory_entry(self, db_engine):
        _, mem = await self._create_test_data(db_engine)
        await delete_memory_entry(mem.id)
        memories = await get_session_memories(mem.session_id)
        assert len(memories) == 0

    async def test_delete_memory_entry_not_found(self, db_engine):
        await delete_memory_entry("nonexistent")

    async def test_clear_session_memories(self, db_engine):
        sess = await create_session(title="Clear Test")
        for i in range(3):
            await create_memory_entry(
                session_id=sess.id,
                run_id=str(uuid.uuid4()),
                agent_role="tester",
                content_type="bug",
                summary=f"Bug {i}",
            )
        await clear_session_memories(sess.id)
        memories = await get_session_memories(sess.id)
        assert memories == []


# ── Auth Tests ─────────────────────────────────────────────────────────


class TestAuthRepo:
    TEST_HASH = "$2b$12$LJ3m4ys3Lk0TSwHmGsm.KuYcK6mHdJR7FpGq0OEZHVmB8GskCf"
    TEST_EMAIL = "test@example.com"

    async def test_create_user(self, db_engine):
        user = await create_user(
            email=self.TEST_EMAIL,
            password_hash=self.TEST_HASH,
            username="testuser",
        )
        assert user.id is not None
        assert user.email == self.TEST_EMAIL
        assert user.username == "testuser"
        assert user.is_active is True

    async def test_create_user_default_username(self, db_engine):
        email = f"prefix_{uuid.uuid4().hex[:8]}@example.com"
        user = await create_user(email=email, password_hash=self.TEST_HASH)
        assert user.username == email.split("@")[0]

    async def test_get_user_by_email(self, db_engine):
        await create_user(email="lookup@example.com", password_hash=self.TEST_HASH)
        found = await get_user_by_email("lookup@example.com")
        assert found is not None
        assert found.email == "lookup@example.com"

    async def test_get_user_by_email_not_found(self, db_engine):
        result = await get_user_by_email("nonexistent@example.com")
        assert result is None

    async def test_get_user_by_id(self, db_engine):
        user = await create_user(email="byid@example.com", password_hash=self.TEST_HASH)
        found = await get_user_by_id(user.id)
        assert found is not None
        assert found.id == user.id

    async def test_get_user_by_id_not_found(self, db_engine):
        result = await get_user_by_id("nonexistent-id")
        assert result is None

    async def test_get_user_by_username(self, db_engine):
        uname = f"user_{uuid.uuid4().hex[:8]}"
        await create_user(
            email=f"{uname}@example.com", password_hash=self.TEST_HASH, username=uname
        )
        found = await get_user_by_username(uname)
        assert found is not None
        assert found.username == uname

    async def test_get_user_by_username_not_found(self, db_engine):
        result = await get_user_by_username("no_such_user")
        assert result is None

    async def _seed_member_role(self):
        """Ensure 'member' role exists in the test DB."""
        factory = get_session_factory()
        async with factory() as session:
            existing = await session.execute(select(RoleDB).where(RoleDB.name == "member"))
            if not existing.scalar_one_or_none():
                role = RoleDB(id=str(uuid.uuid4()), name="member")
                session.add(role)
                await session.commit()

    async def test_get_user_roles(self, db_engine):
        await self._seed_member_role()
        user = await create_user(email="roles@example.com", password_hash=self.TEST_HASH)
        roles = await get_user_roles(user.id)
        assert "member" in roles

    async def test_get_user_roles_nonexistent(self, db_engine):
        roles = await get_user_roles("nonexistent")
        assert roles == []

    async def test_mark_user_verified(self, db_engine):
        user = await create_user(
            email="verify@example.com", password_hash=self.TEST_HASH, is_verified=False
        )
        await mark_user_verified(user.id)
        found = await get_user_by_id(user.id)
        assert found is not None
        assert found.is_verified is True

    async def test_update_password(self, db_engine):
        user = await create_user(email="pwd@example.com", password_hash="old_hash")
        await update_password(user.id, "new_hash")
        found = await get_user_by_id(user.id)
        assert found is not None
        assert found.password_hash == "new_hash"

    async def test_increment_and_reset_failed_logins(self, db_engine):
        email = "logins@example.com"
        user = await create_user(email=email, password_hash=self.TEST_HASH)
        await increment_failed_logins(email)
        found = await get_user_by_id(user.id)
        assert found is not None
        assert found.failed_login_attempts >= 1

        await reset_failed_logins(email)
        found = await get_user_by_id(user.id)
        assert found is not None
        assert found.failed_login_attempts == 0

    async def test_refresh_token_flow(self, db_engine):
        user = await create_user(email="token@example.com", password_hash=self.TEST_HASH)
        token_str, family_id = await create_refresh_token(user.id, ttl_days=1)
        assert token_str is not None

        consumed_user, new_token = await consume_refresh_token(token_str)
        assert consumed_user is not None
        assert consumed_user.id == user.id

        consumed_user2, new_token2 = await consume_refresh_token(token_str)
        assert consumed_user2 is None
        assert new_token2 is None

    async def test_revoke_all_user_tokens(self, db_engine):
        user = await create_user(email="revoke@example.com", password_hash=self.TEST_HASH)
        for _ in range(3):
            await create_refresh_token(user.id, ttl_days=1)
        await revoke_all_user_tokens(user.id)

    async def test_revoke_token_family(self, db_engine):
        user = await create_user(email="family@example.com", password_hash=self.TEST_HASH)
        token_str, family_id = await create_refresh_token(user.id, ttl_days=1)
        await revoke_token_family(family_id)

    async def test_merge_guest_data(self, db_engine):
        guest = await create_user(email="guest@example.com", password_hash=self.TEST_HASH)
        target = await create_user(email="target@example.com", password_hash=self.TEST_HASH)
        await merge_guest_data({guest.id}, target.id)
