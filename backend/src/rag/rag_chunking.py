"""Semantic chunking for RAG pipeline."""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Chunk:
    id: str
    text: str
    session_id: str
    run_id: str | None
    tags: list[str] = field(default_factory=list)
    embedding: list[float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def semantic_chunk(
    text: str,
    session_id: str,
    run_id: str | None = None,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[Chunk]:
    """Split text into overlapping word windows, one Chunk per markdown section.

    ``chunk_size`` counts *words* (not characters); adjacent windows overlap
    by ``overlap`` words so sentence boundaries across a cut stay retrievable.
    Heading blocks (``#``/``##``/``###``) become section boundaries — each
    section is chunked independently and inherits the section's tags.
    Chunk ids are content hashes, so re-chunking identical text is idempotent.
    """
    if not text or not text.strip():
        return []

    chunks: list[Chunk] = []
    for section in _split_sections(text):
        tags = _extract_tags(section)

        if len(section) <= chunk_size:
            chunks.append(
                Chunk(
                    id=_hash_id(section),
                    text=section,
                    session_id=session_id,
                    run_id=run_id,
                    tags=tags,
                )
            )
        else:
            words = section.split()
            for chunk_text, start in _word_windows(words, chunk_size, overlap):
                chunks.append(
                    Chunk(
                        id=_hash_id(chunk_text + str(start)),
                        text=chunk_text,
                        session_id=session_id,
                        run_id=run_id,
                        tags=tags,
                    )
                )

    return chunks


def hierarchical_chunk(
    text: str,
    session_id: str,
    run_id: str | None = None,
    child_size: int = 256,
    child_overlap: int = 32,
) -> list[Chunk]:
    """Hierarchical chunking: child retrieval granularity, parent context in metadata.

    Each markdown section (heading split) is one parent; children are
    overlapping word windows of child_size. The full parent text rides in
    metadata["parent_text"] (with parent_id) so retrieval returns a child plus
    enough surrounding context for the LLM — child for precision, parent for
    completeness.
    """
    if not text or not text.strip():
        return []

    chunks: list[Chunk] = []
    for section in _split_sections(text):
        tags = _extract_tags(section)
        words = section.split()
        if not words:
            continue
        # Normalized parent: children are word windows of this exact string,
        # so every child is a substring of its parent (deterministic matching).
        parent_text = " ".join(words)
        parent_id = _hash_id(parent_text)

        if len(words) <= child_size:
            chunks.append(
                Chunk(
                    id=_hash_id(parent_text),
                    text=parent_text,
                    session_id=session_id,
                    run_id=run_id,
                    tags=tags,
                    metadata={"parent_id": parent_id, "parent_text": parent_text},
                )
            )
            continue

        for chunk_text, start in _word_windows(words, child_size, child_overlap):
            chunks.append(
                Chunk(
                    id=_hash_id(chunk_text + str(start)),
                    text=chunk_text,
                    session_id=session_id,
                    run_id=run_id,
                    tags=tags,
                    metadata={"parent_id": parent_id, "parent_text": parent_text},
                )
            )

    return chunks


TAG_PATTERNS: tuple[str, ...] = (
    r"##\s*(.+)",
    r"###\s*(.+)",
    r"```(\w+)",
    r"(Bug|Fix|Bugfix|修复|缺陷|BUG)",
    r"(PRD|Feature|需求|功能|设计)",
    r"(API|接口|端点|endpoint)",
    r"(Test|测试|test)",
    r"(Deploy|部署|CI/CD)",
)


def _split_sections(text: str) -> list[str]:
    """Split markdown into non-empty sections on heading boundaries.

    Heading blocks (``#``/``##``/``###``) start a new section; the rest of
    the text forms its own sections. Shared by semantic and hierarchical
    chunking so both honour the same boundary rules.
    """
    return [
        s.strip()
        for s in re.split(r"(?=^#{1,3}\s)", text, flags=re.MULTILINE)
        if s.strip()
    ]


def _word_windows(words: list[str], size: int, overlap: int) -> list[tuple[str, int]]:
    """Sliding word windows over a section, each with its start offset.

    The tail window is emitted before the loop exits, so a window landing
    exactly on ``len(words)`` never loops forever or drops the tail.
    Degenerate sizes are clamped rather than trusted: ``size <= 0`` yields
    no windows, and ``overlap >= size`` would pin ``start`` and hang — it is
    capped at ``size - 1``.
    """
    if size <= 0:
        return []
    overlap = max(0, min(overlap, size - 1))
    windows: list[tuple[str, int]] = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        windows.append((" ".join(words[start:end]), start))
        if end == len(words):
            break
        start = end - overlap
    return windows


def _extract_tags(text: str) -> list[str]:
    tags = []
    for pattern in TAG_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            tag = m.strip().lower()[:32]
            if tag and tag not in tags:
                tags.append(tag)
    return tags


def _hash_id(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
