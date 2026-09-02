"""Latency distribution analytics for the diagnosis tab (heatmap + scatter).

Read-only companions to repository/monitoring.py:
- ``latency_heatmap``  → time-bucket × fixed latency-bin count matrix
- ``latency_scatter``  → bounded sample of individual retrievals for
  hit-count vs latency correlation inspection

Window semantics are identical to monitoring.py: sliding ``window_hours``
(or explicit ``since``/``until`` overrides), ``window_hours <= 0`` = all
time, user-isolated rows only.
"""

from bisect import bisect_right
from datetime import UTC, datetime, timedelta
from typing import Any

from core.infra.database import RetrievalLogDB, get_session_factory
from sqlalchemy import func, select

from repository.monitoring_shared import (
    resolve_window_lower,
    window_conds,
)
from repository.monitoring_timeseries import (
    MAX_BUCKETS,
    align_index,
    bucket_hours,
    resolve_grid_anchor,
)

# Fixed latency-bin edges (ms): aligned with the p95 SLO default of 8000;
# everything above the last edge forms its own open-ended bin. Single source
# of truth — the frontend derives bin labels from the returned edges.
LATENCY_BIN_EDGES_MS = (500, 1000, 2000, 4000, 8000)
BIN_COUNT = len(LATENCY_BIN_EDGES_MS) + 1


def _bin_index(latency_ms: int) -> int:
    """Right-closed binning: [0,500)→0 … [4000,8000)→4, ≥8000→5."""
    return bisect_right(LATENCY_BIN_EDGES_MS, latency_ms)


def _iso(dt: datetime) -> str:
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).isoformat()


async def latency_heatmap(
    user_id: str,
    window_hours: int,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Retrieval counts on a time-bucket × latency-bin aligned grid.

    Same bucket ladder / grid cap as ``quality_timeseries`` so both charts
    stay visually comparable on the same window. Bins are fixed-width
    (see LATENCY_BIN_EDGES_MS); the last bin is open-ended (≥8s).
    """
    lower_eff = resolve_window_lower(window_hours, since)
    factory = get_session_factory()
    async with factory() as session:
        upper = until if until is not None else datetime.now(UTC)
        anchor, span_h = await resolve_grid_anchor(session, user_id, lower_eff, upper)
        bucket = bucket_hours(span_h)
        n_points = int(min(max(-(-span_h // bucket), 1), MAX_BUCKETS))
        start = upper - timedelta(hours=bucket * n_points)

        rows = (
            await session.execute(
                select(RetrievalLogDB.created_at, RetrievalLogDB.latency_ms).where(
                    *window_conds(
                        RetrievalLogDB.user_id,
                        RetrievalLogDB.created_at,
                        user_id,
                        start,
                        upper,
                    )
                )
            )
        ).all()

    grid: list[dict[str, Any]] = [
        {
            "ts": (start + timedelta(hours=i * bucket)).isoformat(),
            "counts": [0] * BIN_COUNT,
        }
        for i in range(n_points)
    ]
    for created_at, latency_ms in rows:
        idx = align_index(created_at, start, bucket, len(grid))
        if idx is None or latency_ms is None:
            continue
        grid[idx]["counts"][_bin_index(int(latency_ms))] += 1

    return {
        "window_hours": window_hours,
        "bucket_hours": bucket,
        "bin_edges_ms": list(LATENCY_BIN_EDGES_MS),
        "points": grid,
    }


async def latency_scatter(
    user_id: str,
    window_hours: int,
    *,
    limit: int = 1000,
    since: datetime | None = None,
    until: datetime | None = None,
) -> dict[str, Any]:
    """Bounded sample of individual retrievals (newest-first capped).

    Returns the window total plus the sampled subset in chronological
    order, so the frontend can flag truncation honestly.
    """
    lower_eff = resolve_window_lower(window_hours, since)
    factory = get_session_factory()
    async with factory() as session:
        conds = window_conds(
            RetrievalLogDB.user_id,
            RetrievalLogDB.created_at,
            user_id,
            lower_eff,
            until,
        )
        total = int(
            (
                await session.execute(
                    select(func.count()).select_from(RetrievalLogDB).where(*conds)
                )
            ).scalar_one()
        )
        # Newest-first cap: the scatter only serves correlation inspection,
        # so over-limit traffic keeps its most recent shape.
        rows = (
            await session.execute(
                select(
                    RetrievalLogDB.created_at,
                    RetrievalLogDB.hit_count,
                    RetrievalLogDB.latency_ms,
                )
                .where(*conds)
                .order_by(RetrievalLogDB.created_at.desc())
                .limit(limit)
            )
        ).all()

    items = [
        {
            "ts": _iso(created_at),
            "hits": int(hit_count or 0),
            "latency_ms": int(latency_ms),
        }
        for created_at, hit_count, latency_ms in reversed(rows)
    ]
    return {
        "window_hours": window_hours,
        "total": total,
        "sampled": len(items),
        "items": items,
    }
