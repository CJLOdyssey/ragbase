"""Bad-feedback review queue — human triage storage (read/write)."""

from datetime import UTC, datetime
from typing import Any

from core.infra.database import FeedbackLog, FeedbackReviewDB, get_session_factory
from sqlalchemy import func, select

ALLOWED_CAUSES = {"retrieval_miss", "wrong_answer", "bad_format", "other"}
ALLOWED_STATUSES = {"pending", "resolved", "dismissed"}


async def list_bad_feedback(
    user_id: str,
    window_hours: int = 0,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """List bad-rated feedback with optional review status filter.

    Returns rows of {feedback fields..., review: {...}|None}, newest first.
    """
    from datetime import timedelta

    factory = get_session_factory()
    async with factory() as session:
        conds = [
            FeedbackLog.user_id == user_id,
            FeedbackLog.rating == "bad",
        ]
        lower = (
            since
            if since is not None
            else (
                datetime.now(UTC) - timedelta(hours=window_hours)
                if window_hours > 0
                else None
            )
        )
        if lower is not None:
            conds.append(FeedbackLog.created_at >= lower)
        if until is not None:
            conds.append(FeedbackLog.created_at <= until)
        base = (
            select(FeedbackLog, FeedbackReviewDB)
            .outerjoin(FeedbackReviewDB, FeedbackReviewDB.feedback_id == FeedbackLog.id)
            .where(*conds)
        )
        if status is not None:
            base = base.where(FeedbackReviewDB.status == status)

        count_q = select(func.count()).select_from(
            base.order_by(None).subquery()
        )
        total = int((await session.execute(count_q)).scalar() or 0)

        rows = (
            (
                await session.execute(
                    base.order_by(FeedbackLog.created_at.desc())
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .all()
        )

    items = []
    for fb, review in rows:
        items.append(
            {
                "feedback_id": fb.id,
                "run_id": fb.run_id,
                "query": fb.query,
                "answer": fb.answer,
                "created_at": fb.created_at.isoformat() if fb.created_at else None,
                "review": (
                    {
                        "status": review.status,
                        "root_cause": review.root_cause,
                        "note": review.note,
                        "updated_at": (
                            review.updated_at.isoformat()
                            if review.updated_at
                            else None
                        ),
                    }
                    if review
                    else None
                ),
            }
        )
    return items, total


async def upsert_review(
    *,
    user_id: str,
    feedback_id: str,
    status: str,
    root_cause: str | None = None,
    note: str | None = None,
) -> dict[str, Any] | None:
    """Create or update the triage record for a bad rating.

    Returns the review payload, or None when the feedback does not belong
    to the user (ownership enforced against feedback_logs).
    """
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"invalid status: {status}")
    if root_cause is not None and root_cause not in ALLOWED_CAUSES:
        raise ValueError(f"invalid root_cause: {root_cause}")

    factory = get_session_factory()
    async with factory() as session:
        fb = await session.get(FeedbackLog, feedback_id)
        if fb is None or fb.user_id != user_id or fb.rating != "bad":
            return None

        review = (
            await session.execute(
                select(FeedbackReviewDB).where(
                    FeedbackReviewDB.feedback_id == feedback_id
                )
            )
        ).scalar_one_or_none()

        now = datetime.now(UTC)
        if review is None:
            review = FeedbackReviewDB(
                feedback_id=feedback_id,
                user_id=user_id,
                status=status,
                root_cause=root_cause,
                note=note,
                created_at=now,
                updated_at=now,
            )
            session.add(review)
        else:
            review.status = status
            review.root_cause = root_cause
            review.note = note
            review.updated_at = now
        await session.commit()
        return {
            "feedback_id": feedback_id,
            "status": review.status,
            "root_cause": review.root_cause,
            "note": review.note,
            "updated_at": review.updated_at.isoformat(),
        }
