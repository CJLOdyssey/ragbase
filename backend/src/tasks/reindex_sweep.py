"""Periodic reindex sweep — catches files changed on disk after indexing.

Celery beat runs this every few minutes: an indexed asset whose file mtime
is newer than its updated_at row was replaced/edited externally, so its
chunks are stale; an unindexed asset (failed first attempt) is retried.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .index_asset import is_index_in_flight


async def _reindex_sweep() -> dict[str, int]:
    from core.infra.database import AssetDB, get_session_factory
    from sqlalchemy import select

    factory = get_session_factory()
    async with factory() as session:
        # Column projection only: the sweep touches six fields of every row,
        # never ORM mutations — loading full entities per asset is waste.
        rows = (
            await session.execute(
                select(
                    AssetDB.id,
                    AssetDB.user_id,
                    AssetDB.storage_path,
                    AssetDB.indexed,
                    AssetDB.updated_at,
                    AssetDB.created_at,
                )
            )
        ).all()

    queued = 0
    for row in rows:
        path = Path(row.storage_path)
        if not path.exists():
            continue
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        indexed_at = row.updated_at or row.created_at
        # Stale = never indexed (retry a failed attempt) or the file was
        # replaced/edited externally after indexing (mtime newer than row).
        stale = not row.indexed or mtime > indexed_at
        # 并发防重：已有索引任务在飞的资产不入队，避免重复 embedding。
        if not stale or await is_index_in_flight(row.id):
            continue
        from tasks.registry import index_asset

        index_asset.delay(row.id, row.user_id)
        queued += 1
    return {"queued": queued}


def run_reindex_sweep() -> dict[str, Any]:
    """Sync entrypoint for the Celery task wrapper."""
    import asyncio

    return asyncio.run(_reindex_sweep())
