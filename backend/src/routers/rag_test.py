"""RAG retrieval test workbench — validate retrieval quality before/after ingest."""

from typing import Any, Literal

from auth import get_user_id
from core.infra.logging_config import get_logger
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from pydantic.alias_generators import to_camel
from rag.rag_pipeline import get_rag_pipeline, retrieve_sources
from repository.assets import list_asset_ids_by_kb

from routers.query_strategies import rewrite_query

logger = get_logger(__name__)
router = APIRouter(tags=["rag"])


class RetrievalTestIn(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    rerank: bool = False
    rewrite: bool = False
    knowledge_base_id: str | None = None
    retrieval_method: Literal["hybrid", "semantic", "lexical"] = "hybrid"
    tags: list[str] | None = None


class RetrievalSourceOut(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    asset_id: str | None
    asset_name: str | None
    text: str
    similarity: float


class RetrievalTestOut(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    original_query: str
    query: str
    hit_count: int
    embedding_configured: bool
    sources: list[RetrievalSourceOut]


@router.post("/api/rag/test-retrieval", response_model=RetrievalTestOut)
async def test_retrieval(req: RetrievalTestIn, request: Request) -> Any:
    """Dry-run retrieval for a single query, returning hit chunks + scores.

    Reuses the production retrieve_sources pipeline so the workbench measures
    real search quality. Supports optional query rewrite and knowledge-base
    scoping.
    """
    user_id = get_user_id(request)
    original = req.query.strip()
    if not original:
        raise HTTPException(status_code=400, detail="query is required")

    embedding_provider, _ = get_rag_pipeline()

    effective = original
    if req.rewrite:
        effective = rewrite_query(original, []) or original

    asset_ids = None
    if req.knowledge_base_id:
        asset_ids = await list_asset_ids_by_kb(req.knowledge_base_id, user_id)

    sources = await retrieve_sources(
        query=effective,
        user_id=user_id,
        asset_ids=asset_ids,
        top_k=req.top_k,
        rerank=req.rerank,
        tags=[t.strip().lower() for t in req.tags or [] if t.strip()],
        retrieval_method=req.retrieval_method,
    )

    logger.info(
        "RAG test-retrieval | user=%s | kb=%s | query=%s | hits=%d",
        user_id, req.knowledge_base_id, effective, len(sources),
    )

    return RetrievalTestOut(
        original_query=original,
        query=effective,
        hit_count=len(sources),
        embedding_configured=embedding_provider is not None,
        sources=[RetrievalSourceOut(**s) for s in sources],
    )
