"""Asset library API routes — SPEC §3.3 assets CRUD + index."""

import os
import urllib.parse
import uuid
from pathlib import Path
from typing import Any

from auth import get_user_id
from core.error_codes import ErrorCode, error_response
from core.infra.logging_config import get_logger
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from httpx import Timeout
from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel
from repository.assets import (
    create_asset,
    delete_asset,
    get_asset_for_user,
    increment_asset_usage,
    list_assets_by_user,
    update_asset_name,
)

logger = get_logger(__name__)
router = APIRouter(tags=["assets"])

ASSET_DIR = Path(os.environ.get("UPLOAD_DIR", str(Path(__file__).resolve().parents[1] / "uploads"))) / "assets"
ASSET_DIR.mkdir(parents=True, exist_ok=True)

_MAX_IMAGE_MB = 10
_MAX_DOC_MB = 20
_MAX_REDIRECTS = 3
_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif", "image/bmp"}
_DATA_TYPES = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
_DOC_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/html",
    "application/msword",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def _extract_format(filename: str) -> str:
    """Extract file extension (format) from filename, lowercase without dot."""
    from pathlib import Path
    suffix = Path(filename).suffix.lower()
    return suffix.lstrip(".") if suffix else "unknown"


class AssetItem(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    id: str
    name: str
    asset_type: str
    format: str | None = None
    size_bytes: int
    usage_count: int
    indexed: bool
    index_error: str | None = None
    knowledge_base_id: str | None = None
    source: str = "upload"
    source_ref: str | None = None
    tags: list[str] = []
    updated_at: Any | None = None
    chunk_count: int | None = None


class AssetTagsIn(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=20)


class AssetChunkOut(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    id: str | None = None
    enabled: bool = True
    text: str
    tags: list[str] = []
    metadata: dict[str, Any] = {}


class ChunkTextIn(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


class ChunkToggleIn(BaseModel):
    enabled: bool


class ChunkQAPairIn(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1, max_length=4000)


class ChunkBatchQAIn(BaseModel):
    pairs: list[ChunkQAPairIn] = Field(min_length=1, max_length=50)


async def _embed_for_asset(
    asset: Any, texts: list[str]
) -> tuple[list[list[float]], str | None]:
    """Embed texts with the asset's KB binding (model + chunk cohort).

    Raises RuntimeError when no embedding key is configured — curation ops
    must fail loudly rather than write vectors from an unknown space.
    """
    from rag.rag_embedding import EmbeddingProvider
    from rag.rag_guard import require_kb_binding
    from repository.keys import get_embedding_config
    from repository.knowledge_bases import get_kb

    require_kb_binding(asset)
    kb = await get_kb(asset.knowledge_base_id, asset.user_id)
    kb_embed_model: str | None = getattr(kb, "embed_model", None) if kb else None
    cfg = await get_embedding_config(preferred_model=kb_embed_model)
    if cfg is None or cfg["api_key"] is None:
        raise RuntimeError("no embedding API key configured")
    provider = EmbeddingProvider(
        api_key=cfg["api_key"],
        model=cfg["model"] or "text-embedding-v3",
        base_url=cfg["base_url"],
    )
    embeddings = await provider.embed(texts)
    return embeddings, provider.model


def _validate(content_type: str, size: int) -> str:
    if content_type in _IMAGE_TYPES:
        limit = _MAX_IMAGE_MB * 1024 * 1024
        asset_type = "image"
    elif content_type in _DATA_TYPES:
        limit = _MAX_DOC_MB * 1024 * 1024
        asset_type = "data"
    elif content_type in _DOC_TYPES:
        limit = _MAX_DOC_MB * 1024 * 1024
        asset_type = "document"
    else:
        raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail=f"不支持的文件类型: {content_type}")
    if size > limit:
        raise error_response(ErrorCode.ATTACHMENT_TOO_LARGE, detail="文件超过大小限制")
    return asset_type


def _to_item(asset: Any, chunk_count: int | None = None) -> AssetItem:
    kb_id = getattr(asset, "knowledge_base_id", None)
    updated = getattr(asset, "updated_at", None)
    raw_index_error = getattr(asset, "index_error", None)
    return AssetItem(
        id=asset.id,
        name=asset.name,
        asset_type=asset.asset_type,
        format=getattr(asset, "format", None),
        size_bytes=asset.size_bytes,
        usage_count=asset.usage_count,
        indexed=asset.indexed,
        index_error=raw_index_error if isinstance(raw_index_error, str) else None,
        knowledge_base_id=kb_id if isinstance(kb_id, str) else None,
        source=asset.source,
        source_ref=asset.source_ref,
        tags=list(getattr(asset, "tags", None) or []),
        updated_at=updated,
        chunk_count=chunk_count,
    )


async def _chunk_counts_for(asset_ids: list[str]) -> dict[str, int]:
    if not asset_ids:
        return {}
    try:
        from core.infra.database import get_session_factory
        from sqlalchemy import text

        factory = get_session_factory()
        async with factory() as session:
            rows = await session.execute(
                text("SELECT asset_id, COUNT(*) FROM vector_chunks WHERE asset_id = ANY(:aids) GROUP BY asset_id"),
                {"aids": asset_ids},
            )
            return {r[0]: int(r[1]) for r in rows.fetchall()}
    except Exception:
        return {}


@router.get("/api/assets", response_model=list[AssetItem])
async def list_assets(
    request: Request,
    sort_by: str | None = None,
    order: str | None = None,
) -> Any:
    """List the current user's assets.

    默认按点击排序（点击次数 + 最近一次点击 均 desc，见 repository）。
    支持 ?sort_by=usage_count|updated_at|name|size&order=asc|desc
    """
    user_id = get_user_id(request)
    assets = await list_assets_by_user(user_id, sort_by=sort_by, order=order)
    ids = [a.id for a in assets]
    counts = await _chunk_counts_for(ids)
    return [_to_item(a, counts.get(a.id, 0 if a.indexed else 0)) for a in assets]


@router.post("/api/assets", response_model=AssetItem, status_code=201)
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),  # noqa: B008
    name: str | None = Form(None),
) -> Any:
    """Upload a file as an asset, validating type and size limits."""
    user_id = get_user_id(request)
    content_type = file.content_type or "application/octet-stream"
    # 浏览器/ curl 对 csv/doc 等可能误报 octet-stream，退化按扩展名推断
    if content_type == "application/octet-stream" and file.filename:
        import mimetypes

        guessed, _ = mimetypes.guess_type(file.filename)
        if guessed:
            content_type = guessed
        else:
            ext = Path(file.filename).suffix.lower()
            ext_fallback = {
                ".csv": "text/csv",
                ".html": "text/html",
                ".htm": "text/html",
                ".doc": "application/msword",
                ".xls": "application/vnd.ms-excel",
                ".ppt": "application/vnd.ms-powerpoint",
                ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ".md": "text/markdown",
                ".txt": "text/plain",
            }
            content_type = ext_fallback.get(ext, content_type)
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
            format=_extract_format(safe_name),
            size_bytes=len(content),
            storage_path=storage_path,
        )
    except Exception:
        Path(storage_path).unlink(missing_ok=True)
        raise
    logger.info("Asset uploaded | user=%s | %s", user_id, storage_path)
    return _to_item(asset, 0)


