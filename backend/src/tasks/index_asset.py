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
    from repository.assets import get_asset, set_asset_indexed
    from repository.keys import get_embedding_config

    asset = await get_asset(asset_id)
    if asset is None or asset.user_id != user_id:
        raise ValueError(f"asset {asset_id} not found or not owned by user")

    from rag.rag_parsing import extract_text

    text = extract_text(asset.storage_path)
    if not text.strip():
        raise ValueError("asset has no text content — cannot index")

    cfg = await get_embedding_config()
    if cfg is None or cfg["api_key"] is None:
        raise RuntimeError("no embedding API key configured")

    chunks = semantic_chunk(text, session_id=f"asset:{asset.id}", run_id=None)
    for chunk in chunks:
        chunk.metadata = {"asset_id": asset.id, "asset_name": asset.name}

    provider = EmbeddingProvider(
        api_key=cfg["api_key"],
        model=cfg["model"] or "text-embedding-v3",
        base_url=cfg["base_url"],
    )
    embeddings = await provider.embed([c.text for c in chunks])
    for chunk, emb in zip(chunks, embeddings, strict=False):
        chunk.embedding = emb

    store = PgVectorStore()
    await store.clear_asset(asset.id)  # idempotent reindex: no stale chunks
    await store.add(chunks, user_id=user_id)
    await set_asset_indexed(asset.id, True)
    return {"indexed": True, "chunks": len(chunks)}
