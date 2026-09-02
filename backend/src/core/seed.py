"""Default data seeding — roles and admin user bootstrap."""

import os

from orm import RoleDB, UserDB, UserRoleDB
from sqlalchemy import select

from core.infra.database import get_session_factory
from core.infra.logging_config import get_logger

logger = get_logger(__name__)

# Bootstrap admin password. Dev/test default only — production must inject it.
DEFAULT_ADMIN_PASSWORD = "admin123"
ADMIN_PASSWORD_ENV = "SEED_ADMIN_PASSWORD"
ENVIRONMENT_ENV = "RAGBASE_ENV"


def resolve_admin_password() -> str:
    """Admin bootstrap password with environment-aware enforcement.

    - SEED_ADMIN_PASSWORD set → use it (any environment).
    - RAGBASE_ENV=production without it → fail loud: never ship the dev
      default admin password to production (CWE-798 / 12-factor config).
    - Otherwise (dev/test) → documented default with a warning.
    """
    password = os.environ.get(ADMIN_PASSWORD_ENV)
    if password:
        return password
    if os.environ.get(ENVIRONMENT_ENV, "development") == "production":
        raise RuntimeError(
            f"{ENVIRONMENT_ENV}=production requires {ADMIN_PASSWORD_ENV} to be "
            "set (refusing to seed the admin user with the dev default password)."
        )
    logger.warning(
        "%s not set — using the development default admin password "
        "(dev/test only; production must inject it)",
        ADMIN_PASSWORD_ENV,
    )
    return DEFAULT_ADMIN_PASSWORD


async def seed_default_roles_and_admin() -> None:
    """Create default roles (admin, member) and an admin user if they don't exist."""
    import asyncio

    import bcrypt

    async def _hash_password(password: str) -> str:
        # bcrypt is CPU-bound (~100-250ms) — keep it off the event loop.
        return await asyncio.to_thread(
            lambda: bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        )

    factory = get_session_factory()
    async with factory() as session:
        admin_role = await session.execute(select(RoleDB).where(RoleDB.name == "admin"))
        if not admin_role.scalar_one_or_none():
            session.add(RoleDB(name="admin", permissions={"all": True}))
        member_role = await session.execute(select(RoleDB).where(RoleDB.name == "member"))
        if not member_role.scalar_one_or_none():
            session.add(RoleDB(name="member", permissions={"read": True}))
        await session.commit()

    async with factory() as session:
        admin_user = await session.execute(select(UserDB).where(UserDB.username == "admin"))
        if not admin_user.scalar_one_or_none():
            admin_role_db = (
                await session.execute(select(RoleDB).where(RoleDB.name == "admin"))
            ).scalar_one_or_none()
            user = UserDB(
                username="admin",
                email="admin@example.com",
                password_hash=await _hash_password(resolve_admin_password()),
                is_active=True,
                is_verified=True,
            )
            session.add(user)
            await session.flush()
            if admin_role_db:
                session.add(UserRoleDB(user_id=user.id, role_id=admin_role_db.id))
            await session.commit()
