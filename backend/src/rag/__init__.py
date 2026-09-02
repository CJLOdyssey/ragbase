"""RAG engine — chunking, embedding, vector store, and retrieval pipeline.

Curated re-exports of the engine's public API. Consumers may import from
here or directly from the defining module (e.g. ``from rag import
retrieve_context`` or ``from rag.rag_pipeline import retrieve_context``).
"""

from rag.rag_chunking import Chunk, hierarchical_chunk, semantic_chunk
from rag.rag_embedding import EMBEDDING_MODEL, EmbeddingProvider
from rag.rag_pipeline import (
    ensure_embedding_provider,
    get_rag_pipeline,
    ingest_session_messages,
    retrieve_context,
    retrieve_sources,
)
from rag.rag_store import PgVectorStore

__all__ = [
    "Chunk",
    "EMBEDDING_MODEL",
    "EmbeddingProvider",
    "PgVectorStore",
    "ensure_embedding_provider",
    "get_rag_pipeline",
    "hierarchical_chunk",
    "ingest_session_messages",
    "retrieve_context",
    "retrieve_sources",
    "semantic_chunk",
]
