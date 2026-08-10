"""Document text extraction for asset indexing.

Suffix-driven: PDF goes through pypdf (lazy import keeps this module
importable without the dependency), everything else reads as UTF-8 text.
"""

from pathlib import Path


def extract_text(path: str | Path) -> str:
    """Extract readable text from an asset file by extension."""
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        return _extract_pdf(p)
    return p.read_text(encoding="utf-8", errors="ignore")


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)
