"""Tests for document text extraction (backend/rag/rag_parsing.py)."""

from pathlib import Path

from pypdf import PdfWriter
from rag.rag_parsing import extract_text

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


class TestExtractText:
    def test_markdown_reads_as_text(self, tmp_path):
        p = tmp_path / "doc.md"
        p.write_text("# 标题\n内容", encoding="utf-8")
        assert "标题" in extract_text(p)

    def test_txt_reads_as_text(self, tmp_path):
        p = tmp_path / "doc.txt"
        p.write_text("纯文本内容", encoding="utf-8")
        assert "纯文本内容" in extract_text(p)

    def test_pdf_with_text_layer(self):
        """A real PDF with a text layer must extract its content."""
        text = extract_text(FIXTURES / "sample.pdf")
        assert "Hello PDF Index" in text

    def test_empty_pdf_returns_empty(self, tmp_path):
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        pdf_path = tmp_path / "blank.pdf"
        with open(pdf_path, "wb") as f:
            writer.write(f)
        assert extract_text(pdf_path).strip() == ""
