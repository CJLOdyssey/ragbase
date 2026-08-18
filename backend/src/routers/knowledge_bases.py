"""Knowledge base API routes — multi-KB isolation CRUD."""

from typing import Any

from auth import get_user_id
from core.infra.logging_config import get_logger
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from pydantic.alias_generators import to_camel
from repository.knowledge_bases import (
    assign_asset_to_kb,
    create_kb,
    delete_kb,
    list_kbs,
    update_kb,
)

logger = get_logger(__name__)
router = APIRouter(tags=["knowledge-bases"])


class KBItem(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    id: str
    name: str
    description: str = ""
    created_at: str
    updated_at: str


class KBCreateIn(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    name: str
    description: str | None = None


class KBUpdateIn(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    name: str | None = None
    description: str | None = None


class AssignKBIn(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    knowledge_base_id: str | None


def _to_item(kb: Any) -> KBItem:
    return KBItem(
        id=kb.id,
        name=kb.name,
        description=kb.description or "",
        created_at=kb.created_at.isoformat() if kb.created_at else "",
        updated_at=kb.updated_at.isoformat() if kb.updated_at else "",
    )


@router.get("/api/knowledge-bases", response_model=list[KBItem])
async def list_knowledge_bases(request: Request) -> Any:
    """List the current user's knowledge bases."""
    user_id = get_user_id(request)
    kbs = await list_kbs(user_id)
    return [_to_item(kb) for kb in kbs]


@router.post("/api/knowledge-bases", response_model=KBItem, status_code=201)
async def create_knowledge_base(req: KBCreateIn, request: Request) -> Any:
    """Create a new knowledge base."""
    user_id = get_user_id(request)
    kb = await create_kb(user_id, req.name.strip()[:256], req.description or "")
    logger.info("KB created | user=%s | kb=%s", user_id, kb.id)
    return _to_item(kb)


@router.put("/api/knowledge-bases/{kb_id}", response_model=KBItem)
async def update_knowledge_base(kb_id: str, req: KBUpdateIn, request: Request) -> Any:
    """Update a knowledge base's name/description."""
    user_id = get_user_id(request)
    name = req.name.strip()[:256] if req.name is not None else None
    kb = await update_kb(kb_id, user_id, name=name, description=req.description)
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return _to_item(kb)


@router.delete("/api/knowledge-bases/{kb_id}")
async def delete_knowledge_base(kb_id: str, request: Request) -> Any:
    """Delete a knowledge base (nullifies assets' knowledge_base_id)."""
    user_id = get_user_id(request)
    deleted = await delete_kb(kb_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return {"deleted": True}


@router.post("/api/assets/{asset_id}/assign-kb")
async def assign_asset_kb(asset_id: str, req: AssignKBIn, request: Request) -> Any:
    """Assign an asset to a knowledge base (or null to unassign)."""
    user_id = get_user_id(request)
    success = await assign_asset_to_kb(asset_id, req.knowledge_base_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset or knowledge base not found")
    return {"assigned": True}
