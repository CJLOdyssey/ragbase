"""Periodic reindex sweep — catches files changed on disk after indexing.

Celery beat runs this every few minutes: an indexed asset whose file mtime
is newer than its updated_at row was replaced/edited externally, so its
chunks are stale; an unindexed asset (failed first attempt) is retried.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


async def _reindex_sweep() -> dict[str, int]:
    from core.infra.database import AssetDB, get_session_factory
    from sqlalchemy import select

    factory = get_session_factory()
    async with factory() as session:
        rows = (await session.execute(select(AssetDB))).scalars().all()

    queued = 0
    for asset in rows:
        path = Path(asset.storage_path)
        if not path.exists():
            continue
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        indexed_at = asset.updated_at
        if indexed_at is None:
            indexed_at = asset.created_at
        if not asset.indexed or mtime > indexed_at:
            from tasks.registry import index_asset

            index_asset.delay(asset.id, asset.user_id)
            queued += 1
    return {"queued": queued}


def run_reindex_sweep() -> dict[str, Any]:
    """Sync entrypoint for the Celery task wrapper."""
    import asyncio

    return asyncio.run(_reindex_sweep())