class UrlImportIn(BaseModel):
    url: str
    name: str | None = None


def _candidate_import_urls(url: str) -> list[str]:
    """Google Workspace 友好：自动将分享链接转为可直接下载的 export 链接."""
    import re

    candidates: list[str] = []
    # Docs
    m = re.search(r"docs\.google\.com/document/d/([a-zA-Z0-9-_]+)", url)
    if m:
        candidates.append(f"https://docs.google.com/document/d/{m.group(1)}/export?format=docx")
        candidates.append(f"https://docs.google.com/document/d/{m.group(1)}/export?format=pdf")
    # Sheets
    m = re.search(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if m:
        candidates.append(f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=xlsx")
        candidates.append(f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=pdf")
    # Slides
    m = re.search(r"docs\.google\.com/presentation/d/([a-zA-Z0-9-_]+)", url)
    if m:
        candidates.append(f"https://docs.google.com/presentation/d/{m.group(1)}/export?format=pptx")
        candidates.append(f"https://docs.google.com/presentation/d/{m.group(1)}/export?format=pdf")
    # Drive file
    m = re.search(r"drive\.google\.com/file/d/([a-zA-Z0-9-_]+)", url)
    if m:
        candidates.append(f"https://drive.google.com/uc?export=download&id={m.group(1)}")
    # 原链接兜底
    candidates.append(url)
    # 去重保序
    seen: set[str] = set()
    uniq: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


@router.post("/api/assets/import-url", response_model=AssetItem, status_code=201)
async def import_asset_from_url(req: UrlImportIn, request: Request) -> Any:
    """Multi-source A: import a public document from a URL, then index as usual.

    SSRF guard: only http/https, never RFC1918/loopback/link-local targets.
    B/C (SharePoint/S3/DB/dir connectors) extend this via source field.
    """
    user_id = get_user_id(request)

    # Google 文档私有会导致长时间重定向到登录页，需快速失败并给出可操作提示
    is_google = "docs.google.com" in req.url or "drive.google.com" in req.url
    timeout = Timeout(15.0 if is_google else 30.0)
    last_exc: Exception | None = None
    content: bytes | None = None
    content_type = ""
    last_url = req.url
    for cand in _candidate_import_urls(req.url):
        try:
            logger.info("URL import try cand=%s", cand)
            c, ct = await _fetch_public(cand, timeout)
            logger.info("URL import cand ok ct=%s len=%d", ct, len(c))
            # 检测 Google 私有文档的登录页（text/html 且含登录特征）
            if is_google and ct.startswith("text/html"):
                try:
                    html = c[:4096].decode("utf-8", errors="ignore").lower()
                except Exception:
                    html = ""
                if "accounts.google.com" in html or "servicelogin" in html or "signin" in html or "登录" in html:
                    logger.warning("URL import cand private html %s", cand)
                    last_exc = RuntimeError("google_private")
                    continue
            content, content_type = c, ct
            last_url = cand
            break
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("URL import cand failed %s err=%s type=%s", cand, e, type(e).__name__)
            last_exc = e
            continue
    if content is None:
        if isinstance(last_exc, RuntimeError) and str(last_exc) == "google_private":
            raise error_response(
                ErrorCode.ATTACHMENT_TYPE_INVALID,
                detail="该 Google 文档未公开：请先设为“任何拥有链接的人可查看”，或下载为 .docx 后上传",
            ) from last_exc
        raise error_response(
            ErrorCode.ATTACHMENT_TYPE_INVALID,
            detail="下载链接失败，请检查链接是否可公开访问",
        ) from last_exc

    # 兜底：仍为登录页
    if is_google and content_type.startswith("text/html"):
        try:
            html = content[:4096].decode("utf-8", errors="ignore").lower()
            if "accounts.google.com" in html or "servicelogin" in html:
                raise error_response(
                    ErrorCode.ATTACHMENT_TYPE_INVALID,
                    detail="该 Google 文档未公开：请先设为“任何拥有链接的人可查看”，或下载为 .docx 后上传",
                )
        except HTTPException:
            raise
        except Exception:
            pass

    try:
        asset_type = _validate(content_type, len(content))
    except HTTPException as e:
        logger.warning(
            "URL import validate failed ct=%s len=%d err=%s", content_type, len(content) if content else 0, e
        )
        raise

    safe_name = Path(urllib.parse.urlparse(last_url).path or "asset").name or "asset"
    # export 链接的 path 为 /export，无文件名，需回退到原始 URL 的文件名或按类型补后缀
    if safe_name == "export" or not Path(safe_name).suffix:
        orig_name = Path(urllib.parse.urlparse(req.url).path or "").name or "document"
        # 若原始链接也无后缀，按 content_type 补一个
        if not Path(safe_name).suffix and Path(orig_name).suffix:
            safe_name = orig_name
        elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            safe_name = (Path(orig_name).stem or "document") + ".docx"
        elif content_type == "application/pdf":
            safe_name = (Path(orig_name).stem or "document") + ".pdf"
        elif content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            safe_name = (Path(orig_name).stem or "spreadsheet") + ".xlsx"
        elif content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
            safe_name = (Path(orig_name).stem or "presentation") + ".pptx"
    filename = f"{user_id}-{uuid.uuid4().hex[:8]}-{safe_name}"
    storage_path = str(ASSET_DIR / filename)
    Path(storage_path).write_bytes(content)

    try:
        asset = await create_asset(
            user_id=user_id,
            name=(req.name or safe_name)[:256],
            asset_type=asset_type,
            format=_extract_format(safe_name),
            size_bytes=len(content),
            storage_path=storage_path,
            source="url",
            source_ref=req.url,
        )
    except Exception:
        Path(storage_path).unlink(missing_ok=True)
        raise
    logger.info("Asset imported from url | user=%s | %s", user_id, req.url)
    return _to_item(asset, 0)


async def _resolve_host(hostname: str) -> str:
    import asyncio

    return await asyncio.to_thread(__import__("socket").gethostbyname, hostname)


async def _validate_public_host(hostname: str) -> None:
    """Reject private/loopback/link-local/reserved hosts — every redirect hop."""
    import ipaddress

    try:
        host_ip = ipaddress.ip_address(hostname)
    except ValueError:
        try:
            host_ip = ipaddress.ip_address(await _resolve_host(hostname))
        except Exception:
            raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail="无法解析链接域名") from None
    # 私网/回环/链路本地/保留/未指定(0.0.0.0)/组播地址一律拒绝 —— 任何一跳都不放过
    if (
        host_ip.is_private
        or host_ip.is_loopback
        or host_ip.is_link_local
        or host_ip.is_reserved
        or host_ip.is_unspecified
        or host_ip.is_multicast
    ):
        raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail="不允许导入内网地址")


async def _fetch_public(url: str, timeout: Any) -> tuple[bytes, str]:
    """通用拉取：逐跳 SSRF 校验 + 手动跟随重定向（每跳都拒绝内网，防 open redirect）。"""
    import urllib.parse

    from httpx import AsyncClient

    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        parsed = urllib.parse.urlparse(current)
        if parsed.scheme not in ("http", "https"):
            raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail="仅支持 http/https 链接")
        # 每一跳都做 SSRF 复核，私网/回环/保留地址在任意跳均被拒绝
        await _validate_public_host(parsed.hostname or "")
        async with AsyncClient(follow_redirects=False, timeout=timeout) as client:
            resp = await client.get(
                current,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; RagBase/1.0)",
                    "Accept": "*/*",
                },
            )
        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("location")
            if not location:
                raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail="重定向缺少目标地址")
            current = urllib.parse.urljoin(current, location)
            continue
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "").split(";")[0].strip()
        # 兜底：部分导出链接不带 content-type，按扩展名补型（如 googleusercontent 导出）
        if not content_type:
            ext = Path(urllib.parse.urlparse(str(resp.url)).path).suffix.lower()
            if ext == ".docx":
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif ext == ".pdf":
                content_type = "application/pdf"
        return resp.content, content_type
    raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail="重定向次数过多")


