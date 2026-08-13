"""Document text extraction for asset indexing.

Suffix-driven: PDF → pypdf; DOCX/XLSX → zipfile + XML via defusedxml
(XXE-hardened — uploaded files are untrusted input); everything else reads
as UTF-8 text.
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
