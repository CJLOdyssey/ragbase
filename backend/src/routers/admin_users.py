"""Admin user management API routes — requires admin role."""

from typing import Any

from auth.auth_rbac import require_role
from core.infra.database import RoleDB, UserDB, UserRoleDB, get_session_factory
from core.infra.logging_config import get_logger
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from pydantic.alias_generators import to_camel
from repository.auth import get_user_roles
from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select

logger = get_logger(__name__)
router = APIRouter(tags=["admin-users"])


class UserInfo(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    user_id: str
    email: str
    name: str
    role: str
    is_active: bool
    created_at: str


class UserListOut(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    users: list[UserInfo]
    total: int


class UpdateRoleIn(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    role: str


class UpdateStatusIn(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    is_active: bool


@router.get("/api/admin/users", response_model=UserListOut)
async def list_users(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    user: Any = Depends(require_role("admin")),
) -> Any:
    """List all users (admin only)."""
    factory = get_session_factory()
    async with factory() as session:
        # Build query with optional search filter
        query = select(UserDB)
        count_query = select(func.count()).select_from(UserDB)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (UserDB.email.ilike(search_pattern)) | (UserDB.username.ilike(search_pattern))
            )
            count_query = count_query.where(
                (UserDB.email.ilike(search_pattern)) | (UserDB.username.ilike(search_pattern))
            )

        # Get total count
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.order_by(UserDB.created_at.desc()).offset(offset).limit(page_size)

        result = await session.execute(query)
        users_db = result.scalars().all()

        users = []
        for u in users_db:
            roles = await get_user_roles(u.id)
            role = roles[0] if roles else "member"
            users.append(
                UserInfo(
                    user_id=u.id,
                    email=u.email,
                    name=u.username,
                    role=role,
                    is_active=u.is_active,
                    created_at=u.created_at.isoformat() if u.created_at else "",
                )
            )

        return UserListOut(users=users, total=total)


@router.put("/api/admin/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    req: UpdateRoleIn,
    request: Request,
    admin: Any = Depends(require_role("admin")),
) -> Any:
    """Update a user's role (admin only)."""
    factory = get_session_factory()
    async with factory() as session:
        user = await session.get(UserDB, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        # Find the role
        role_result = await session.execute(select(RoleDB).where(RoleDB.name == req.role))
        role = role_result.scalar_one_or_none()
        if role is None:
            raise HTTPException(status_code=400, detail=f"Role '{req.role}' not found")

        # Remove existing roles and add the new one
        await session.execute(sa_delete(UserRoleDB).where(UserRoleDB.user_id == user_id))
        session.add(UserRoleDB(user_id=user_id, role_id=role.id))
        await session.commit()

        logger.info("Admin %s updated user %s role to %s", admin.id, user_id, req.role)
        return {"updated": True, "user_id": user_id, "role": req.role}


@router.put("/api/admin/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    req: UpdateStatusIn,
    request: Request,
    admin: Any = Depends(require_role("admin")),
) -> Any:
    """Toggle a user's active status (admin only)."""
    factory = get_session_factory()
    async with factory() as session:
        user = await session.get(UserDB, user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_active = req.is_active
        await session.commit()
        logger.info("Admin %s updated user %s status to %s", admin.id, user_id, req.is_active)
        return {"updated": True, "user_id": user_id, "is_active": req.is_active}