@router.put("/api/assets/{asset_id}", response_model=AssetItem)
async def rename_asset(asset_id: str, request: Request, name: str) -> Any:
    """Rename an asset owned by the current user（扩展名不可变，后端权威兜底）."""
    user_id = get_user_id(request)
    existing = await get_asset_for_user(asset_id, user_id)
    if existing is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    raw = name.strip()[:256]
    if not raw:
        raise error_response(ErrorCode.INVALID_REQUEST, detail="文件名不能为空")
    # 扩展名守恒：仅允许修改 basename
    orig_name: str = existing.name
    idx = orig_name.rfind('.')
    orig_ext = orig_name[idx:] if idx > 0 else ''
    if orig_ext:
        # 去除用户可能误带的扩展或路径
        base = raw.split('.')[0].split('/')[0].split('\\')[0].strip()
        if not base:
            raise error_response(ErrorCode.INVALID_REQUEST, detail="文件名不能为空")
        # 保留原始扩展（大小写按原始）
        if not raw.lower().endswith(orig_ext.lower()):
            raw = base + orig_ext
        # 长度再截断
        raw = raw[:256]
    asset = await update_asset_name(asset_id, user_id, raw)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    counts = await _chunk_counts_for([asset.id])
    return _to_item(asset, counts.get(asset.id, 0))


