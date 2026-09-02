"""Async asset indexing — Celery worker side of /api/assets/{id}/index.

Moves chunking/embedding/store out of the HTTP request. Idempotent: clears
the asset's previous chunks before writing, so re-indexing never leaves
stale fragments behind (chunk ids are content hashes — changed text would
otherwise orphan old rows).
"""

from typing import Any

# Stages written while an indexing task is actively working on an asset.
# "done"/"failed" are terminal and must not count as in-flight (a failed
# index must remain retryable by the sweep).
_ACTIVE_INDEX_STAGES = frozenset({"parsing", "chunking", "contextual", "embedding", "storing"})


async def is_index_in_flight(asset_id: str) -> bool:
    """True when another indexing task for this asset appears to be running.

    Progress markers carry a 10-minute TTL, so a crashed worker releases its
    marker on its own; until then duplicate indexing (manual trigger racing
    the periodic sweep) is detected instead of double-embedding.
    """
    from repository.index_progress import get_index_progress

    progress = await get_index_progress(asset_id)
    return progress is not None and progress.get("stage") in _ACTIVE_INDEX_STAGES


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

    # Concurrency dedup: a manual trigger racing the reindex sweep (or a beat
    # overlap) would clear+rewrite chunks twice. The in-flight run owns the
    # asset — skip quietly; the caller's UI keeps tracking that run's progress.
    if await is_index_in_flight(asset_id):
        return {"indexed": False, "skipped": "in-flight"}

    # Invariant: vector-write must belong to a KB (rag_guard).
    from rag.rag_guard import require_kb_binding
    kb_id = require_kb_binding(asset)

    # Per-KB binding: vectors in one KB share a single embedding space.
    kb = await get_kb(kb_id, user_id)
    kb_embed_model: str | None = getattr(kb, "embed_model", None) if kb else None
    kb_parser_config: dict[str, Any] | None = (getattr(kb, "parser_config", None) or None) if kb else None
    contextual_enabled: bool = bool(kb_parser_config and kb_parser_config.get("contextual_retrieval"))

    from rag.rag_guard import ALLOWED_INDEX_SOURCES, scan_document
    from rag.rag_parsing import extract_metadata, extract_text

    try:
        # OWASP LLM08 source whitelist: only known ingestion channels may index.
        if asset.source not in ALLOWED_INDEX_SOURCES:
            raise ValueError(
                f"asset source {asset.source!r} not allowed for indexing"
            )

        # In-flight marker BEFORE the slow parse: closes the guard window so a
        # concurrent trigger sees this task instead of double-indexing.
        await set_index_progress(asset_id, "parsing", 10, "Extracting text...")

        text = extract_text(asset.storage_path)
        if not text.strip():
            raise ValueError("asset has no text content — cannot index")

        # Document-level metadata extraction (author, date, title) — stored
        # in chunk metadata for richer citation and filtering.
        doc_metadata = extract_metadata(asset.storage_path)

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

        # Contextual Retrieval: prepend document-level context prefix to each
        # chunk before embedding.  Improves retrieval accuracy by ~67%
        # (Anthropic research) — the vector captures document-level semantics
        # alongside chunk content.  Original text is preserved in metadata for
        # display and LLM context injection.
        if contextual_enabled and chunks:
            from rag.rag_contextual import apply_context_prefixes, generate_context_prefixes

            await set_index_progress(asset_id, "chunking", 40, "Generating context prefixes...")
            chunk_texts = [c.text for c in chunks]
            # Reuse the embedding provider's API key + base_url — same
            # SiliconFlow/OpenAI-compatible endpoint serves both embeddings
            # and chat completions.
            prefixes = await generate_context_prefixes(
                document_text=text,
                chunk_texts=chunk_texts,
                api_key=cfg["api_key"],
                model=cfg["model"],
                base_url=cfg["base_url"],
            )
            apply_context_prefixes(chunks, prefixes)

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
            # Merge with existing metadata (apply_context_prefixes may have
            # written original_text / context_prefix).
            chunk.metadata = {
                **(chunk.metadata or {}),
                "asset_id": asset.id,
                "asset_name": asset.name,
                "embed_model": provider.model,
                **{k: v for k, v in doc_metadata.items() if v},
            }

        # Race guard against a concurrent rebind: the KB binding may have
        # changed during the slow embed step, so these vectors could belong
        # to the old space. Comparing against the START-of-task snapshot
        # would never see the change — re-read the LIVE binding instead.
        # Abort (fail-loud): the failed terminal state makes the sweep retry
        # with the new model, so the asset always converges to one space.
        if kb_id is not None and kb_embed_model is not None:
            kb_now = await get_kb(kb_id, user_id)
            live_model = getattr(kb_now, "embed_model", None) if kb_now else None
            if live_model is not None and live_model != provider.model:
                raise RuntimeError(
                    f"KB embed model changed to {live_model!r} mid-indexing; "
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
