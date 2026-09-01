"""Basic tests for backend/rag_chunking.py — Chunk model, chunking, metadata."""




class TestChunkModel:
    def test_import(self):
        from rag.rag_chunking import Chunk
        assert Chunk is not None

    def test_chunk_basic_fields(self):
        from rag.rag_chunking import Chunk

        chunk = Chunk(id="abc123", text="Hello world", session_id="sess-1", run_id="run-1")
        assert chunk.id == "abc123"
        assert chunk.text == "Hello world"
        assert chunk.session_id == "sess-1"
        assert chunk.run_id == "run-1"
        assert chunk.tags == []
        assert chunk.embedding is None
        assert chunk.metadata == {}

    def test_chunk_defaults(self):
        from rag.rag_chunking import Chunk

        chunk = Chunk(id="x", text="test", session_id="s1", run_id=None)
        assert chunk.run_id is None
        assert chunk.tags == []
        assert chunk.embedding is None
        assert chunk.metadata == {}

    def test_chunk_with_tags_and_metadata(self):
        from rag.rag_chunking import Chunk

        chunk = Chunk(
            id="abc",
            text="code",
            session_id="s1",
            run_id="r1",
            tags=["python", "bug"],
            metadata={"source": "test", "line": 42},
        )
        assert chunk.tags == ["python", "bug"]
        assert chunk.metadata == {"source": "test", "line": 42}

    def test_chunk_with_embedding(self):
        from rag.rag_chunking import Chunk

        chunk = Chunk(id="e1", text="text", session_id="s1", run_id="r1", embedding=[0.1, 0.2, 0.3])
        assert chunk.embedding == [0.1, 0.2, 0.3]


class TestSemanticChunk:
    def test_semantic_chunk_import(self):
        from rag.rag_chunking import semantic_chunk
        assert semantic_chunk is not None

    def test_semantic_chunk_empty_text(self):
        from rag.rag_chunking import semantic_chunk

        result = semantic_chunk("", "sess-1")
        assert result == []

    def test_semantic_chunk_whitespace_only(self):
        from rag.rag_chunking import semantic_chunk

        result = semantic_chunk("   \n  \t  ", "sess-1")
        assert result == []

    def test_semantic_chunk_single_short_section(self):
        from rag.rag_chunking import semantic_chunk

        text = "Hello world"
        result = semantic_chunk(text, "sess-1", "run-1")
        assert len(result) == 1
        assert result[0].text == "Hello world"
        assert result[0].session_id == "sess-1"
        assert result[0].run_id == "run-1"

    def test_semantic_chunk_hashes_consistently(self):
        from rag.rag_chunking import semantic_chunk

        text = "Consistent text"
        result1 = semantic_chunk(text, "s1")
        result2 = semantic_chunk(text, "s1")
        assert result1[0].id == result2[0].id

    def test_semantic_chunk_id_ignores_session(self):
        from rag.rag_chunking import semantic_chunk

        text = "Same text"
        r1 = semantic_chunk(text, "sess-a")
        r2 = semantic_chunk(text, "sess-b")
        assert r1[0].id == r2[0].id  # id is hash of text only, session 不参与

    def test_semantic_chunk_with_headings(self):
        from rag.rag_chunking import semantic_chunk

        text = "# Introduction\n\nHello\n\n## Details\n\nMore content"
        result = semantic_chunk(text, "sess-1")
        assert len(result) >= 2

    def test_semantic_chunk_large_section_split(self):
        from rag.rag_chunking import semantic_chunk

        words = ["word"] * 300
        text = " ".join(words)
        result = semantic_chunk(text, "sess-1", chunk_size=100, overlap=0)
        assert len(result) > 1
        assert all(c.session_id == "sess-1" for c in result)

    def test_semantic_chunk_tail_window_no_infinite_loop(self):
        """Regression: when the final window touched len(words), the old
        start = end - overlap arithmetic pinned start and looped forever."""
        from rag.rag_chunking import semantic_chunk

        words = ["word"] * 150  # tail window lands exactly on len(words)
        text = " ".join(words)
        result = semantic_chunk(text, "sess-1", chunk_size=100, overlap=64)
        assert len(result) >= 3
        assert result[-1].text.split()[-1] == "word"  # tail preserved

    def test_hierarchical_chunk_carries_parent_text(self):
        from rag.rag_chunking import hierarchical_chunk

        words = ["word"] * 300
        text = "# 章一\n\n" + " ".join(words)
        result = hierarchical_chunk(text, "sess-1", child_size=100, child_overlap=20)
        assert len(result) > 1
        for c in result:
            # Parent text is the normalized full section; child is a sub-window.
            assert c.metadata["parent_text"] == "# 章一 " + " ".join(words)
            assert c.text in c.metadata["parent_text"]
            assert c.metadata["parent_id"]

    def test_hierarchical_chunk_short_section_single_child(self):
        from rag.rag_chunking import hierarchical_chunk

        text = "## 短节\n\n短内容"
        result = hierarchical_chunk(text, "sess-1")
        assert len(result) == 1
        assert result[0].metadata["parent_text"] == "## 短节 短内容"

    def test_hierarchical_chunk_empty(self):
        from rag.rag_chunking import hierarchical_chunk

        assert hierarchical_chunk("", "s1") == []
        assert hierarchical_chunk("   \n  ", "s1") == []

    def test_semantic_chunk_tags_from_headings(self):
        from rag.rag_chunking import semantic_chunk

        text = "## Bug Fix\n\nFixed the issue"
        result = semantic_chunk(text, "sess-1")
        assert len(result) == 1
        assert any("bug" in tag for tag in result[0].tags) or any("bug fix" in tag for tag in result[0].tags)


class TestExtractTags:
    def test_extract_tags_import(self):
        from rag.rag_chunking import _extract_tags
        assert _extract_tags is not None

    def test_extract_tags_from_heading(self):
        from rag.rag_chunking import _extract_tags

        tags = _extract_tags("## Feature\nContent")
        assert any("feature" in t for t in tags)

    def test_extract_tags_from_code_fence(self):
        from rag.rag_chunking import _extract_tags

        tags = _extract_tags("Some ```python code")
        assert "python" in tags

    def test_extract_tags_bug(self):
        from rag.rag_chunking import _extract_tags

        tags = _extract_tags("Found a Bug in the code")
        assert "bug" in tags

    def test_extract_tags_dedup(self):
        from rag.rag_chunking import _extract_tags

        tags = _extract_tags("## Bug\n\nBug present multiple times")
        assert len([t for t in tags if t == "bug"]) <= 1

    def test_extract_tags_empty(self):
        from rag.rag_chunking import _extract_tags

        tags = _extract_tags("No tags here")
        assert tags == []

    def test_extract_tags_truncated(self):
        from rag.rag_chunking import _extract_tags

        long_word = "a" * 50
        tags = _extract_tags(f"## {long_word}")
        assert all(len(t) <= 32 for t in tags)


class TestHashId:
    def test_hash_id_import(self):
        from rag.rag_chunking import _hash_id
        assert _hash_id is not None

    def test_hash_id_length(self):
        from rag.rag_chunking import _hash_id

        h = _hash_id("test text")
        assert len(h) == 16

    def test_hash_id_consistency(self):
        from rag.rag_chunking import _hash_id

        assert _hash_id("hello") == _hash_id("hello")

    def test_hash_id_different_inputs(self):
        from rag.rag_chunking import _hash_id

        assert _hash_id("abc") != _hash_id("xyz")