def _sanitize_tags(raw: list[str]) -> list[str]:
    """Normalize user tags: trim/lower/dedupe/cap length — max 20."""
    out: list[str] = []
    for t in raw:
        clean = t.strip().lower()[:32]
        if clean and clean not in out:
            out.append(clean)
    return out[:20]


@router.put("/api/assets/{asset_id}/tags", response_model=AssetItem)
async def set_asset_tags(asset_id: str, req: AssetTagsIn, request: Request) -> Any:
    """Replace an asset's curated tags (owner-scoped).

    Tags are injected into the asset's chunks at (re)index time and usable
    as a retrieval filter.
    """
    from repository.assets import update_asset_tags

    user_id = get_user_id(request)
    existing = await get_asset_for_user(asset_id, user_id)
    if existing is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    asset = await update_asset_tags(asset_id, user_id, _sanitize_tags(req.tags))
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    counts = await _chunk_counts_for([asset.id])
    logger.info("Asset tags set | user=%s | asset=%s | n=%d", user_id, asset_id, len(asset.tags))
    return _to_item(asset, counts.get(asset.id, 0))


@router.delete("/api/assets/{asset_id}")
async def remove_asset(asset_id: str, request: Request) -> Any:
    """Delete an asset and purge its vector chunks from the store."""
    user_id = get_user_id(request)
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
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
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    if asset.asset_type != "document":
        raise error_response(ErrorCode.INVALID_REQUEST, detail="仅文档类素材可索引")
    if not asset.knowledge_base_id:
        raise error_response(ErrorCode.INVALID_REQUEST, detail="请先将素材分配到知识库")

    # Async, idempotent (reindex clears old chunks first); HTTP request returns
    # immediately — heavy work runs in the Celery worker.
    from tasks.registry import index_asset as index_asset_task

    index_asset_task.delay(asset_id, user_id)
    return {"indexing": True}


