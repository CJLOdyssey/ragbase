"""Knowledge base API routes — multi-KB isolation CRUD."""

from typing import Any

from auth import get_user_id
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel
from repository.knowledge_bases import (
    assign_asset_to_kb,
    change_indexing_config,
    count_assets_by_kb,
    create_kb,
    delete_kb,
    list_kbs,
    update_kb,
)

logger = get_logger(__name__)
router = APIRouter(tags=["knowledge-bases"])


class KBParserConfig(BaseModel):
    """Chunking parameters applied at (re)index — engine-honest fields only."""

    model_config = {"alias_generator": to_camel, "populate_by_name": True}

    chunk_size: int = Field(default=512, ge=50, le=2000)
    overlap: int = Field(default=64, ge=0, le=500)


class KBItem(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    id: str
    name: str
    description: str = ""
    embed_model: str | None = None
    parser_config: dict[str, Any] | None = None
    asset_count: int = 0
    created_at: str
    updated_at: str


class KBCreateIn(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    name: str
    description: str | None = None
    embed_model: str
    parser_config: KBParserConfig | None = None


class KBUpdateIn(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    name: str | None = None
    description: str | None = None
    embed_model: str | None = None
    parser_config: KBParserConfig | None = None


class AssignKBIn(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    knowledge_base_id: str | None


def _to_item(kb: Any, asset_count: int = 0) -> KBItem:
    return KBItem(
        id=kb.id,
        name=kb.name,
        description=kb.description or "",
        embed_model=getattr(kb, "embed_model", None),
        parser_config=getattr(kb, "parser_config", None),
        asset_count=asset_count,
        created_at=kb.created_at.isoformat() if kb.created_at else "",
        updated_at=kb.updated_at.isoformat() if kb.updated_at else "",
    )


async def _validate_embed_model(user_id: str, model: str) -> None:
    """Ensure the model is declared (type=embedding) on one of the user's active keys.

    Vectors in a KB must share one embedding space — binding an unknown or
    non-embedding model would silently poison retrieval.
    """
    from routers.models import embedding_model_ids, get_user_models

    valid = embedding_model_ids(await get_user_models(user_id))
    if model not in valid:
        raise error_response(
            ErrorCode.INVALID_REQUEST,
            detail="嵌入模型不可用：请先在 API 管理中配置该模型的嵌入能力",
        )


async def _apply_indexing_change(
    kb_id: str,
    user_id: str,
    embed_model: str | None = None,
    parser_config: dict[str, Any] | None = None,
) -> int:
    """Apply a reindex-worthy config change (model and/or chunking params).

    Purges + requeues the KB's indexed assets when either changed. Returns
    the number of assets queued for rebuild (0 when unchanged). Last-write-
    wins: applying again mid-rebuild simply re-invalidates.
    """
    updated, affected = await change_indexing_config(
        kb_id, user_id, embed_model=embed_model, parser_config=parser_config
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    if not affected:
        return 0

    from rag.rag_store import PgVectorStore
    from tasks.registry import index_asset as index_asset_task

    await PgVectorStore().clear_assets(affected)
    for asset_id in affected:
        index_asset_task.delay(asset_id, user_id)
    logger.info(
        "KB indexing config changed | user=%s | kb=%s | reindexing=%d",
        user_id, kb_id, len(affected),
    )
    return len(affected)


@router.get("/api/knowledge-bases", response_model=list[KBItem])
async def list_knowledge_bases(request: Request) -> Any:
    """List the current user's knowledge bases."""
    user_id = get_user_id(request)
    kbs = await list_kbs(user_id)
    asset_counts = await count_assets_by_kb(user_id)
    return [_to_item(kb, asset_counts.get(kb.id, 0)) for kb in kbs]


@router.post("/api/knowledge-bases", response_model=KBItem, status_code=201)
async def create_knowledge_base(req: KBCreateIn, request: Request) -> Any:
    """Create a new knowledge base bound to an embedding model (required)."""
    user_id = get_user_id(request)
    await _validate_embed_model(user_id, req.embed_model)
    kb = await create_kb(
        user_id,
        req.name.strip()[:256],
        req.description or "",
        embed_model=req.embed_model,
        parser_config=req.parser_config.model_dump() if req.parser_config else None,
    )
    logger.info(
        "KB created | user=%s | kb=%s | embed_model=%s",
        user_id, kb.id, req.embed_model,
    )
    return _to_item(kb)


@router.put("/api/knowledge-bases/{kb_id}", response_model=KBItem)
async def update_knowledge_base(kb_id: str, req: KBUpdateIn, request: Request) -> Any:
    """Update a knowledge base's name/description and/or indexing config.

    A changed embed_model or parser_config invalidates the KB's vectors:
    assets are reset to unindexed, chunks purged, and reindex tasks queued
    (fire-and-forget).
    """
    user_id = get_user_id(request)
    name = req.name.strip()[:256] if req.name is not None else None
    if req.embed_model is not None or req.parser_config is not None:
        if req.embed_model is not None:
            await _validate_embed_model(user_id, req.embed_model)
        await _apply_indexing_change(
            kb_id,
            user_id,
            embed_model=req.embed_model,
            parser_config=(
                req.parser_config.model_dump() if req.parser_config else None
            ),
        )
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
