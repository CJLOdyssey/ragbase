from typing import Any

"""RAG pipeline: analysis → chunking → embedding → vector store → retrieval.

Steps 8-15 of the single-agent template:
  8.  Analyze & preprocess session content
  9.  Semantic chunking
  10. Text vectorization (DashScope text-embedding-v3, 1024d)
  11. Store in pgvector
  12. On new input: vectorize query
  13. Hybrid retrieval (tag match + cosine similarity via pgvector)
  14. Inject results into LLM context

Production stack:
  - Embedding: Alibaba DashScope (text-embedding-v3)
  - Vector DB: PostgreSQL + pgvector extension
"""

from core.infra.logging_config import get_logger

from rag.rag_chunking import semantic_chunk
from rag.rag_embedding import EMBEDDING_MODEL, EmbeddingProvider
from rag.rag_store import PgVectorStore

logger = get_logger(__name__)

# ── Global state ─────────────────────────────────────────────────────────────

_embedding_provider: EmbeddingProvider | None = None
_vector_store = PgVectorStore()


def get_rag_pipeline() -> tuple[EmbeddingProvider | None, PgVectorStore]:
    return _embedding_provider, _vector_store


def ensure_embedding_provider(
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> None:
    global _embedding_provider
    _embedding_provider = (
        EmbeddingProvider(
            api_key=api_key, model=model or EMBEDDING_MODEL, base_url=base_url
        )
        if api_key
        else None
    )


async def ingest_session_messages(
    session_id: str,
    run_id: str,
    messages: list[dict[str, Any]],
    user_id: str = "anonymous",
) -> None:
    """Steps 8-11: Ingest conversation messages into pgvector.

    1. Concatenate messages → text
    2. Chunk semantically
    3. Embed with DashScope
    4. Store in pgvector (tagged with the owning user)
    """
    text = "\n".join(m.get("content", "") for m in messages if m.get("content"))
    if not text.strip():
        return

    chunks = semantic_chunk(text, session_id=session_id, run_id=run_id)
    if not chunks:
        return

    if _embedding_provider is None:
        logger.warning("Embedding provider not configured — skipping RAG ingestion")
        return
    texts = [c.text for c in chunks]
    embeddings = await _embedding_provider.embed(texts)
    for chunk, emb in zip(chunks, embeddings, strict=False):
        chunk.embedding = emb

    await _vector_store.add(chunks, user_id=user_id)
    logger.info("RAG: ingested %d chunks for session %s", len(chunks), session_id)


async def retrieve_context(
    query: str,
    user_id: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    top_k: int = 5,
) -> str:
    """Steps 13-14: Retrieve relevant context for a user query.

    1. Embed query with DashScope
    2. Hybrid search (HNSW ‖ pg_trgm + RRF), filtered to user_id
    3. Return formatted context with asset trace for LLM
    """
    if _embedding_provider is None:
        return ""
    query_embedding = await _embedding_provider.embed_query(query)
    results = await _vector_store.search(
        query_embedding,
        query_text=query,
        user_id=user_id,
        session_id=session_id,
        tag_filter=tags,
        top_k=top_k,
    )

    if not results:
        return ""

    parts = []
    for r in results:
        tag_str = f" [{', '.join(r['tags'])}]" if r["tags"] else ""
        asset_str = _asset_label(r["metadata"]) or ""
        parts.append(
            f"--- [相似度: {r['similarity']:.2f}]{asset_str}{tag_str} ---\n{r['text']}"
        )

    return "\n\n".join(parts)


def _asset_label(metadata: dict[str, Any]) -> str:
    """Format source trace: [素材: 名称] when the chunk came from an asset."""
    name = (metadata or {}).get("asset_name")
    return f" [素材: {name}]" if name else ""
