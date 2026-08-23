"""Online quality metrics aggregation + alert evaluation (R3, ENTERPRISE_RAG_TOP_BAR §4 #7).

Read-only analytics over the append-only retrieval_logs and feedback_logs.
Counts are aggregated in SQL; latency percentiles are computed in Python
from the latest bounded sample of the window. PostgreSQL has native
percentile_cont(), but the in-memory sqlite used by unit tests does not —
the nearest-rank Python percentile keeps behavior identical across both.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from core.infra.database import (
    FeedbackLog,
    FeedbackReviewDB,
    RetrievalLogDB,
    get_session_factory,
)
from core.infra.database import ProjectRun, SessionDB
from sqlalchemy import func, select

# Cap latency samples pulled for percentile computation (defensive bound for
# very large windows — alerting percentiles stay stable beyond this).
_LATENCY_SAMPLE_LIMIT = 10000

# 与 feedback_reviews.root_cause 的枚举一致（单一事实来源在 ORM 迁移注释）。
_ROOT_CAUSES = ("retrieval_miss", "wrong_answer", "bad_format", "other")

# Trend-bucket granularity ladder (hours); pick the finest that keeps the
# grid ≤ ~48 points, so "all time" stays bounded too.
_BUCKET_LADDER_H = (1, 4, 12, 24, 72, 168, 336, 720)
_MAX_BUCKETS = 48


def _window_since(window_hours: int) -> datetime | None:
    """Window lower bound; None means "all time" (window_hours <= 0)."""
    if window_hours <= 0:
        return None
    return datetime.now(UTC) - timedelta(hours=window_hours)


def _resolve_lower(
    window_hours: int, since: datetime | None
) -> datetime | None:
    """Custom ``since`` overrides the sliding-window lower bound."""
    return since if since is not None else _window_since(window_hours)


def _window_conds(
    user_col,
    time_col,
    user_id: str,
    lower: datetime | None,
    upper: datetime | None = None,
):
    """Common WHERE conditions: user isolation + optional time bounds."""
    conds = [user_col == user_id]
    if lower is not None:
        conds.append(time_col >= lower)
    if upper is not None:
        conds.append(time_col <= upper)
    return conds


async def retrieval_summary(
    user_id: str,
    window_hours: int,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Aggregate retrieval activity in the window: volume, empty recall, latency.

    ``window_hours <= 0`` means "all time"; explicit ``since``/``until``
    override the sliding-window bounds.
    """
    lower = _resolve_lower(window_hours, since)
    factory = get_session_factory()
    async with factory() as session:
        agg = (
            select(
                func.count().label("total"),
                func.count().filter(RetrievalLogDB.hit_count <= 0).label("empty"),
                func.avg(RetrievalLogDB.hit_count).label("avg_hits"),
            ).where(
                *_window_conds(
                    RetrievalLogDB.user_id,
                    RetrievalLogDB.created_at,
                    user_id,
                    lower,
                    until,
                )
            )
        )
        row = (await session.execute(agg)).one()
        total = int(row.total)
        empty_recall = int(row.empty)
        avg_hits = round(float(row.avg_hits), 2) if row.avg_hits is not None else None
        latency_stmt = (
            select(RetrievalLogDB.latency_ms)
            .where(
                *_window_conds(
                    RetrievalLogDB.user_id,
                    RetrievalLogDB.created_at,
                    user_id,
                    lower,
                    until,
                )
            )
            # Newest-first sample: with more rows than the cap, the most
            # recent traffic (not the window's tail) drives alerting.
            .order_by(RetrievalLogDB.created_at.desc())
            .limit(_LATENCY_SAMPLE_LIMIT)
        )
        latencies = list((await session.execute(latency_stmt)).scalars())
    return {
        "total": total,
        "empty_recall_count": empty_recall,
        "empty_recall_rate": (empty_recall / total) if total else 0.0,
        "avg_hit_count": avg_hits,
        "latency_p50_ms": _percentile(latencies, 50),
        "latency_p95_ms": _percentile(latencies, 95),
        "latency_p99_ms": _percentile(latencies, 99),
    }


