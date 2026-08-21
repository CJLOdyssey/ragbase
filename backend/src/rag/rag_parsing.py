"""Document text extraction for asset indexing.

Suffix-driven: PDF → pypdf; DOCX/XLSX/PPTX → zipfile + XML via defusedxml
(XXE-hardened — uploaded files are untrusted input); HTML strips tags;
CSV/TXT/MD read as UTF-8 text.
"""

import re
import zipfile
from pathlib import Path

from defusedxml import ElementTree  # type: ignore[import-untyped]

_DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
_XLSX_NS = {
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
# XLSX cell types: s=shared string (index into sharedStrings.xml), inlineStr=inline text
_XLSX_SHARED = "s"
_XLSX_INLINE = "inlineStr"
_PPTX_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def extract_text(path: str | Path) -> str:
    """Extract readable text from an asset file by extension."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        return _extract_pdf(p)
    if suffix == ".docx":
        return _extract_docx(p)
    if suffix == ".xlsx":
        return _extract_xlsx(p)
    if suffix == ".pptx":
        return _extract_pptx(p)
    if suffix in (".html", ".htm"):
        return _extract_html(p)
    # .doc/.xls/.ppt (legacy OLE) 无轻量解析，退化为文本读取（乱码但不抛异常）
    # .csv/.txt/.md/.json 等直接按文本读取
    return p.read_text(encoding="utf-8", errors="ignore")


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(path: Path) -> str:
    """Concatenate paragraph text from word/document.xml (w:t nodes)."""
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile):
        return ""
    root = ElementTree.fromstring(xml)
    paragraphs = []
    for para in root.iter(f"{{{_DOCX_NS['w']}}}p"):
        text = "".join(
            node.text or ""
            for node in para.iter(f"{{{_DOCX_NS['w']}}}t")
        ).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def _extract_xlsx(path: Path) -> str:
    """Read cell text from all worksheets, preserving row order.

    Shared strings resolve via xl/sharedStrings.xml; inline strings carry
    their own text. Only text-bearing cells are emitted.
    """
    try:
        with zipfile.ZipFile(path) as zf:
            shared = _xlsx_shared_strings(zf)
            sheet_names = sorted(
                n for n in zf.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)
            )
            rows: list[str] = []
            for sheet in sheet_names:
                rows.extend(_xlsx_sheet_rows(zf.read(sheet), shared))
    except (KeyError, zipfile.BadZipFile):
        return ""
    return "\n".join(rows)


def _xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ElementTree.fromstring(zf.read("xl/sharedStrings.xml"))
    out = []
    for si in root.iter(f"{{{_XLSX_NS['s']}}}si"):
        text = "".join(node.text or "" for node in si.iter(f"{{{_XLSX_NS['s']}}}t"))
        out.append(text)
    return out


def _xlsx_sheet_rows(xml: bytes, shared: list[str]) -> list[str]:
    root = ElementTree.fromstring(xml)
    rows: list[str] = []
    for row in root.iter(f"{{{_XLSX_NS['s']}}}row"):
        cells: list[str] = []
        for cell in row.iter(f"{{{_XLSX_NS['s']}}}c"):
            t = cell.get("t")
            text = ""
            for node in cell.iter(f"{{{_XLSX_NS['s']}}}v"):
                if t == _XLSX_SHARED:
                    idx = int(node.text or "0")
                    text = shared[idx] if idx < len(shared) else ""
                else:
                    text = node.text or ""
            if not text and t == _XLSX_INLINE:
                text = "".join(
                    node.text or ""
                    for node in cell.iter(f"{{{_XLSX_NS['s']}}}t")
                )
            if text:
                cells.append(text)
        if cells:
            rows.append(" | ".join(cells))
    return rows


def _extract_pptx(path: Path) -> str:
    """Extract text from PPTX slides (a:t nodes in ppt/slides/)."""
    try:
        with zipfile.ZipFile(path) as zf:
            slide_names = sorted(
                n for n in zf.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)
            )
            texts: list[str] = []
            for name in slide_names:
                root = ElementTree.fromstring(zf.read(name))
                for node in root.iter(f"{{{_PPTX_NS['a']}}}t"):
                    if node.text and node.text.strip():
                        texts.append(node.text.strip())
            return "\n\n".join(texts)
    except (KeyError, zipfile.BadZipFile):
        return ""
    return ""


def _extract_html(path: Path) -> str:
    """Strip HTML tags to plain text for indexing."""
    raw = path.read_text(encoding="utf-8", errors="ignore")
    # 去 script/style 块
    raw = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw)
    raw = re.sub(r"(?is)<style.*?>.*?</style>", " ", raw)
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text).strip()
    return text
