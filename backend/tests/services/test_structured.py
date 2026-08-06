"""Structured generation result parsing tests."""

import pytest
from services.structured import CONTENT_TYPES, GENERATION_MODES, parse_generation_result

pytestmark = pytest.mark.unit


@pytest.mark.unit
def test_content_type_constants_match_spec() -> None:
    assert set(CONTENT_TYPES) == {
        "xiaohongshu", "wechat_article", "short_video_script", "marketing_copy", "generic",
    }
    assert set(GENERATION_MODES) == {"generate", "rewrite", "title_suggest", "variations"}


@pytest.mark.unit
def test_parse_valid_json_block() -> None:
    text = '```json\n{"title": "T", "summary": "S", "body_markdown": "B", "keywords": ["a"]}\n```'
    result = parse_generation_result(text)
    assert result.title == "T"
    assert result.summary == "S"
    assert result.body_markdown == "B"
    assert result.keywords == ["a"]


@pytest.mark.unit
def test_parse_raw_json_without_fence() -> None:
    text = '{"title": "T", "summary": "S", "body_markdown": "B"}'
    result = parse_generation_result(text)
    assert result.title == "T"
    assert result.body_markdown == "B"


@pytest.mark.unit
def test_parse_fallback_when_not_json() -> None:
    result = parse_generation_result("纯文本内容，没有 JSON")
    assert result.body_markdown == "纯文本内容，没有 JSON"
    assert result.summary == "纯文本内容，没有 JSON"[:200]
    assert result.title == ""


@pytest.mark.unit
def test_parse_skips_invalid_blocks_then_falls_back() -> None:
    text = "```json\n[1, 2]\n```\n```json\n{\"keywords\": 42}\n```\n```\nnot json\n```"
    result = parse_generation_result(text)
    assert result.title == ""
    assert result.body_markdown == text