@router.get("/api/assets/{asset_id}/progress")
async def get_asset_progress(asset_id: str, request: Request) -> Any:
    """Get indexing progress for an asset."""
    user_id = get_user_id(request)
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")

    from repository.index_progress import get_index_progress

    progress = await get_index_progress(asset_id)
    if progress is None:
        return {"stage": None}
    return progress


@router.get("/api/assets/{asset_id}/chunks", response_model=list[AssetChunkOut])
async def get_asset_chunks(asset_id: str, request: Request) -> Any:
    """List an asset's vector chunks for preview (owner-scoped)."""
    user_id = get_user_id(request)
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")

    from rag.rag_store import PgVectorStore

    return await PgVectorStore().list_asset_chunks(asset_id, user_id)


@router.post("/api/assets/{asset_id}/chunks", response_model=AssetChunkOut, status_code=201)
async def add_asset_chunk(asset_id: str, req: ChunkTextIn, request: Request) -> Any:
    """Manually append a curated chunk (embedded with the KB's binding)."""
    user_id = get_user_id(request)
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")

    from rag.rag_store import PgVectorStore

    try:
        embeddings, model = await _embed_for_asset(asset, [req.text.strip()])
    except (RuntimeError, ValueError) as e:
        raise error_response(ErrorCode.INVALID_REQUEST, detail=str(e)) from e
    store: PgVectorStore = PgVectorStore()
    chunk_id = await store.add_manual_chunk(
        asset_id,
        user_id,
        req.text.strip(),
        embeddings[0],
        model,
        asset_name=asset.name,
    )
    logger.info(
        "Manual chunk added | user=%s | asset=%s | chunk=%s", user_id, asset_id, chunk_id
    )
    return AssetChunkOut(
        id=chunk_id, enabled=True, text=req.text.strip(), metadata={"manual": True}
    )


