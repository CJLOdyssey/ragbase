"""RAG quality feedback — user answers are the online eval loop's intake.

A 'bad' rating exports the (run, question, answer) triple later, when someone
curates it into a golden case (scripts/eval_rag.py golden_qa.json).

alembic p9g3n009 defines feedback_logs (id, run_id, user_id, rating,
created_at).
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.infra.database import FeedbackLog, get_session_factory
from sqlalchemy import select

VALID_RATINGS = {"good", "bad"}


async def create_feedback(run_id: str, user_id: str, rating: str) -> dict[str, Any]:
    if rating not in VALID_RATINGS:
        raise ValueError(f"rating must be one of {sorted(VALID_RATINGS)}")
    factory = get_session_factory()
    async with factory() as session:
        row = FeedbackLog(
            id=str(uuid4()),
            run_id=run_id,
            user_id=user_id,
            rating=rating,
        )
        session.add(row)
        await session.commit()
        return {"id": row.id, "run_id": run_id, "user_id": user_id, "rating": rating}


async def list_feedback(user_id: str, limit: int = 200) -> list[dict[str, Any]]:
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
            "created_at": (r.created_at or datetime.now(UTC)).isoformat(),
        }
        for r in rows
    ]
