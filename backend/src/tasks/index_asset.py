"""Async asset indexing — Celery worker side of /api/assets/{id}/index.

Moves chunking/embedding/store out of the HTTP request. Idempotent: clears
the asset's previous chunks before writing, so re-indexing never leaves
stale fragments behind (chunk ids are content hashes — changed text would
otherwise orphan old rows).
"""

from typing import Any


async def _index_asset(asset_id: str, user_id: str) -> dict[str, Any]:
    from rag.rag_chunking import semantic_chunk
    from rag.rag_embedding import EmbeddingProvider
    from rag.rag_store import PgVectorStore
    from repository.assets import get_asset, set_asset_index_result
    from repository.index_progress import set_index_progress
    from repository.keys import get_embedding_config
    from repository.knowledge_bases import get_kb

    asset = await get_asset(asset_id)
    if asset is None or asset.user_id != user_id:
        raise ValueError(f"asset {asset_id} not found or not owned by user")

    # Per-KB binding: vectors in one KB share a single embedding space, so the
    # owning KB's bound model (when set) wins over the global heuristic.
    kb_embed_model: str | None = None
    kb_parser_config: dict[str, Any] | None = None
    if asset.knowledge_base_id:
        kb = await get_kb(asset.knowledge_base_id, user_id)
        if kb is not None:
            kb_embed_model = getattr(kb, "embed_model", None)
            kb_parser_config = getattr(kb, "parser_config", None) or None

    from rag.rag_guard import ALLOWED_INDEX_SOURCES, scan_document
    from rag.rag_parsing import extract_text

    try:
        # OWASP LLM08 source whitelist: only known ingestion channels may index.
        if asset.source not in ALLOWED_INDEX_SOURCES:
            raise ValueError(
                f"asset source {asset.source!r} not allowed for indexing"
            )

        text = extract_text(asset.storage_path)
        if not text.strip():
            raise ValueError("asset has no text content — cannot index")

        # OWASP LLM08: reject poisoned/hidden-instruction text before it reaches
        # the vector store — a flagged asset stays unindexed, fail-loud.
        reasons = scan_document(text)
        if reasons:
            raise ValueError(
                f"asset rejected by document guard: {'; '.join(reasons)}"
            )

        await set_index_progress(asset_id, "chunking", 30, "Chunking document...")

        cfg = await get_embedding_config(preferred_model=kb_embed_model)
        if cfg is None or cfg["api_key"] is None:
            raise RuntimeError("no embedding API key configured")

        # Per-KB chunking parameters (engine-honest: size + word-window overlap).
        chunk_size = 512
        overlap = 64
        if kb_parser_config:
            raw_size = kb_parser_config.get("chunk_size")
            raw_overlap = kb_parser_config.get("overlap")
            if isinstance(raw_size, int):
                chunk_size = max(50, min(2000, raw_size))
            if isinstance(raw_overlap, int):
                overlap = max(0, min(chunk_size - 1, raw_overlap))

        chunks = semantic_chunk(
            text,
            session_id=f"asset:{asset.id}",
            run_id=None,
            chunk_size=chunk_size,
            overlap=overlap,
        )
        # User-curated asset tags ride along on every chunk so retrieval can
        # filter by them (store's tag_filter leg).
        asset_tags = [t.strip().lower() for t in (getattr(asset, "tags", None) or []) if t.strip()]
        if asset_tags:
            for c in chunks:
                c.tags = list(dict.fromkeys([*c.tags, *asset_tags]))

        await set_index_progress(asset_id, "embedding", 50, "Generating embeddings...")

        provider = EmbeddingProvider(
            api_key=cfg["api_key"],
            model=cfg["model"] or "text-embedding-v3",
            base_url=cfg["base_url"],
        )
        embeddings = await provider.embed([c.text for c in chunks])
        for chunk, emb in zip(chunks, embeddings, strict=False):
            chunk.embedding = emb
            # Record the model that produced this vector — retrieval groups by
            # it so mixed-model corpora never cross vector spaces.
            chunk.metadata = {
                "asset_id": asset.id,
                "asset_name": asset.name,
                "embed_model": provider.model,
            }

        # Race guard against a concurrent rebind: if the KB's binding changed
        # while we were embedding, these vectors belong to the old space —
        # abort (fail-loud) and let the reindex sweep redo it with the new one.
        if kb_embed_model is not None and provider.model != kb_embed_model:
            raise RuntimeError(
                f"KB embed model changed to {kb_embed_model!r} mid-indexing; "
                "discarding stale-space vectors"
            )

        await set_index_progress(asset_id, "storing", 80, "Storing vectors...")

        store = PgVectorStore()
        await store.clear_asset(asset.id)  # idempotent reindex: no stale chunks
        await store.add(chunks, user_id=user_id)
        await set_asset_index_result(asset.id, True, None)

        await set_index_progress(asset_id, "done", 100, "Indexing complete")
        return {"indexed": True, "chunks": len(chunks)}
    except Exception as exc:
        # Persist the failure terminal state (Redis progress alone has a
        # 10-min TTL — the UI must see "failed" after refresh, not a
        # silent fallback to "unindexed").
        await set_asset_index_result(asset_id, False, str(exc))
        await set_index_progress(asset_id, "failed", 0, str(exc))
        raise
