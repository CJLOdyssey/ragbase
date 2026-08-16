"""各格式文本提取器——由 ``registry.FORMAT_REGISTRY`` 的 kind 分派。

PDF 用 pypdf；DOCX 用 zipfile + defusedxml（XXE 加固——上传文件不可信）。
解析失败返回空串或注册表占位符，绝不向调用方抛异常。
"""

import zipfile
from pathlib import Path

from defusedxml import ElementTree  # type: ignore[import-untyped]

from .registry import FORMAT_REGISTRY

_TEXT_LIMIT = 50000
_DOCX_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def extract_text(file_path: Path, content_type: str) -> str:
    """Extract readable text from an uploaded attachment by content type."""
    spec = FORMAT_REGISTRY.get(content_type)
    if spec is None:
        return ""
    try:
        if spec.kind == "text":
            return Path(file_path).read_text(encoding="utf-8", errors="ignore")[:_TEXT_LIMIT]
        if spec.kind == "pdf":
            return _extract_pdf(file_path) or spec.placeholder
        if spec.kind == "docx":
            return _extract_docx(file_path)
        if spec.kind == "image":
            return f"[图片文件 - {Path(file_path).stat().st_size} bytes]"
    except Exception:
        return spec.placeholder
    return spec.placeholder


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
