"""Asset library API routes — SPEC §3.3 assets CRUD + index."""

import os
import uuid
from pathlib import Path
from typing import Any

from auth import get_user_id
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from pydantic.alias_generators import to_camel
from repository.assets import (
    create_asset,
    delete_asset,
    get_asset,
    list_assets_by_user,
    set_asset_indexed,
)

logger = get_logger(__name__)
router = APIRouter(tags=["assets"])

ASSET_DIR = Path(os.environ.get("UPLOAD_DIR", "./uploads")) / "assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)

_MAX_IMAGE_MB = 10
_MAX_DOC_MB = 20
_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
_DOC_TYPES = {"application/pdf", "text/plain", "text/markdown"}


class AssetItem(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    id: str
    name: str
    asset_type: str
    size_bytes: int
    usage_count: int
    indexed: bool


def _validate(content_type: str, size: int) -> str:
    if content_type in _IMAGE_TYPES:
        limit = _MAX_IMAGE_MB * 1024 * 1024
        asset_type = "image"
    elif content_type in _DOC_TYPES:
        limit = _MAX_DOC_MB * 1024 * 1024
        asset_type = "document"
    else:
        raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail=f"不支持的文件类型: {content_type}")
    if size > limit:
        raise error_response(ErrorCode.ATTACHMENT_TOO_LARGE, detail="文件超过大小限制")
    return asset_type


def _to_item(asset: Any) -> AssetItem:
    return AssetItem(
        id=asset.id,
        name=asset.name,
        asset_type=asset.asset_type,
        size_bytes=asset.size_bytes,
        usage_count=asset.usage_count,
        indexed=asset.indexed,
    )


@router.get("/api/assets", response_model=list[AssetItem])
async def list_assets(request: Request) -> Any:
    user_id = get_user_id(request)
    assets = await list_assets_by_user(user_id)
    return [_to_item(a) for a in assets]


@router.post("/api/assets", response_model=AssetItem, status_code=201)
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    name: str | None = Form(None),
) -> Any:
    user_id = get_user_id(request)
    content_type = file.content_type or "application/octet-stream"
    content = await file.read()
    asset_type = _validate(content_type, len(content))

    safe_name = Path(file.filename or "asset").name
    filename = f"{user_id}-{uuid.uuid4().hex[:8]}-{safe_name}"
    storage_path = str(ASSET_DIR / filename)
    Path(storage_path).write_bytes(content)

    try:
        asset = await create_asset(
            user_id=user_id,
            name=(name or file.filename or filename)[:256],
            asset_type=asset_type,
            size_bytes=len(content),
            storage_path=storage_path,
        )
    except Exception:
        Path(storage_path).unlink(missing_ok=True)
        raise
    logger.info("Asset uploaded | user=%s | %s", user_id, storage_path)
    return _to_item(asset)


@router.put("/api/assets/{asset_id}", response_model=AssetItem)
async def rename_asset(asset_id: str, request: Request, name: str) -> Any:
    user_id = get_user_id(request)
    asset = await get_asset(asset_id)
    if asset is None or asset.user_id != user_id:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    asset.name = name.strip()[:256]
    from core.infra.database import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        session.add(asset)
        await session.commit()
    return _to_item(asset)


@router.delete("/api/assets/{asset_id}")
async def remove_asset(asset_id: str, request: Request) -> Any:
    user_id = get_user_id(request)
    asset = await get_asset(asset_id)
    if asset is None or asset.user_id != user_id:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    storage_path = await delete_asset(asset_id)
    if storage_path is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    Path(storage_path).unlink(missing_ok=True)
    return {"deleted": True}


@router.post("/api/assets/{asset_id}/index")
async def index_asset(asset_id: str, request: Request) -> Any:
    user_id = get_user_id(request)
    asset = await get_asset(asset_id)
    if asset is None or asset.user_id != user_id:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    if asset.asset_type != "document":
        raise error_response(ErrorCode.INVALID_REQUEST, detail="仅文档类素材可索引")
    try:
        from rag.rag_chunking import semantic_chunk
        from rag.rag_embedding import EmbeddingProvider
        from rag.rag_store import PgVectorStore
        from repository.keys import get_embedding_api_key

        text = Path(asset.storage_path).read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            raise error_response(ErrorCode.INVALID_REQUEST, detail="素材无文本内容，无法索引")
        api_key = await get_embedding_api_key()
        if not api_key:
            raise error_response(ErrorCode.INVALID_REQUEST, detail="未配置 embedding API Key")
        provider = EmbeddingProvider(api_key=api_key)

        chunks = semantic_chunk(text, session_id=f"asset:{asset.id}", run_id=None)
        embeddings = await provider.embed([c.text for c in chunks])
        for chunk, emb in zip(chunks, embeddings, strict=False):
            chunk.embedding = emb
        store = PgVectorStore()
        await store.add(chunks)
        await set_asset_indexed(asset.id, True)
        return {"indexed": True, "chunks": len(chunks)}
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        logger.exception("Asset index failed: %s", asset_id)
        raise error_response(ErrorCode.INTERNAL_ERROR, detail=f"索引失败: {e}") from e
