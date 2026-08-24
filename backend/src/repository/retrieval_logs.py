"""Append-only retrieval activity log — write path only (OWASP LLM08).

Immutability by construction: no update/delete exists; rows are only ever
inserted at the retrieval boundary, once per user question.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from core.infra.database import get_session_factory
from orm import RetrievalLogDB
from sqlalchemy import case, func, select


@dataclass
class RetrievalStats:
    """Aggregated retrieval statistics for chart visualization."""

    latency_distribution: list[dict[str, Any]] = field(default_factory=list)
    hit_rate: dict[str, Any] = field(default_factory=dict)
    volume_trend: list[dict[str, Any]] = field(default_factory=list)
    daily_activity: list[dict[str, Any]] = field(default_factory=list)


async def create_retrieval_log(
    *,
    user_id: str,
    query: str,
    latency_ms: int,
    hit_count: int,
    session_id: str | None = None,
    run_id: str | None = None,
    top_k: int = 5,
    rerank: bool = False,
    min_score: float | None = None,
    sources: list[dict[str, Any]] | None = None,
) -> None:
    """Append a retrieval activity log entry (write-only by design)."""
    entry = RetrievalLogDB(
        user_id=user_id,
        session_id=session_id,
        run_id=run_id,
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
                "text": s.get("text"),
            }
            for s in sources
        ],
        ensure_ascii=False,
    )


def _time_conds(
    since_hours: int | None,
    since: datetime | None,
    until: datetime | None,
) -> list[Any]:
    """Build created_at window conditions.

    Custom absolute range (since/until) takes precedence over the trailing
    ``since_hours`` preset — powers both the drill-down link and the
    header RangePicker on the logs page.
    """
    conds: list[Any] = []
    if since is not None:
        conds.append(RetrievalLogDB.created_at >= since)
    elif since_hours is not None and since_hours > 0:
        conds.append(
            RetrievalLogDB.created_at
            >= datetime.now(UTC) - timedelta(hours=since_hours)
        )
    if until is not None:
        conds.append(RetrievalLogDB.created_at <= until)
    return conds


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _bucket_seconds(span: timedelta) -> int:
    """Whole-hour bucket size giving ~24 points across the window."""
    hours = max(1.0, span.total_seconds() / 3600)
    return int(-(-hours // 24)) * 3600


async def _trend_window(
    session: Any,
    base_conds: list[Any],
    since_hours: int | None,
    since: datetime | None,
    until: datetime | None,
) -> tuple[datetime, datetime] | None:
    """Resolve the [start, end) window the trend chart covers.

    Absolute range > trailing preset > all-time (earliest row → now).
    Returns None when the user has no rows at all.
    """
    now = datetime.now(UTC)
    if since is not None:
        start = _aware(since)
        return start, _aware(until) if until is not None else now
    if since_hours is not None and since_hours > 0:
        return now - timedelta(hours=since_hours), now
    earliest = await session.scalar(
        select(func.min(RetrievalLogDB.created_at)).where(*base_conds)
    )
    if earliest is None:
        return None
    return _aware(earliest), now


async def list_retrieval_logs(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    min_hit_count: int | None = None,
    max_latency_ms: int | None = None,
    empty_only: bool = False,
    since_hours: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> tuple[list[RetrievalLogDB], int]:
    """List retrieval logs for a user with pagination and filters.

    Window resolution: absolute ``since``/``until`` wins over the trailing
    ``since_hours`` preset (None/<=0 = all time).
    """
    factory = get_session_factory()
    async with factory() as session:
        conds = [RetrievalLogDB.user_id == user_id]
        if min_hit_count is not None:
            conds.append(RetrievalLogDB.hit_count >= min_hit_count)
        if max_latency_ms is not None:
            conds.append(RetrievalLogDB.latency_ms <= max_latency_ms)
        if empty_only:
            conds.append(RetrievalLogDB.hit_count == 0)
        conds.extend(_time_conds(since_hours, since, until))
        query = select(RetrievalLogDB).where(*conds)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(RetrievalLogDB.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        items = list(result.scalars().all())

        return items, total


async def get_retrieval_stats(
    user_id: str,
    since_hours: int | None = None,
    empty_only: bool = False,
    max_latency_ms: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> RetrievalStats:
    """Get aggregated retrieval statistics for chart visualization.

    Returns latency distribution, hit rate, adaptive-bucket volume trend,
    and daily activity.

    Condition scoping — composition metrics must never be constrained by a
    filter on their own dimension, or they collapse into tautologies
    (empty-only → hit rate pinned at 100%; max-latency → >300ms bucket zeroed):

    - ``latency_distribution`` / ``hit_rate``: baseline scope (user + time
      window) — always the full-window picture.
    - ``volume_trend`` / ``daily_activity``: subset scope (baseline + row
      filters) — "when do the filtered failures happen" stays informative.
    """
    factory = get_session_factory()
    async with factory() as session:
        base_conds: list[Any] = [RetrievalLogDB.user_id == user_id]
        base_conds.extend(_time_conds(since_hours, since, until))

        subset_conds = list(base_conds)
        if empty_only:
            subset_conds.append(RetrievalLogDB.hit_count == 0)
        if max_latency_ms is not None:
            subset_conds.append(RetrievalLogDB.latency_ms <= max_latency_ms)

        # 1. Latency distribution: <150ms, 150-300ms, >300ms (baseline scope)
        latency_query = select(
            case(
                (RetrievalLogDB.latency_ms < 150, "<150ms"),
                (RetrievalLogDB.latency_ms < 300, "150-300ms"),
                else_=">300ms",
            ).label("latency_bucket"),
            func.count().label("cnt"),
        ).where(*base_conds).group_by("latency_bucket")
        latency_result = await session.execute(latency_query)
        latency_rows = latency_result.all()
        total_count = sum(int(r.cnt) for r in latency_rows)
        latency_distribution = [
            {
                "range": r.latency_bucket,
                "count": r.cnt,
                "percentage": round(int(r.cnt) / total_count * 100, 1) if total_count > 0 else 0,
            }
            for r in latency_rows
        ]

        # 2. Hit rate: empty recall vs hit recall (baseline scope)
        total = await session.scalar(select(func.count()).where(*base_conds)) or 0
        empty_recall = await session.scalar(
            select(func.count()).where(*base_conds, RetrievalLogDB.hit_count == 0)
        ) or 0
        hit_rate = {
            "total": total,
            "empty_recall": empty_recall,
            "hit_recall": total - empty_recall,
            "empty_recall_rate": round(empty_recall / total * 100, 1) if total > 0 else 0,
        }

        # 3. Volume trend — adaptive time buckets (~24 points), subset scope.
        #    Follows the selected window (preset or custom range) instead of
        #    collapsing everything into hour-of-day.
        window = await _trend_window(
            session, base_conds, since_hours, since, until
        )
        volume_trend: list[dict[str, Any]] = []
        if window is not None:
            start, end = window
            bucket_secs = _bucket_seconds(end - start)
            # Epoch-integer bucketing — portable across Postgres and SQLite
            # (tests). to_timestamp() is Postgres-only.
            bucket = (
                func.floor(
                    func.extract("epoch", RetrievalLogDB.created_at)
                    / bucket_secs
                )
                * bucket_secs
            ).label("bucket")
            trend_query = (
                select(
                    bucket,
                    func.count().label("cnt"),
                    func.avg(RetrievalLogDB.latency_ms).label("avg_lat"),
                )
                .where(*subset_conds)
                .group_by("bucket")
                .order_by("bucket")
            )
            trend_result = await session.execute(trend_query)
            counts = {
                int(r.bucket): (int(r.cnt), r.avg_lat)
                for r in trend_result.all()
            }
            first = int(start.timestamp()) // bucket_secs * bucket_secs
            last = int(end.timestamp())
            for ts in range(first, last + 1, bucket_secs):
                cnt, avg_lat = counts.get(ts, (0, None))
                volume_trend.append(
                    {
                        "ts": datetime.fromtimestamp(ts, UTC).isoformat(),
                        "count": cnt,
                        "avg_latency": round(float(avg_lat), 1)
                        if avg_lat
                        else 0,
                    }
                )

        # 4. Daily activity (day of week x hour) for heatmap — subset scope
        daily_query = select(
            func.extract("dow", RetrievalLogDB.created_at).label("dow"),
            func.extract("hour", RetrievalLogDB.created_at).label("hr"),
            func.count().label("cnt"),
        ).where(*subset_conds).group_by("dow", "hr").order_by("dow", "hr")
        daily_result = await session.execute(daily_query)
        daily_activity = [
            {
                "day": int(r.dow),
                "hour": int(r.hr),
                "count": r.cnt,
            }
            for r in daily_result.all()
        ]

    return RetrievalStats(
        latency_distribution=latency_distribution,
        hit_rate=hit_rate,
        volume_trend=volume_trend,
        daily_activity=daily_activity,
    )
