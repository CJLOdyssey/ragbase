"""Shadow retrieval log (O4) — append-only variant-config comparison.

Separate from retrieval_logs so shadow replays of the same query never
pollute the online monitoring metrics (empty-recall rate, latency percentiles).
Immutability by construction: create-only, no update/delete.
"""

from typing import Any

from core.infra.database import get_session_factory
from orm import ShadowRetrievalLogDB


async def create_shadow_log(
    *,
    user_id: str,
    query: str,
    variant: str,
    latency_ms: int,
    hit_count: int,
    session_id: str | None = None,
    top_k: int = 5,
    rerank: bool = False,
    min_score: float | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> None:
    """Append a shadow retrieval log entry for variant comparison."""
    entry = ShadowRetrievalLogDB(
        user_id=user_id,
        session_id=session_id,
        query=query,
        top_k=top_k,
        rerank=rerank,
        min_score=min_score,
        latency_ms=latency_ms,
        hit_count=hit_count,
        sources=_sources_json(sources),
        variant=variant,
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
