"""Tests for document text extraction (backend/rag/rag_parsing.py)."""

import zipfile
from pathlib import Path

from pypdf import PdfWriter
from rag.rag_parsing import extract_text

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

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


def _make_xlsx(path: Path, shared: list[str], cells: list[list[int | str]]) -> None:
    """Build a minimal XLSX: sharedStrings + one worksheet of cells."""
    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        + "".join(f"<si><t>{s}</t></si>" for s in shared)
        + "</sst>"
    )
    row_xml = ""
    for row in cells:
        cell_xml = ""
        for cell in row:
            if isinstance(cell, int):
                cell_xml += f'<c r="A1" t="n"><v>{cell}</v></c>'
            else:
                idx = shared.index(cell)
                cell_xml += f'<c r="A1" t="s"><v>{idx}</v></c>'
        row_xml += f"<row>{cell_xml}</row>"
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{row_xml}</sheetData></worksheet>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("xl/sharedStrings.xml", shared_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)



def _make_pptx(path: Path, slide_texts: list[list[str]]) -> None:
    """Build a minimal PPTX: one <a:t> run per string in ppt/slides/slideN.xml."""
    ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
    with zipfile.ZipFile(path, "w") as zf:
        for i, runs in enumerate(slide_texts, start=1):
            body = "".join(
                f'<a:p><a:r><a:t>{t}</a:t></a:r></a:p>' for t in runs
            )
            slide = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
                f'xmlns:a="{ns}"><p:cSld><p:spTree>'
                f'<p:sp><p:txBody>{body}</p:txBody></p:sp>'
                f"</p:spTree></p:cSld></p:sld>"
            )
            zf.writestr(f"ppt/slides/slide{i}.xml", slide)


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

    def test_docx_extracts_paragraphs(self, tmp_path):
        p = tmp_path / "doc.docx"
        _make_docx(p, ["第一段", "第二段内容"])
        text = extract_text(p)
        assert "第一段" in text
        assert "第二段内容" in text

    def test_docx_missing_document_returns_empty(self, tmp_path):
        p = tmp_path / "bad.docx"
        with zipfile.ZipFile(p, "w") as zf:
            zf.writestr("word/other.xml", "<x/>")
        assert extract_text(p) == ""

    def test_xlsx_extracts_shared_strings(self, tmp_path):
        p = tmp_path / "book.xlsx"
        _make_xlsx(p, ["名称", "数量", "苹果"], [["名称", "数量"], ["苹果", 3]])
        text = extract_text(p)
        assert "名称" in text
        assert "数量" in text
        assert "苹果" in text

    def test_xlsx_bad_zip_returns_empty(self, tmp_path):
        p = tmp_path / "bad.xlsx"
        p.write_bytes(b"not a zip")
        assert extract_text(p) == ""

    def test_pptx_extracts_slide_texts(self, tmp_path):
        p = tmp_path / "deck.pptx"
        _make_pptx(p, [["标题页"], ["要点一", "要点二"]])
        text = extract_text(p)
        assert "标题页" in text
        assert "要点一" in text
        assert "要点二" in text

    def test_pptx_bad_zip_returns_empty(self, tmp_path):
        p = tmp_path / "bad.pptx"
        p.write_bytes(b"not a zip")
        assert extract_text(p) == ""

    def test_html_strips_tags_keeps_text(self, tmp_path):
        p = tmp_path / "page.html"
        p.write_text(
            "<html><body><h1>标题</h1><p>正文段落</p>"
            "<script>var x = 1;</script><style>.a{}</style></body></html>",
            encoding="utf-8",
        )
        text = extract_text(p)
        assert "标题" in text
        assert "正文段落" in text
        # script/style 内容被剔除。
        assert "var x" not in text
        assert ".a{}" not in text
