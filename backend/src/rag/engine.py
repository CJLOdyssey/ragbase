"""RAG pipeline: chunking, embedding, vector store, and retrieval."""

from rag.rag_chunking import Chunk, semantic_chunk  # noqa: F401
from rag.rag_embedding import EmbeddingProvider  # noqa: F401
from rag.rag_pipeline import (  # noqa: F401
    ensure_embedding_provider,
    get_rag_pipeline,
    ingest_session_messages,
    retrieve_context,
)
from rag.rag_store import PgVectorStore  # noqa: F401
