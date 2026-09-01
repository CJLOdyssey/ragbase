"""RAG pipeline: analysis → chunking → embedding → vector store → retrieval.

Pipeline stages:
  1.  Analyze & preprocess session content
  2.  Semantic chunking
  3.  Text vectorization (DashScope text-embedding-v3)
  4.  Store in pgvector
  5.  On new input: vectorize query
  6.  Hybrid retrieval (tag match + cosine similarity via pgvector)
  7.  Inject results into LLM context

Production stack:
  - Embedding: Alibaba DashScope (text-embedding-v3)
  - Vector DB: PostgreSQL + pgvector extension
"""

from typing import Any

from core.infra.logging_config import get_logger

from rag.rag_chunking import semantic_chunk
from rag.rag_embedding import EMBEDDING_MODEL, EmbeddingProvider
from rag.rag_store import PgVectorStore

logger = get_logger(__name__)

# ── Global state ─────────────────────────────────────────────────────────────

_embedding_provider: EmbeddingProvider | None = None
_vector_store = PgVectorStore()


def get_rag_pipeline() -> tuple[EmbeddingProvider | None, PgVectorStore]:
    """Return the process-global (embedding provider, vector store)."""
    return _embedding_provider, _vector_store


def ensure_embedding_provider(
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> None:
    """Set the global embedding provider from an API key; None disables embedding."""
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
    """Ingest conversation messages into the pgvector store.

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


RERANK_CANDIDATES = 20  # overfetch before cross-encoder rerank narrows to top_k

# Vector-leg similarity floor: hits below this never enter context. Guards
# against junk chunks poisoning the LLM prompt when the corpus has no real
# match (Azure guidance: minimum thresholds to exclude low-scoring results).
DEFAULT_MIN_SCORE = 0.45


async def retrieve_context(
    query: str,
    user_id: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    asset_ids: list[str] | None = None,
    top_k: int = 5,
    rerank: bool = False,
    min_score: float | None = DEFAULT_MIN_SCORE,
) -> str:
    """Retrieve relevant context for a user query.

    1. Embed query
    2. Hybrid search (HNSW ‖ pg_trgm + RRF), filtered to user_id
    3. Optional cross-encoder rerank of candidates down to top_k
    4. Return formatted context with asset trace for LLM
    """
    results = await _search_results(
        query=query,
        user_id=user_id,
        session_id=session_id,
        tags=tags,
        asset_ids=asset_ids,
        top_k=top_k,
        rerank=rerank,
        min_score=min_score,
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


async def retrieve_sources(
    query: str,
    user_id: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    asset_ids: list[str] | None = None,
    top_k: int = 5,
    rerank: bool = False,
    min_score: float | None = DEFAULT_MIN_SCORE,
    retrieval_method: str = "hybrid",
) -> list[dict[str, Any]]:
    """Structured retrieval for citation UI — same pipeline as retrieve_context.

    Returns chunk-level sources ordered by RRF score: {asset_id, asset_name,
    text, similarity}. The LLM context stays plain text; this is the
    auditability counterpart (NVIDIA: "log the response alongside its
    references").
    """
    results = await _search_results(
        query=query,
        user_id=user_id,
        session_id=session_id,
        tags=tags,
        asset_ids=asset_ids,
        top_k=top_k,
        rerank=rerank,
        min_score=min_score,
        retrieval_method=retrieval_method,
    )
    return [
        {
            "asset_id": r.get("asset_id"),
            "asset_name": (r.get("metadata") or {}).get("asset_name"),
            "text": r["text"],
            "similarity": r["similarity"],
        }
        for r in results
    ]


async def _search_results(
    query: str,
    user_id: str,
    session_id: str | None = None,
    tags: list[str] | None = None,
    asset_ids: list[str] | None = None,
    top_k: int = 5,
    rerank: bool = False,
    min_score: float | None = DEFAULT_MIN_SCORE,
    retrieval_method: str = "hybrid",
) -> list[dict[str, Any]]:
    """Shared retrieval core: embed → hybrid search → optional rerank.

    Mixed-model corpora: the query is embedded once per distinct embedding
    cohort (the ``embed_model`` marker recorded at index time), so vectors
    are only ever compared inside their own space. Group results merge by
    RRF score — an ordering heuristic across models; enabling rerank lets
    the cross-encoder restore a common scale.
    """
    store = _vector_store
    groups = await store.embed_model_groups(
        user_id, session_id=session_id, tag_filter=tags, asset_ids=asset_ids
    )
    if not groups:
        return []

    candidate_k = RERANK_CANDIDATES if rerank else top_k

    if len(groups) == 1:
        if _embedding_provider is None and retrieval_method != "lexical":
            return []
        query_embedding: list[float] = (
            [] if retrieval_method == "lexical" or _embedding_provider is None
            else await _embedding_provider.embed_query(query)
        )
        results: list[dict[str, Any]] = await store.search(
            query_embedding,
            query_text=query,
            user_id=user_id,
            session_id=session_id,
            tag_filter=tags,
            asset_ids=asset_ids,
            top_k=candidate_k,
            min_score=min_score,
            method=retrieval_method,
        )
    else:
        # Lazy: repository.keys sits at the tail of the rag import chain.
        from repository.keys import get_embedding_config

        merged: list[dict[str, Any]] = []
        for model in groups:
            # Lexical-only retrieval needs no embeddings — mirror the
            # single-cohort path where a missing provider short-circuits.
            cohort_embedding: list[float]
            if retrieval_method == "lexical":
                cohort_embedding = []
            else:
                cfg = await get_embedding_config(preferred_model=model)
                if cfg is None or cfg["api_key"] is None:
                    logger.warning(
                        "no embedding config for cohort %r — skipped", model
                    )
                    continue
                provider = EmbeddingProvider(
                    api_key=cfg["api_key"],
                    model=cfg["model"] or EMBEDDING_MODEL,
                    base_url=cfg["base_url"],
                )
                try:
                    cohort_embedding = await provider.embed_query(query)
                except Exception:
                    logger.exception(
                        "query embedding failed for %r — group skipped", model
                    )
                    continue
            merged.extend(
                await store.search(
                    cohort_embedding,
                    query_text=query,
                    user_id=user_id,
                    session_id=session_id,
                    tag_filter=tags,
                    asset_ids=asset_ids,
                    top_k=candidate_k,
                    min_score=min_score,
                    embed_model=model,
                    embed_model_filter=True,
                    method=retrieval_method,
                )
            )
        results = sorted(merged, key=lambda r: r["score"], reverse=True)[:candidate_k]

    if results and rerank and len(results) > top_k:
        results = await _rerank_results(query, results, top_k)
    return results


async def _rerank_results(
    query: str, results: list[dict[str, Any]], top_k: int
) -> list[dict[str, Any]]:
    """Reorder results with the configured cross-encoder; no-op if unavailable."""
    from repository.keys import get_rerank_config

    from rag.rag_rerank import RerankProvider

    cfg = await get_rerank_config()
    if cfg is None or cfg["api_key"] is None:
        return results
    provider = RerankProvider(
        api_key=cfg["api_key"], base_url=cfg["base_url"], model=cfg["model"]
    )
    indices = await provider.rerank(query, [r["text"] for r in results], top_n=top_k)
    # Drop out-of-range indices defensively — a provider bug must not crash
    # retrieval, only narrow the ranked list.
    return [results[idx] for idx in indices if 0 <= idx < len(results)]


def _asset_label(metadata: dict[str, Any]) -> str:
    """Format source trace: [素材: 名称] when the chunk came from an asset."""
    name = (metadata or {}).get("asset_name")
    return f" [素材: {name}]" if name else ""