@router.patch(
    "/api/assets/{asset_id}/chunks/{chunk_id}", response_model=AssetChunkOut
)
async def edit_asset_chunk(
    asset_id: str, chunk_id: str, req: ChunkTextIn, request: Request
) -> Any:
    """Rewrite a chunk's text and re-embed it in place."""
    user_id = get_user_id(request)
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")

    from rag.rag_store import PgVectorStore

    try:
        embeddings, model = await _embed_for_asset(asset, [req.text.strip()])
    except (RuntimeError, ValueError) as e:
        raise error_response(ErrorCode.INVALID_REQUEST, detail=str(e)) from e
    new_id = await PgVectorStore().update_chunk_text(
        chunk_id, asset_id, user_id, req.text.strip(), embeddings[0], model
    )
    if new_id is None:
        raise error_response(ErrorCode.CHUNK_NOT_FOUND, detail="chunk 不存在")
    logger.info(
        "Chunk edited | user=%s | asset=%s | chunk=%s -> %s",
        user_id, asset_id, chunk_id, new_id,
    )
    return AssetChunkOut(id=new_id, text=req.text.strip(), metadata={})


@router.delete("/api/assets/{asset_id}/chunks/{chunk_id}")
async def delete_asset_chunk(
    asset_id: str, chunk_id: str, request: Request
) -> Any:
    """Hard-delete a single curated chunk."""
    user_id = get_user_id(request)
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")

    from rag.rag_store import PgVectorStore

    ok = await PgVectorStore().delete_chunk(chunk_id, asset_id, user_id)
    if not ok:
        raise error_response(ErrorCode.CHUNK_NOT_FOUND, detail="chunk 不存在")
    return {"deleted": True}


@router.post("/api/assets/{asset_id}/chunks/{chunk_id}/toggle")
async def toggle_asset_chunk(
    asset_id: str, chunk_id: str, req: ChunkToggleIn, request: Request
) -> Any:
    """Soft-disable/enable a single chunk (excluded from retrieval)."""
    user_id = get_user_id(request)
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")

    from rag.rag_store import PgVectorStore

    ok = await PgVectorStore().set_chunk_enabled(
        chunk_id, asset_id, user_id, req.enabled
    )
    if not ok:
        raise error_response(ErrorCode.CHUNK_NOT_FOUND, detail="chunk 不存在")
    return {"enabled": req.enabled}


@router.get("/api/assets/{asset_id}/content")
async def get_asset_content(asset_id: str, request: Request) -> Any:
    """Return raw file content for preview (owner-scoped, truncated)."""
    user_id = get_user_id(request)
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    storage_path = getattr(asset, "storage_path", None)
    if not storage_path or not Path(storage_path).exists():
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="文件不存在")
    # 图片走 /file 直显，不在此提取文本；避免二进制按 utf-8 误读为乱码
    if asset.asset_type == "image":
        return {"content": "", "truncated": False, "assetType": asset.asset_type}
    try:
        from rag.rag_parsing import extract_text

        text = extract_text(storage_path)
        truncated = False
        if len(text) > 20000:
            text = text[:20000]
            truncated = True
        return {"content": text, "truncated": truncated, "assetType": asset.asset_type}
    except Exception as e:
        logger.warning("extract failed for %s: %s", asset_id, e)
        raise error_response(ErrorCode.INTERNAL_ERROR, detail="文件解析失败") from e


