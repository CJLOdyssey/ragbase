"""Retrieval logs browse API — paginated retrieval activity logs."""

import json
from typing import Any

from auth import get_user_id
from core.infra.logging_config import get_logger
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from pydantic.alias_generators import to_camel
from repository.retrieval_logs import list_retrieval_logs

logger = get_logger(__name__)
router = APIRouter(tags=["retrieval_logs"])


class RetrievalLogItem(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    id: str
    query: str
    session_id: str | None
    run_id: str | None
    latency_ms: int
    hit_count: int
    top_k: int
    rerank: bool
    min_score: float | None
    sources: list[dict[str, Any]] | None
    created_at: str


class RetrievalLogsResponse(BaseModel):
    model_config = {"alias_generator": to_camel, "populate_by_name": True}
    items: list[RetrievalLogItem]
    total: int
    page: int
    page_size: int


def _parse_sources(sources_json: str | None) -> list[dict[str, Any]] | None:
    """Parse sources JSON string into list of dicts."""
    if not sources_json:
        return None
    try:
        result = json.loads(sources_json)
        return result if isinstance(result, list) else None
    except (json.JSONDecodeError, TypeError):
        return None


@router.get("/api/retrieval-logs", response_model=RetrievalLogsResponse)
async def get_retrieval_logs(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_hit_count: int | None = Query(None, ge=0),
    max_latency_ms: int | None = Query(None, ge=0),
    empty_only: bool = Query(False),
    since_hours: int | None = Query(None, ge=0, le=24 * 30),
) -> Any:
    """List retrieval logs for the current user with pagination and filters."""
    user_id = get_user_id(request)

    items, total = await list_retrieval_logs(
        user_id=user_id,
        page=page,
        page_size=page_size,
        min_hit_count=min_hit_count,
        max_latency_ms=max_latency_ms,
        empty_only=empty_only,
        since_hours=since_hours,
    )

    log_items = [
        RetrievalLogItem(
            id=log.id,
            query=log.query,
            session_id=log.session_id,
            run_id=log.run_id,
            latency_ms=log.latency_ms,
            hit_count=log.hit_count,
            top_k=log.top_k,
            rerank=log.rerank,
            min_score=log.min_score,
            sources=_parse_sources(log.sources),
            created_at=log.created_at.isoformat(),
        )
        for log in items
    ]

    logger.info(
        "Retrieval logs fetched | user=%s | page=%d | total=%d",
        user_id, page, total,
    )

    return RetrievalLogsResponse(
        items=log_items,
        total=total,
        page=page,
        page_size=page_size,
    )
