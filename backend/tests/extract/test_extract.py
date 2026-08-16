"""Tests for the extract registry + extractors (backend/extract/)."""

import zipfile
from pathlib import Path

import pytest
from extract import extract_text, validate_magic, validate_upload
from extract.registry import ALLOWED_CONTENT_TYPES, FORMAT_REGISTRY, MAX_FILE_SIZE_MB
from fastapi import HTTPException
from pypdf import PdfWriter


def _make_docx(path: Path, paragraphs: list[str]) -> None:
    """Build a minimal DOCX (OOXML zip) with the given paragraph texts."""
    body = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{p}</w:t></w:r></w:p>' for p in paragraphs
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{body}</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", document)


class TestExtractText:
    def test_txt_reads_content(self, tmp_path):
        p = tmp_path / "doc.txt"
        p.write_text("纯文本内容", encoding="utf-8")
        assert "纯文本内容" in extract_text(p, "text/plain")

    def test_markdown_reads_content(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("# 标题\n内容", encoding="utf-8")
        assert "标题" in extract_text(p, "text/markdown")

    def test_text_truncated_at_limit(self, tmp_path):
        p = tmp_path / "big.txt"
        p.write_text("x" * 60000, encoding="utf-8")
        assert len(extract_text(p, "text/plain")) == 50000

    def test_pdf_invalid_returns_placeholder(self, tmp_path):
        p = tmp_path / "fake.pdf"
        p.write_bytes(b"%PDF-1.4 not a real pdf")
        assert extract_text(p, "application/pdf") == "[PDF 文档 - 解析失败]"

    def test_pdf_blank_page_returns_placeholder(self, tmp_path):
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        p = tmp_path / "blank.pdf"
        with open(p, "wb") as f:
            writer.write(f)
        assert extract_text(p, "application/pdf") == "[PDF 文档 - 解析失败]"

    def test_docx_extracts_paragraphs(self, tmp_path):
        p = tmp_path / "doc.docx"
        _make_docx(p, ["第一段", "第二段内容"])
        text = extract_text(p, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        assert "第一段" in text
        assert "第二段内容" in text

    def test_docx_bad_zip_returns_empty(self, tmp_path):
        p = tmp_path / "bad.docx"
        p.write_bytes(b"not a zip")
        assert extract_text(p, "application/vnd.openxmlformats-officedocument.wordprocessingml.document") == ""

    def test_image_returns_size_placeholder(self, tmp_path):
        p = tmp_path / "pic.png"
        p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        assert extract_text(p, "image/png") == f"[图片文件 - {p.stat().st_size} bytes]"

    def test_unknown_type_returns_empty(self, tmp_path):
        p = tmp_path / "x.bin"
        p.write_bytes(b"abc")
        assert extract_text(p, "application/x-executable") == ""


class TestValidateUpload:
    def test_too_large(self):
        with pytest.raises(HTTPException):
            validate_upload("text/plain", (MAX_FILE_SIZE_MB + 1) * 1024 * 1024)

    def test_invalid_type(self):
        with pytest.raises(HTTPException):
            validate_upload("application/x-executable", 100)

    def test_whitelist_derives_from_registry(self):
        assert frozenset(FORMAT_REGISTRY) == ALLOWED_CONTENT_TYPES

    def test_valid_passes(self):
        validate_upload("text/plain", 100)


class TestValidateMagic:
    def test_text_rejects_nul_bytes(self):
        with pytest.raises(HTTPException):
            validate_magic(b"abc\x00def", "text/plain")

    def test_pdf_rejects_wrong_magic(self):
        with pytest.raises(HTTPException):
            validate_magic(b"GIF89a not pdf", "application/pdf")

    def test_webp_requires_fourcc(self):
        with pytest.raises(HTTPException):
            validate_magic(b"RIFF\x00\x00\x00\x00JPEG", "image/webp")

    def test_valid_pdf_passes(self):
        validate_magic(b"%PDF-1.4 content", "application/pdf")

    def test_valid_text_passes(self):
        validate_magic("普通文本".encode(), "text/plain")
