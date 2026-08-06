"""Structured generation output — spec constants and tolerant parsing.

SPEC §1.3 命名规范: content_type / generation_mode 常量；§3.2 结构化结果
(正文 Markdown + 标题 + 摘要) 用 Pydantic 校验。流式收全文后在服务端解析，
不依赖各家 response_format 支持度（多源参照 2026-08-06）。
"""

import json
import re
from typing import Any

from pydantic import BaseModel, Field

CONTENT_TYPES: tuple[str, ...] = (
    "xiaohongshu",
    "wechat_article",
    "short_video_script",
    "marketing_copy",
    "generic",
)

GENERATION_MODES: tuple[str, ...] = (
    "generate",
    "rewrite",
    "title_suggest",
    "variations",
)

MAX_SUMMARY_LENGTH = 200


class GenerationResult(BaseModel):
    title: str = ""
    summary: str = ""
    body_markdown: str = ""
    keywords: list[str] = Field(default_factory=list)


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(.+?)```", re.DOTALL)


def parse_generation_result(text: str) -> GenerationResult:
    """Parse structured JSON out of LLM output; fall back to raw text."""
    candidates: list[str] = []
    for block in _JSON_BLOCK_RE.findall(text):
        candidates.append(block.strip())
    if not candidates:
        candidates.append(text.strip())

    for candidate in candidates:
        try:
            data: Any = json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        try:
            return GenerationResult(**data)
        except Exception:
            continue
    fallback = text.strip()
    return GenerationResult(
        title="",
        summary=fallback[:MAX_SUMMARY_LENGTH],
        body_markdown=fallback,
    )
