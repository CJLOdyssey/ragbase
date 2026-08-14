"""RAG quality feedback — user answers are the online eval loop's intake.

A 'bad' rating exports the (run, question, answer, sources) snapshot later,
when someone curates it into a golden case (backend/tests/eval/golden_qa.json).
The snapshot is captured at rating time so the eval record stays auditable
even if the message/run is later edited or deleted (NVIDIA: "log the response
alongside its references").

alembic p9g3n009/p9g3n011 define feedback_logs (id, run_id, user_id, rating,
query, answer, sources, created_at).
"""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.infra.database import FeedbackLog, ProjectRun, get_session_factory
from sqlalchemy import select

from repository.message_repo import get_messages

VALID_RATINGS = {"good", "bad"}


def _parse_sources(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


async def _snapshot_for_run(run_id: str) -> tuple[str | None, str | None, list[dict[str, Any]]]:
    """Grab (requirement, latest agent answer, sources) for a run's feedback."""
    factory = get_session_factory()
    async with factory() as session:
        run = await session.get(ProjectRun, run_id)
        query = run.requirement if run else None
    messages = await get_messages(run_id)
    answer = None
    sources: list[dict[str, Any]] = []
    for m in reversed(messages):
        if m.role != "user" and m.content:
            answer = m.content
            sources = _parse_sources(m.sources)
            break
    return query, answer, sources


async def create_feedback(run_id: str, user_id: str, rating: str) -> dict[str, Any]:
    """Record a rating for a run, snapshotting its query, answer, and sources."""
    if rating not in VALID_RATINGS:
        raise ValueError(f"rating must be one of {sorted(VALID_RATINGS)}")
    query, answer, sources = await _snapshot_for_run(run_id)
    factory = get_session_factory()
    async with factory() as session:
        row = FeedbackLog(
            id=str(uuid4()),
            run_id=run_id,
            user_id=user_id,
            rating=rating,
            query=query,
            answer=answer,
            sources=json.dumps(sources, ensure_ascii=False) if sources else None,
        )
        session.add(row)
        await session.commit()
        return {
            "id": row.id,
            "run_id": run_id,
            "user_id": user_id,
            "rating": rating,
            "query": query,
            "answer": answer,
            "sources": sources,
        }


async def list_feedback(user_id: str, limit: int = 200) -> list[dict[str, Any]]:
    """Return a user's feedback entries, newest first."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(FeedbackLog)
            .where(FeedbackLog.user_id == user_id)
            .order_by(FeedbackLog.created_at.desc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "id": r.id,
            "run_id": r.run_id,
            "rating": r.rating,
            "query": r.query,
            "answer": r.answer,
            "sources": _parse_sources(r.sources),
            "created_at": (r.created_at or datetime.now(UTC)).isoformat(),
        }
        for r in rows
    ]
