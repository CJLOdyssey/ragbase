"""Time-bucketed monitoring grids (trend/heatmap/scatter shared helpers).

Split out of ``repository.monitoring`` to honor the ≤400-line module rule.
Bucketing happens in Python instead of SQL ``date_trunc``/``strftime``:
the in-memory sqlite used by unit tests lacks PG's date functions, and the
Python path keeps behavior identical across both backends — same trade-off
as the nearest-rank percentiles in the parent module.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from core.infra.database import (
    FeedbackLog,
    RetrievalLogDB,
    get_session_factory,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from repository.monitoring_shared import (
    percentile_nearest_rank,
    resolve_window_lower,
    window_conds,
)

# Trend-bucket granularity ladder (hours); pick the finest that keeps the
# grid ≤ ~48 points, so "all time" stays bounded too.
_BUCKET_LADDER_H = (1, 4, 12, 24, 72, 168, 336, 720)
MAX_BUCKETS = 48


def bucket_hours(span_hours: float) -> int:
    """Finest ladder granularity keeping the grid within MAX_BUCKETS points."""
    for bucket in _BUCKET_LADDER_H:
        if span_hours / bucket <= MAX_BUCKETS:
            return bucket
    return _BUCKET_LADDER_H[-1]


async def resolve_grid_anchor(
    session: AsyncSession,
    user_id: str,
    lower_eff: datetime | None,
    upper: datetime,
) -> tuple[datetime, float]:
    """Effective span anchor for aligned bucket grids (timeseries/heatmap).

    Explicit lower bound wins; otherwise fall back to the user's oldest
    retrieval row ("all time"), or the last 24h when the log is empty.
    Returns ``(anchor, span_hours>=1)``.
    """
    anchor = lower_eff
    if anchor is None:
        oldest = (
            await session.execute(
                select(func.min(RetrievalLogDB.created_at)).where(
                    RetrievalLogDB.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        anchor = oldest if oldest is not None else upper - timedelta(hours=24)
    anchor = anchor if anchor.tzinfo else anchor.replace(tzinfo=UTC)
    return anchor, max((upper - anchor).total_seconds() / 3600, 1.0)


def align_index(ts: datetime, start: datetime, bucket: int, size: int) -> int | None:
    """Bucket-grid index for ``ts``; None when outside ``[start, start+size)``."""
    ts = ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    offset = (ts - start).total_seconds() / 3600
    idx = int(offset // bucket)
    return idx if 0 <= idx < size else None


async def quality_timeseries(
    user_id: str,
    window_hours: int,
    *,
    include_previous: bool = False,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Retrieval + feedback trends on one aligned time grid.

    ``window_hours <= 0`` means "all time": the span is derived from the
    oldest log row and the grid is capped at the most recent MAX_BUCKETS
    buckets. Explicit ``since``/``until`` override the sliding window.

    ``include_previous`` (preset windows only) doubles the fetched range
    and additionally returns the immediately preceding equal-length period
    on the same bucket grid — index-aligned for ghost-line overlays and
    true previous-period deltas.
    """
    factory = get_session_factory()

    # 粒度与点数只取决于当前窗口长度（不含上期），保证与单窗行为一致。
    upper = until if until is not None else datetime.now(UTC)
    lower_eff = resolve_window_lower(window_hours, since)
    async with factory() as session:
        anchor, span_h = await resolve_grid_anchor(session, user_id, lower_eff, upper)

        bucket = bucket_hours(span_h)
        n_points = min(max(-(-span_h // bucket), 1), MAX_BUCKETS)

        # 上期序列仅在预设窗口下提供（自定义范围没有规范的"上一期"）。
        periods = (
            2
            if include_previous and window_hours > 0 and since is None and until is None
            else 1
        )
        total_points = int(n_points) * periods
        start = upper - timedelta(hours=bucket * total_points)

        retrieval_conds = window_conds(
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
                        *window_conds(
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
        return align_index(ts, start, bucket, len(grid))

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
            "avg_hits": round(sum(p["hits"]) / len(p["hits"]), 2) if p["hits"] else None,
            "avg_latency_ms": (
                round(sum(p["latencies"]) / len(p["latencies"])) if p["latencies"] else None
            ),
            # 桶级分位数：驱动监控页的延迟分位数带图。
            "latency_p50_ms": percentile_nearest_rank(p["latencies"], 50),
            "latency_p95_ms": percentile_nearest_rank(p["latencies"], 95),
            "latency_p99_ms": percentile_nearest_rank(p["latencies"], 99),
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
