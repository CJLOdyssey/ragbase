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
    if not text or not text.strip():
        return []

    sections = re.split(r"(?=^#{1,3}\s)", text, flags=re.MULTILINE)
    chunks: list[Chunk] = []

    for section in sections:
        section = section.strip()
        if not section:
            continue
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
            start = 0
            while start < len(words):
                end = min(start + chunk_size, len(words))
                chunk_text = " ".join(words[start:end])
                chunks.append(
                    Chunk(
                        id=_hash_id(chunk_text + str(start)),
                        text=chunk_text,
                        session_id=session_id,
                        run_id=run_id,
                        tags=tags,
                    )
                )
                start = end - overlap

    return chunks


TAG_PATTERNS = [
    (r"##\s*(.+)", 1),
    (r"###\s*(.+)", 2),
    (r"```(\w+)", 3),
    (r"(Bug|Fix|Bugfix|修复|缺陷|BUG)", 4),
    (r"(PRD|Feature|需求|功能|设计)", 4),
    (r"(API|接口|端点|endpoint)", 4),
    (r"(Test|测试|test)", 4),
    (r"(Deploy|部署|CI/CD)", 4),
]


def _extract_tags(text: str) -> list[str]:
    tags = []
    for pattern, _ in TAG_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for m in matches:
            tag = m.strip().lower()[:32]
            if tag and tag not in tags:
                tags.append(tag)
    return tags


def _hash_id(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]
