"""Tests for backend/rag/__init__.py and backend/rag/engine.py exports."""


class TestRagInit:
    def test_imports_chunk(self):
        from rag import Chunk
        assert Chunk is not None

    def test_imports_semantic_chunk(self):
        from rag import semantic_chunk
        assert callable(semantic_chunk)

    def test_imports_embedding_provider(self):
        from rag import EmbeddingProvider
        assert EmbeddingProvider is not None

    def test_imports_ensure_embedding_provider(self):
        from rag import ensure_embedding_provider
        assert callable(ensure_embedding_provider)

    def test_imports_get_rag_pipeline(self):
        from rag import get_rag_pipeline
        assert callable(get_rag_pipeline)

    def test_imports_ingest_session_messages(self):
        from rag import ingest_session_messages
        assert callable(ingest_session_messages)

    def test_imports_retrieve_context(self):
        from rag import retrieve_context
        assert callable(retrieve_context)

    def test_imports_pgvector_store(self):
        from rag import PgVectorStore
        assert PgVectorStore is not None

    def test_engine_module_exists(self):
        import rag.engine as engine_mod
        assert engine_mod is not None

    def test_init_module_exists(self):
        import rag as rag_mod
        assert rag_mod is not None