async def feedback_summary(
    user_id: str,
    window_hours: int,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Aggregate answer-quality feedback in the window: volume and good ratio.

    ``window_hours <= 0`` means "all time".
    """
    lower = _resolve_lower(window_hours, since)
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(
                func.count().label("total"),
                func.count().filter(FeedbackLog.rating == "good").label("good"),
            ).where(
                *_window_conds(
                    FeedbackLog.user_id,
                    FeedbackLog.created_at,
                    user_id,
                    lower,
                    until,
                )
            )
        )
        row = (await session.execute(stmt)).one()
        total = int(row.total)
        good = int(row.good)

        # 覆盖率分母：窗口内成功完成的回答数（好评率的可信度取决于此）。
        answered = 0
        try:
            async with factory() as session:
                conds = [ProjectRun.status == "converged"]
                if lower is not None:
                    conds.append(ProjectRun.created_at >= lower)
                if until is not None:
                    conds.append(ProjectRun.created_at <= until)
                stmt = (
                    select(func.count())
                    .select_from(ProjectRun)
                    .join(SessionDB, ProjectRun.session_id == SessionDB.id)
                    .where(SessionDB.user_id == user_id, *conds)
                )
                answered = int((await session.execute(stmt)).scalar() or 0)
        except Exception:
            # 分母缺失只降级展示，不阻塞 summary。
            answered = 0

    return {
        "total": total,
        "good_count": good,
        "bad_count": total - good,
        "good_ratio": (good / total) if total else None,
        "answered_runs": answered,
    }


def evaluate_alerts(
    retrieval: dict[str, Any],
    feedback: dict[str, Any],
    *,
    max_empty_recall_pct: float = 15.0,
    max_p95_latency_ms: int = 8000,
    min_good_ratio: float = 0.6,
) -> list[dict[str, Any]]:
    """Compare metrics against thresholds; pure, fully unit-testable."""
    alerts: list[dict[str, Any]] = []

    empty_pct = retrieval.get("empty_recall_rate", 0.0) * 100
    if retrieval.get("total", 0) > 0 and empty_pct > max_empty_recall_pct:
        alerts.append(_alert("warning", "empty_recall_high", empty_pct, max_empty_recall_pct))

    p95 = retrieval.get("latency_p95_ms")
    if p95 is not None and p95 > max_p95_latency_ms:
        alerts.append(_alert("warning", "p95_latency_high", p95, max_p95_latency_ms))

    good_ratio = feedback.get("good_ratio")
    if feedback.get("total", 0) > 0 and good_ratio is not None and good_ratio < min_good_ratio:
        alerts.append(_alert("warning", "good_ratio_low", good_ratio, min_good_ratio))

    return alerts


def _alert(level: str, code: str, current: float, threshold: float) -> dict[str, Any]:
    return {"level": level, "code": code, "current": current, "threshold": threshold}


def _percentile(values: list[int], pct: int) -> int | None:
    """Nearest-rank percentile; None when no samples."""
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, round(pct / 100 * len(ordered)) - 1))
    return ordered[idx]


def _bucket_hours(span_hours: float) -> int:
    """Finest ladder granularity keeping the grid within _MAX_BUCKETS points."""
    for bucket in _BUCKET_LADDER_H:
        if span_hours / bucket <= _MAX_BUCKETS:
            return bucket
    return _BUCKET_LADDER_H[-1]


async def quality_timeseries(
    user_id: str,
    window_hours: int,
    *,
    include_previous: bool = False,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Retrieval + feedback trends on one aligned time grid.

    Bucketing happens in Python instead of SQL ``date_trunc``/``strftime``:
    the in-memory sqlite used by unit tests lacks PG's date functions, and
    the Python path keeps behavior identical across both backends — same
    trade-off as the nearest-rank percentiles above.

    ``window_hours <= 0`` means "all time": the span is derived from the
    oldest log row and the grid is capped at the most recent _MAX_BUCKETS
    buckets. Explicit ``since``/``until`` override the sliding window.

    ``include_previous`` (preset windows only) doubles the fetched range
    and additionally returns the immediately preceding equal-length period
    on the same bucket grid — index-aligned for ghost-line overlays and
    true previous-period deltas.
    """
    factory = get_session_factory()

    # 粒度与点数只取决于当前窗口长度（不含上期），保证与单窗行为一致。
    upper = until if until is not None else datetime.now(UTC)
    lower_eff = _resolve_lower(window_hours, since)
    async with factory() as session:
        anchor = lower_eff
        if anchor is None:
            oldest = (
                await session.execute(
                    select(func.min(RetrievalLogDB.created_at)).where(
                        RetrievalLogDB.user_id == user_id
                    )
                )
            ).scalar_one_or_none()
            anchor = (
                oldest if oldest is not None else upper - timedelta(hours=24)
            )
        anchor = anchor if anchor.tzinfo else anchor.replace(tzinfo=UTC)
        span_h = max((upper - anchor).total_seconds() / 3600, 1.0)

        bucket = _bucket_hours(span_h)
        n_points = min(max(-(-span_h // bucket), 1), _MAX_BUCKETS)

        # 上期序列仅在预设窗口下提供（自定义范围没有规范的"上一期"）。
        periods = (
            2
            if include_previous and window_hours > 0 and since is None and until is None
            else 1
        )
        total_points = int(n_points) * periods
        start = upper - timedelta(hours=bucket * total_points)

        retrieval_conds = _window_conds(
            RetrievalLogDB.user_id,
            RetrievalLogDB.created_at,
            user_id,
            start,
            upper,
        )
        rows = (
            (
                await session.execute(
                    select(
                        RetrievalLogDB.created_at,
                        RetrievalLogDB.hit_count,
                        RetrievalLogDB.latency_ms,
                    ).where(*retrieval_conds)
                )
            )
            .all()
        )
        feedback_rows = (
            (
                await session.execute(
                    select(FeedbackLog.created_at, FeedbackLog.rating).where(
                        *_window_conds(
                            FeedbackLog.user_id,
                            FeedbackLog.created_at,
                            user_id,
                            start,
                            upper,
                        )
                    )
                )
            )
            .all()
        )

    # Align both sources onto one grid: point i covers (start + i*bucket, …].
    grid: list[dict[str, Any]] = [
        {
            "ts": (start + timedelta(hours=i * bucket)).isoformat(),
            "retrievals": 0,
            "empty_count": 0,
            "latencies": [],
            "hits": [],
            "good": 0,
            "bad": 0,
        }
        for i in range(total_points)
    ]

    def _idx_of(ts: datetime) -> int | None:
        ts = ts if ts.tzinfo else ts.replace(tzinfo=UTC)
        offset = (ts - start).total_seconds() / 3600
        idx = int(offset // bucket)
        return idx if 0 <= idx < len(grid) else None

    for created_at, hit_count, latency_ms in rows:
        idx = _idx_of(created_at)
        if idx is None:
            continue
        point = grid[idx]
        point["retrievals"] += 1
        if (hit_count or 0) <= 0:
            point["empty_count"] += 1
        if hit_count is not None:
            point["hits"].append(hit_count)
        if latency_ms is not None:
            point["latencies"].append(latency_ms)

    for created_at, rating in feedback_rows:
        idx = _idx_of(created_at)
        if idx is None:
            continue
        grid[idx]["good" if rating == "good" else "bad"] += 1

    points = [
        {
            "ts": p["ts"],
            "retrievals": p["retrievals"],
            "empty_count": p["empty_count"],
            "avg_hits": (
                round(sum(p["hits"]) / len(p["hits"]), 2) if p["hits"] else None
            ),
            "avg_latency_ms": (
                round(sum(p["latencies"]) / len(p["latencies"]))
                if p["latencies"]
                else None
            ),
            # 桶级分位数：驱动监控页的延迟分位数带图。
            "latency_p50_ms": _percentile(p["latencies"], 50),
            "latency_p95_ms": _percentile(p["latencies"], 95),
            "latency_p99_ms": _percentile(p["latencies"], 99),
            "good": p["good"],
            "bad": p["bad"],
        }
        for p in grid
    ]

    split = int(n_points)
    previous_points: list[dict[str, Any]] | None = None
    if periods == 2:
        previous_points = points[:split]
        points = points[split:]
    return {
        "window_hours": window_hours,
        "bucket_hours": bucket,
        "points": points,
        "previous_points": previous_points,
    }


async def root_cause_breakdown(
    user_id: str,
    window_hours: int,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Aggregate bad-feedback triage state in the window.

    Single-pass conditional aggregation over bad ratings joined to their
    review records: status mix (unreviewed ≡ pending) + per-root-cause
    counts. ``window_hours <= 0`` means "all time".
    """
    lower = _resolve_lower(window_hours, since)
    factory = get_session_factory()
    async with factory() as session:
        conds = _window_conds(
            FeedbackLog.user_id,
            FeedbackLog.created_at,
            user_id,
            lower,
            until,
        )
        conds.append(FeedbackLog.rating == "bad")

        cols: list[Any] = [func.count().label("total")]
        for cause in _ROOT_CAUSES:
            cols.append(
                func.count()
                .filter(FeedbackReviewDB.root_cause == cause)
                .label(f"c_{cause}")
            )
        cols.append(
            func.count()
            .filter(FeedbackReviewDB.status == "resolved")
            .label("resolved")
        )
        cols.append(
            func.count()
            .filter(FeedbackReviewDB.status == "dismissed")
            .label("dismissed")
        )
        stmt = (
            select(*cols)
            .select_from(FeedbackLog)
            .outerjoin(FeedbackReviewDB, FeedbackReviewDB.feedback_id == FeedbackLog.id)
            .where(*conds)
        )
        row = (await session.execute(stmt)).one()

    total = int(row.total)
    resolved = int(row.resolved)
    dismissed = int(row.dismissed)
    return {
        "window_hours": window_hours,
        "total_bad": total,
        # 未审查的差评视同 pending（review 为 NULL 时两个状态计数都不命中）。
        "pending": total - resolved - dismissed,
        "resolved": resolved,
        "dismissed": dismissed,
        "causes": [
            {"cause": cause, "count": int(getattr(row, f"c_{cause}"))}
            for cause in _ROOT_CAUSES
        ],
    }


async def top_queries(
    user_id: str,
    window_hours: int,
    *,
    kind: str = "empty",
    limit: int = 10,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Rank recurring problem queries in the window.

    ``kind="empty"`` ranks zero-hit queries by frequency (corpus gaps to
    fill); ``kind="slow"`` ranks by average latency (performance hotspots).
    ``window_hours <= 0`` means "all time".
    """
    lower = _resolve_lower(window_hours, since)
    factory = get_session_factory()
    async with factory() as session:
        conds = _window_conds(
            RetrievalLogDB.user_id,
            RetrievalLogDB.created_at,
            user_id,
            lower,
            until,
        )
        order_col = func.avg(RetrievalLogDB.latency_ms)
        if kind == "empty":
            conds.append(RetrievalLogDB.hit_count <= 0)
            order_col = func.count()

        stmt = (
            select(
                RetrievalLogDB.query.label("query"),
                func.count().label("n"),
                func.avg(RetrievalLogDB.latency_ms).label("avg_latency"),
            )
            .where(*conds)
            .group_by(RetrievalLogDB.query)
            .order_by(order_col.desc())
            .limit(limit)
        )
        rows = (await session.execute(stmt)).all()

    return {
        "window_hours": window_hours,
        "kind": kind,
        "items": [
            {
                "query": r.query,
                "count": int(r.n),
                "avg_latency_ms": (
                    round(float(r.avg_latency)) if r.avg_latency is not None else None
                ),
            }
            for r in rows
        ],
    }
