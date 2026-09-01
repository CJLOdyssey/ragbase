"""Periodic purge of orphan vector chunks — assets without a KB binding.

Celery beat runs this hourly: clears vector chunks for assets whose
knowledge_base_id is NULL and indexed flag is True, then resets the indexed
flag so they can be properly re-indexed once assigned to a KB.  Idempotent —
no harm running when there are no orphans.
"""

from typing import Any


async def _purge_orphan_vectors() -> dict[str, int]:
    from core.infra.database import get_session_factory
    from sqlalchemy import text

    factory = get_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT id FROM assets "
                    "WHERE indexed = TRUE AND knowledge_base_id IS NULL"
                )
            )
        ).all()

    if not rows:
        return {"purged": 0}

    orphan_ids = [row[0] for row in rows]

    from rag.rag_store import PgVectorStore

    await PgVectorStore().clear_assets(orphan_ids)

    async with factory() as session:
        await session.execute(
            text(
                "UPDATE assets SET indexed = FALSE, index_error = :err "
                "WHERE id = ANY(:ids)"
            ),
            {"err": "purged: no knowledge base", "ids": orphan_ids},
        )
        await session.commit()

    return {"purged": len(orphan_ids)}


def run_purge_orphan_vectors() -> dict[str, Any]:
    """Sync entrypoint for the Celery task wrapper."""
    import asyncio

    return asyncio.run(_purge_orphan_vectors())
