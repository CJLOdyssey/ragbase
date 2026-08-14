"""Append-only retrieval activity log — write path only (OWASP LLM08).

Immutability by construction: no update/delete exists; rows are only ever
inserted at the retrieval boundary, once per user question.
"""

from typing import Any

from core.infra.database import get_session_factory
from orm import RetrievalLogDB


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