@router.get("/api/assets/{asset_id}/file")
async def get_asset_file(asset_id: str, request: Request) -> Any:
    """Serve raw asset file for preview / download (owner-scoped)."""
    user_id = get_user_id(request)
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    storage_path = getattr(asset, "storage_path", None)
    if not storage_path or not Path(storage_path).exists():
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="文件不存在")
    import mimetypes

    media_type, _ = mimetypes.guess_type(asset.name)
    media_type = media_type or "application/octet-stream"
    return FileResponse(storage_path, filename=asset.name, media_type=media_type)


@router.post("/api/assets/{asset_id}/touch", response_model=AssetItem)
async def touch_asset(asset_id: str, request: Request) -> Any:
    """显式点击埋点：增加次数并刷新最近点击，返回更新后资产（供前端乐观对账）."""
    user_id = get_user_id(request)
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    await increment_asset_usage(asset_id)
    # 重新读取以拿到最新的 updated_at/usage_count
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    counts = await _chunk_counts_for([asset.id])
    return _to_item(asset, counts.get(asset.id, 0 if asset.indexed else 0))


@router.post("/api/assets/{asset_id}/retry-index")
async def retry_index_asset(asset_id: str, request: Request) -> Any:
    """Retry indexing a failed asset by resetting indexed flag and re-queuing."""
    user_id = get_user_id(request)
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")
    if asset.asset_type != "document":
        raise error_response(ErrorCode.INVALID_REQUEST, detail="仅文档类素材可索引")
    if not asset.knowledge_base_id:
        raise error_response(ErrorCode.INVALID_REQUEST, detail="请先将素材分配到知识库")

    from repository.assets import set_asset_index_result
    from tasks.registry import index_asset as index_asset_task

    # Clear the stale failure reason up front: while the retry runs, the
    # asset shows processing/pending — not the previous error.
    await set_asset_index_result(asset_id, False, None)
    index_asset_task.delay(asset_id, user_id)

    logger.info("Asset re-index retry queued | user=%s | asset=%s", user_id, asset_id)
    return {"retrying": True}


@router.post("/api/assets/{asset_id}/chunks/batch-qa", status_code=201)
async def add_qa_chunks(asset_id: str, req: ChunkBatchQAIn, request: Request) -> Any:
    """Bulk-import curated Q&A pairs as chunks (one chunk per pair).

    The question rides in metadata for structured display; text embeds as
    "question\\nanswer" so queries match either side. Works on unindexed
    assets — QA ingestion does not depend on document parsing.
    """
    user_id = get_user_id(request)
    asset = await get_asset_for_user(asset_id, user_id)
    if asset is None:
        raise error_response(ErrorCode.ASSET_NOT_FOUND, detail="素材不存在")

    from rag.rag_store import PgVectorStore

    texts = [f"{p.question.strip()}\n{p.answer.strip()}" for p in req.pairs]
    try:
        embeddings, model = await _embed_for_asset(asset, texts)
    except (RuntimeError, ValueError) as e:
        raise error_response(ErrorCode.INVALID_REQUEST, detail=str(e)) from e

    store: PgVectorStore = PgVectorStore()
    ids = []
    for pair, emb in zip(req.pairs, embeddings, strict=True):
        cid = await store.add_manual_chunk(
            asset_id,
            user_id,
            f"{pair.question.strip()}\n{pair.answer.strip()}",
            emb,
            model,
            asset_name=asset.name,
            extra_metadata={"qa": True, "question": pair.question.strip()},
        )
        ids.append(cid)
    logger.info(
        "QA chunks imported | user=%s | asset=%s | n=%d", user_id, asset_id, len(ids)
    )
    return {"created": len(ids)}
