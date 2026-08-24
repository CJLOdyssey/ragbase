"""Chunk governance operations for PgVectorStore (edit/disable/delete/add).

Split from rag_store.py to honor the 400-line file budget; mixed into
PgVectorStore so callers keep a single entry-point object.
"""

import json
from typing import TYPE_CHECKING, Any

from sqlalchemy import text

if TYPE_CHECKING:
    from typing import Protocol

    class _Host(Protocol):
        """Structural view of the store host (avoids a circular type import)."""

        async def _ensure_table(self) -> None: ...
else:
    _Host = object


def _hash_chunk_id(chunk_text: str, salt: str | None = None) -> str:
    """Deterministic content-hash id for curated chunks (dedup by text)."""
    import hashlib

    raw = chunk_text if salt is None else f"{salt}:{chunk_text}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class CurationMixin(_Host):
    """Manual-chunk CRUD: every op is owner-gated and embedding-aware.

    The host base is real under TYPE_CHECKING (so mypy sees _ensure_table)
    and plain ``object`` at runtime — a standard mixin pattern.
    """

    async def _chunk_owner_ok(
        self, session: Any, chunk_id: str, asset_id: str, user_id: str
    ) -> bool:
        """Ownership gate: the chunk must belong to the caller's asset."""
        row = await session.execute(
            text(
                "SELECT 1 FROM vector_chunks "
                "WHERE id = :cid AND asset_id = :aid AND user_id = :uid"
            ),
            {"cid": chunk_id, "aid": asset_id, "uid": user_id},
        )
        return row.scalar() is not None

    async def update_chunk_text(
        self,
        chunk_id: str,
        asset_id: str,
        user_id: str,
        chunk_text: str,
        embedding: list[float],
        embed_model: str | None,
    ) -> str | None:
        """Rewrite a chunk's text and re-embed it in place (manual curation).

        Returns the new (content-hash) chunk id, or None when not found.

        The embedding must be produced by the KB's current binding so the
        chunk stays inside its cohort; embed_model is recorded in metadata.
        """
        await self._ensure_table()
        from core.infra.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            if not await self._chunk_owner_ok(session, chunk_id, asset_id, user_id):
                return None
            emb_str = "[" + ",".join(str(v) for v in embedding) + "]"
            # Content-hash id keeps re-edits idempotent per text.
            new_id = _hash_chunk_id(chunk_text)
            await session.execute(
                text(
                    """
                    UPDATE vector_chunks
                    SET text = :txt,
                        embedding = CAST(:emb AS vector),
                        id = :new_id,
                        enabled = TRUE,
                        metadata = jsonb_set(
                            COALESCE(metadata, '{}'::jsonb),
                            '{embed_model}',
                            to_jsonb(:em::text)
                        )
                    WHERE id = :cid AND asset_id = :aid AND user_id = :uid
                    """
                ),
                {
                    "txt": chunk_text,
                    "emb": emb_str,
                    "new_id": new_id,
                    "cid": chunk_id,
                    "aid": asset_id,
                    "uid": user_id,
                    "em": embed_model,
                },
            )
            await session.commit()
            return new_id

    async def add_manual_chunk(
        self,
        asset_id: str,
        user_id: str,
        chunk_text: str,
        embedding: list[float],
        embed_model: str | None,
        asset_name: str | None = None,
    ) -> str:
        """Insert a manually curated chunk (embedded with the KB's binding).

        Returns the new chunk id (content-hash — duplicate texts are
        idempotent via ON CONFLICT).
        """
        await self._ensure_table()
        from core.infra.database import get_session_factory

        chunk_id = _hash_chunk_id(chunk_text, asset_id)
        emb_str = "[" + ",".join(str(v) for v in embedding) + "]"
        metadata = {
            "asset_id": asset_id,
            **({"asset_name": asset_name} if asset_name else {}),
            "embed_model": embed_model,
            "manual": True,
        }
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(
                text(
                    """
                    INSERT INTO vector_chunks
                        (id, session_id, run_id, text, tags, embedding,
                         user_id, asset_id, metadata, enabled)
                    VALUES (:id, :sid, '', :txt, '{}', CAST(:emb AS vector),
                            :uid, :aid, CAST(:meta AS jsonb), TRUE)
                    ON CONFLICT (id) DO UPDATE
                    SET text = EXCLUDED.text,
                        embedding = EXCLUDED.embedding,
                        enabled = TRUE,
                        metadata = EXCLUDED.metadata
                    """
                ),
                {
                    "id": chunk_id,
                    "sid": f"asset:{asset_id}",
                    "txt": chunk_text,
                    "emb": emb_str,
                    "uid": user_id,
                    "aid": asset_id,
                    "meta": json.dumps(metadata, ensure_ascii=False),
                },
            )
            await session.commit()
        return chunk_id

    async def set_chunk_enabled(
        self, chunk_id: str, asset_id: str, user_id: str, enabled: bool
    ) -> bool:
        """Soft-disable/enable a single chunk (excluded from retrieval)."""
        await self._ensure_table()
        from core.infra.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            if not await self._chunk_owner_ok(session, chunk_id, asset_id, user_id):
                return False
            await session.execute(
                text(
                    "UPDATE vector_chunks SET enabled = :en "
                    "WHERE id = :cid AND asset_id = :aid AND user_id = :uid"
                ),
                {"en": enabled, "cid": chunk_id, "aid": asset_id, "uid": user_id},
            )
            await session.commit()
            return True

    async def delete_chunk(self, chunk_id: str, asset_id: str, user_id: str) -> bool:
        """Hard-delete a single curated chunk."""
        await self._ensure_table()
        from core.infra.database import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            if not await self._chunk_owner_ok(session, chunk_id, asset_id, user_id):
                return False
            await session.execute(
                text(
                    "DELETE FROM vector_chunks "
                    "WHERE id = :cid AND asset_id = :aid AND user_id = :uid"
                ),
                {"cid": chunk_id, "aid": asset_id, "uid": user_id},
            )
            await session.commit()
            return True
