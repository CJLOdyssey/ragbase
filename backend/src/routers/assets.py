"""Asset library API routes — SPEC §3.3 assets CRUD + index."""

import os
import uuid
from pathlib import Path
from typing import Any

from auth import get_user_id
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from fastapi import APIRouter, File, Form, Request, UploadFile
from pydantic import BaseModel
from pydantic.alias_generators import to_camel
from repository.assets import (
    create_asset,
    delete_asset,
    get_asset,
    list_assets_by_user,
)

logger = get_logger(__name__)
router = APIRouter(tags=["assets"])

ASSET_DIR = Path(os.environ.get("UPLOAD_DIR", str(Path(__file__).resolve().parents[1] / "uploads"))) / "assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)

_MAX_IMAGE_MB = 10
_MAX_DOC_MB = 20
_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}
_DOC_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class AssetItem(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    id: str
    name: str
    asset_type: str
    size_bytes: int
    usage_count: int
    indexed: bool
    source: str = "upload"
    source_ref: str | None = None


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
        source=asset.source,
        source_ref=asset.source_ref,
    )


@router.get("/api/assets", response_model=list[AssetItem])
async def list_assets(request: Request) -> Any:
    """List the current user's assets."""
    user_id = get_user_id(request)
    assets = await list_assets_by_user(user_id)
    return [_to_item(a) for a in assets]


@router.post("/api/assets", response_model=AssetItem, status_code=201)
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    name: str | None = Form(None),
) -> Any:
    """Upload a file as an asset, validating type and size limits."""
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


class UrlImportIn(BaseModel):
    url: str
    name: str | None = None


@router.post("/api/assets/import-url", response_model=AssetItem, status_code=201)
async def import_asset_from_url(req: UrlImportIn, request: Request) -> Any:
    """Multi-source A: import a public document from a URL, then index as usual.

    SSRF guard: only http/https, never RFC1918/loopback/link-local targets.
    B/C (SharePoint/S3/DB/dir connectors) extend this via source field.
    """
    import ipaddress
    import urllib.parse

    from httpx import AsyncClient, Timeout

    user_id = get_user_id(request)
    parsed = urllib.parse.urlparse(req.url)
    if parsed.scheme not in ("http", "https"):
        raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail="仅支持 http/https 链接")
    try:
        host_ip = ipaddress.ip_address(parsed.hostname or "")
    except ValueError:
        try:
            host_ip = ipaddress.ip_address(await _resolve_host(parsed.hostname or ""))
        except Exception:
            raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail="无法解析链接域名") from None
    if host_ip.is_private or host_ip.is_loopback or host_ip.is_link_local or host_ip.is_reserved:
        raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail="不允许导入内网地址")

    timeout = Timeout(30.0)
    try:
        async with AsyncClient(follow_redirects=True, timeout=timeout) as client:
            resp = await client.get(req.url)
            resp.raise_for_status()
    except Exception:
        raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail="下载链接失败") from None

    content = resp.content
    content_type = resp.headers.get("content-type", "").split(";")[0].strip()
    asset_type = _validate(content_type, len(content))

    safe_name = Path(urllib.parse.urlparse(req.url).path or "asset").name or "asset"
    filename = f"{user_id}-{uuid.uuid4().hex[:8]}-{safe_name}"
    storage_path = str(ASSET_DIR / filename)
    Path(storage_path).write_bytes(content)

    try:
        asset = await create_asset(
            user_id=user_id,
            name=(req.name or safe_name)[:256],
            asset_type=asset_type,
            size_bytes=len(content),
            storage_path=storage_path,
            source="url",
            source_ref=req.url,
        )
    except Exception:
        Path(storage_path).unlink(missing_ok=True)
        raise
    logger.info("Asset imported from url | user=%s | %s", user_id, req.url)
    return _to_item(asset)


async def _resolve_host(hostname: str) -> str:
    import asyncio

    return await asyncio.to_thread(__import__("socket").gethostbyname, hostname)


@router.put("/api/assets/{asset_id}", response_model=AssetItem)
async def rename_asset(asset_id: str, request: Request, name: str) -> Any:
    """Rename an asset owned by the current user."""
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
    """Delete an asset and purge its vector chunks from the store."""
    user_id = get_user_id(request)
    asset = await get_asset(asset_id)
    if asset is None or asset.user_id != user_id:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    storage_path = await delete_asset(asset_id)
    if storage_path is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    Path(storage_path).unlink(missing_ok=True)
    # Cascade: purge this asset's vector chunks so deleted docs never resurface.
    from rag.rag_store import PgVectorStore

    await PgVectorStore().clear_asset(asset_id)
    return {"deleted": True}


@router.post("/api/assets/{asset_id}/index")
async def index_asset(asset_id: str, request: Request) -> Any:
    """Queue asynchronous indexing of a document asset in Celery."""
    user_id = get_user_id(request)
    asset = await get_asset(asset_id)
    if asset is None or asset.user_id != user_id:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    if asset.asset_type != "document":
        raise error_response(ErrorCode.INVALID_REQUEST, detail="仅文档类素材可索引")

    # Async, idempotent (reindex clears old chunks first); HTTP request returns
    # immediately — heavy work runs in the Celery worker.
    from tasks.registry import index_asset as index_asset_task

    index_asset_task.delay(asset_id, user_id)
    return {"indexing": True}
