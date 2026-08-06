"""Default data seeding — roles and admin user bootstrap."""

import os

from orm import RoleDB, UserDB, UserRoleDB
from sqlalchemy import select

from core.infra.database import get_session_factory

# Bootstrap admin password. Dev default only — production must override via env.
DEFAULT_ADMIN_PASSWORD = "admin123"
ADMIN_PASSWORD_ENV = "SEED_ADMIN_PASSWORD"


async def seed_default_roles_and_admin() -> None:
    """Create default roles (admin, member) and an admin user if they don't exist."""
    import bcrypt

    factory = get_session_factory()
    async with factory() as session:
        admin_role = await session.execute(select(RoleDB).where(RoleDB.name == "admin"))
        if not admin_role.scalar_one_or_none():
            session.add(RoleDB(name="admin", permissions={"all": True}))
        member_role = await session.execute(select(RoleDB).where(RoleDB.name == "member"))
        if not member_role.scalar_one_or_none():
            session.add(RoleDB(name="member", permissions={"read": True}))
        await session.commit()

    admin_user = await session.execute(select(UserDB).where(UserDB.username == "admin"))
    if not admin_user.scalar_one_or_none():
        admin_role_db = (
            await session.execute(select(RoleDB).where(RoleDB.name == "admin"))
        ).scalar_one_or_none()
        user = UserDB(
            username="admin",
            email="admin@example.com",
            password_hash=bcrypt.hashpw(
                os.environ.get(ADMIN_PASSWORD_ENV, DEFAULT_ADMIN_PASSWORD).encode(),
                bcrypt.gensalt(),
            ).decode(),
            is_active=True,
            is_verified=True,
        )
        session.add(user)
        await session.flush()
        if admin_role_db:
            session.add(UserRoleDB(user_id=user.id, role_id=admin_role_db.id))
        await session.commit()


async def seed_builtin_tools() -> None:
    """Sync registered plugins from ToolRegistry into registered_tools table."""
    import json

    import thinking_tree.tools  # noqa: F401 — triggers registration
    from orm import RegisteredToolDB
    from sqlalchemy import select
    from thinking_tree.registry import registry

    from core.infra.database import get_session_factory

    factory = get_session_factory()
    plugins = registry.list_plugins()
    async with factory() as session:
        for p in plugins:
            name = p["tool_name"]
            result = await session.execute(
                select(RegisteredToolDB).where(
                    RegisteredToolDB.name == name,
                    RegisteredToolDB.is_builtin,
                )
            )
            if result.scalar_one_or_none():
                continue
            tool = RegisteredToolDB(
                name=name,
                category="builtin",
                description=p.get("description", ""),
                status="active",
                version="v1.0.0",
                parameters=json.dumps(p.get("config_schema") or {"type": "object", "properties": {}}),
                is_builtin=True,
            )
            session.add(tool)
        await session.commit()
