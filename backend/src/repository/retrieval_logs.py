"""Append-only retrieval activity log — write path only (OWASP LLM08).

Immutability by construction: no update/delete exists; rows are only ever
inserted at the retrieval boundary, once per user question.
"""

from typing import Any

from core.infra.database import get_session_factory
from orm import RetrievalLogDB
from sqlalchemy import func, select


async def create_retrieval_log(
    *,
    user_id: str,
    query: str,
    latency_ms: int,
    hit_count: int,
    session_id: str | None = None,
    top_k: int = 5,
    rerank: bool = False,
    min_score: float | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> None:
    """Append a retrieval activity log entry (write-only by design)."""
    entry = RetrievalLogDB(
        user_id=user_id,
        session_id=session_id,
        query=query,
        top_k=top_k,
        rerank=rerank,
        min_score=min_score,
        latency_ms=latency_ms,
        hit_count=hit_count,
        sources=_sources_json(sources),
    )
    factory = get_session_factory()
    async with factory() as session:
        session.add(entry)
        await session.commit()


def _sources_json(sources: list[dict[str, Any]] | None) -> str | None:
    import json

    if not sources:
        return None
    return json.dumps(
        [
            {
                "asset_id": s.get("asset_id"),
                "asset_name": s.get("asset_name"),
                "similarity": s.get("similarity"),
            }
            for s in sources
        ],
        ensure_ascii=False,
    )


async def list_retrieval_logs(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    min_hit_count: int | None = None,
    max_latency_ms: int | None = None,
    empty_only: bool = False,
) -> tuple[list[RetrievalLogDB], int]:
    """List retrieval logs for a user with pagination and filters."""
    factory = get_session_factory()
    async with factory() as session:
        query = select(RetrievalLogDB).where(RetrievalLogDB.user_id == user_id)

        if min_hit_count is not None:
            query = query.where(RetrievalLogDB.hit_count >= min_hit_count)
        if max_latency_ms is not None:
            query = query.where(RetrievalLogDB.latency_ms <= max_latency_ms)
        if empty_only:
            query = query.where(RetrievalLogDB.hit_count == 0)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(RetrievalLogDB.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        items = list(result.scalars().all())

        return items, total
