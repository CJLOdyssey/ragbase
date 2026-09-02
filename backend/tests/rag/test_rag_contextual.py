"""Tests for contextual retrieval (rag/rag_contextual.py)."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from rag.rag_contextual import (
    _CONTEXT_MAX_WORDS,
    apply_context_prefixes,
    build_context_prefix_prompt,
    generate_context_prefixes,
    parse_context_response,
)


# ── build_context_prefix_prompt ──────────────────────────────────────


class TestBuildContextPrefixPrompt:
    def test_short_document(self):
        doc = "Short doc."
        prompt = build_context_prefix_prompt(doc, ["chunk1"])
        assert "Short doc." in prompt
        assert "[0] chunk1" in prompt
        assert "[truncated]" not in prompt

    def test_long_document_truncated(self):
        doc = "x" * 3000
        prompt = build_context_prefix_prompt(doc, ["c1"])
        assert "[truncated]..." in prompt
        assert len(prompt) < 5000

    def test_long_chunk_truncated(self):
        chunk = "y" * 300
        prompt = build_context_prefix_prompt("doc", [chunk])
        # [0] yyy...yyy... — 200 chars + "..."
        assert "..." in prompt

    def test_short_chunk_no_truncation(self):
        prompt = build_context_prefix_prompt("doc", ["short chunk"])
        assert "[0] short chunk" in prompt

    def test_multiple_chunks(self):
        prompt = build_context_prefix_prompt("doc", ["a", "b", "c"])
        assert "[0] a" in prompt
        assert "[1] b" in prompt
        assert "[2] c" in prompt

    def test_max_words_in_prompt(self):
        prompt = build_context_prefix_prompt("doc", ["c"])
        assert f"Max {_CONTEXT_MAX_WORDS} words" in prompt


# ── parse_context_response ───────────────────────────────────────────


class TestParseContextResponse:
    def test_valid_json_array(self):
        resp = json.dumps(["ctx1", "ctx2"])
        result = parse_context_response(resp, 2)
        assert result == ["ctx1", "ctx2"]

    def test_json_with_code_fences(self):
        resp = '```json\n["ctx1", "ctx2"]\n```'
        result = parse_context_response(resp, 2)
        assert result == ["ctx1", "ctx2"]

    def test_json_code_fence_no_trailing(self):
        resp = '```\n["ctx1"]\n```'
        result = parse_context_response(resp, 1)
        assert result == ["ctx1"]

    def test_json_fewer_pads_empty(self):
        resp = json.dumps(["only one"])
        result = parse_context_response(resp, 3)
        assert result == ["only one", "", ""]

    def test_json_truncates_long_prefix(self):
        long_prefix = " ".join(["word"] * 100)
        resp = json.dumps([long_prefix])
        result = parse_context_response(resp, 1)
        assert len(result[0].split()) == _CONTEXT_MAX_WORDS

    def test_json_extra_items_truncated(self):
        resp = json.dumps(["a", "b", "c", "d"])
        result = parse_context_response(resp, 2)
        assert len(result) == 2

    def test_fallback_to_lines(self):
        resp = "not json at all"
        result = parse_context_response(resp, 1)
        assert result == ["not json at all"]

    def test_fallback_strips_quotes(self):
        resp = '"quoted"\n\'single\''
        result = parse_context_response(resp, 2)
        assert result == ["quoted", "single"]

    def test_fallback_long_line_truncated(self):
        long_line = " ".join(["w"] * 100)
        result = parse_context_response(long_line, 1)
        assert len(result[0].split()) == _CONTEXT_MAX_WORDS

    def test_fallback_fewer_pads_empty(self):
        result = parse_context_response("only one line", 3)
        assert result == ["only one line", "", ""]

    def test_fallback_empty_lines_skipped(self):
        resp = "\n\nline1\n\n\nline2\n\n"
        result = parse_context_response(resp, 2)
        assert result == ["line1", "line2"]

    def test_empty_response_pads(self):
        result = parse_context_response("", 2)
        assert result == ["", ""]

    def test_json_not_list_falls_back(self):
        resp = '{"key": "value"}'
        result = parse_context_response(resp, 1)
        # JSON parses but is not a list → falls to line fallback
        assert len(result) == 1


# ── generate_context_prefixes ────────────────────────────────────────


class TestGenerateContextPrefixes:
    @pytest.mark.asyncio
    async def test_empty_chunks(self):
        result = await generate_context_prefixes("doc", [], "key")
        assert result == []

    @pytest.mark.asyncio
    async def test_no_api_key(self):
        result = await generate_context_prefixes("doc", ["c1"], "")
        assert result == [""]

    @pytest.mark.asyncio
    async def test_llm_success(self):
        mock_resp = json.dumps(["This is about X. Context for chunk."])
        mock_body = json.dumps({
            "choices": [{"message": {"content": mock_resp}}]
        }).encode()

        mock_read = MagicMock()
        mock_read.read.return_value = mock_body
        mock_read.__enter__ = lambda s: s
        mock_read.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_read):
            result = await generate_context_prefixes(
                "doc", ["chunk text"], "test-key",
                model="test-model", base_url="https://api.test.com/v1",
            )

        assert len(result) == 1
        assert "This is about X" in result[0]

    @pytest.mark.asyncio
    async def test_llm_failure_graceful(self):
        with patch("urllib.request.urlopen", side_effect=Exception("network error")):
            result = await generate_context_prefixes(
                "doc", ["c1", "c2"], "key",
            )

        assert result == ["", ""]

    @pytest.mark.asyncio
    async def test_default_model_and_base_url(self):
        mock_resp = json.dumps(["ctx"])
        mock_body = json.dumps({
            "choices": [{"message": {"content": mock_resp}}]
        }).encode()

        mock_read = MagicMock()
        mock_read.read.return_value = mock_body
        mock_read.__enter__ = lambda s: s
        mock_read.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_read) as mock_urlopen:
            await generate_context_prefixes("doc", ["c"], "key")

        # Verify default URL was used
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://api.siliconflow.cn/v1/chat/completions"

    @pytest.mark.asyncio
    async def test_custom_base_url(self):
        mock_resp = json.dumps(["ctx"])
        mock_body = json.dumps({
            "choices": [{"message": {"content": mock_resp}}]
        }).encode()

        mock_read = MagicMock()
        mock_read.read.return_value = mock_body
        mock_read.__enter__ = lambda s: s
        mock_read.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_read) as mock_urlopen:
            await generate_context_prefixes(
                "doc", ["c"], "key", base_url="https://custom.api/v1",
            )

        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://custom.api/v1/chat/completions"

    @pytest.mark.asyncio
    async def test_auth_header(self):
        mock_resp = json.dumps(["ctx"])
        mock_body = json.dumps({
            "choices": [{"message": {"content": mock_resp}}]
        }).encode()

        mock_read = MagicMock()
        mock_read.read.return_value = mock_body
        mock_read.__enter__ = lambda s: s
        mock_read.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_read) as mock_urlopen:
            await generate_context_prefixes("doc", ["c"], "my-secret-key")

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Authorization") == "Bearer my-secret-key"

    @pytest.mark.asyncio
    async def test_content_type_header(self):
        mock_resp = json.dumps(["ctx"])
        mock_body = json.dumps({
            "choices": [{"message": {"content": mock_resp}}]
        }).encode()

        mock_read = MagicMock()
        mock_read.read.return_value = mock_body
        mock_read.__enter__ = lambda s: s
        mock_read.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_read) as mock_urlopen:
            await generate_context_prefixes("doc", ["c"], "key")

        req = mock_urlopen.call_args[0][0]
        assert req.get_header("Content-type") == "application/json"


# ── apply_context_prefixes ───────────────────────────────────────────


class TestApplyContextPrefixes:
    def test_basic(self):
        chunks = [SimpleNamespace(text="hello", metadata={})]
        apply_context_prefixes(chunks, ["ctx: "])
        assert chunks[0].text == "ctx: \n\nhello"
        assert chunks[0].metadata["original_text"] == "hello"
        assert chunks[0].metadata["context_prefix"] == "ctx: "

    def test_empty_prefix_skipped(self):
        chunks = [SimpleNamespace(text="hello", metadata={})]
        apply_context_prefixes(chunks, [""])
        assert chunks[0].text == "hello"
        assert "original_text" not in chunks[0].metadata

    def test_multiple_chunks(self):
        chunks = [
            SimpleNamespace(text="a", metadata={}),
            SimpleNamespace(text="b", metadata={}),
        ]
        apply_context_prefixes(chunks, ["ctx1", ""])
        assert chunks[0].text == "ctx1\n\na"
        assert chunks[1].text == "b"
        assert "original_text" in chunks[0].metadata
        assert "original_text" not in chunks[1].metadata
