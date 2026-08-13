"""Tests for rag.rag_pii — PII scan/redact (OWASP LLM02 / S5)."""

from rag.rag_pii import PII_TYPES, redact_pii, scan_pii


class TestScanPii:
    def test_detects_email(self):
        hits = scan_pii("联系 alice@example.com 获取更多")
        assert {"type": "email", "match": "alice@example.com"} in hits

    def test_detects_cn_phone(self):
        hits = scan_pii("电话 13800138000 或 400 电话")
        assert {"type": "cn_phone", "match": "13800138000"} in hits

    def test_detects_cn_id(self):
        hits = scan_pii("身份证 11010119900307001X 已登记")
        assert {"type": "cn_id", "match": "11010119900307001X"} in hits

    def test_detects_api_key(self):
        hits = scan_pii("key: sk-abcdef1234567890abcdef12")
        assert any(h["type"] == "api_key" for h in hits)

    def test_plain_opaque_text_not_flagged(self):
        """Documents full of chunk ids / hashes must not be flagged."""
        text = "chunk 9f2c7a31e4d5b608a1c3e9f7d2b4a6c8e0f1a2b3c4d5e6f7 相似度 0.98"
        assert scan_pii(text) == []

    def test_dedupes_repeated_occurrences(self):
        hits = scan_pii("a@b.com 与 a@b.com 都写")
        assert sum(1 for h in hits if h["type"] == "email") == 1


class TestRedactPii:
    def test_redacts_each_type(self):
        out = redact_pii("邮箱 a@b.com 电话 13800138000")
        assert "a@b.com" not in out
        assert "13800138000" not in out
        assert "[已脱敏:email]" in out
        assert "[已脱敏:cn_phone]" in out

    def test_redact_plain_text_unchanged(self):
        text = "知识库片段 无敏感信息"
        assert redact_pii(text) == text


def test_pii_types_constant():
    assert PII_TYPES == ("email", "cn_phone", "cn_id", "api_key")
