"""上传格式注册表——白名单/魔数/解析器类型的单一来源。

加一种格式：在 ``FORMAT_REGISTRY`` 注册一项。解析器 ``kind`` 引用
``extractors.py`` 的分派函数（text/pdf/docx/image/none）。
"""

from dataclasses import dataclass

MAX_FILE_SIZE_MB = 10


@dataclass(frozen=True)
class FormatSpec:
    kind: str  # text | pdf | docx | xlsx | image | none
    magic: tuple[bytes, ...] | None = None
    placeholder: str = ""


FORMAT_REGISTRY: dict[str, FormatSpec] = {
    "image/png": FormatSpec(kind="image", magic=(b"\x89PNG\r\n\x1a\n",)),
    "image/jpeg": FormatSpec(kind="image", magic=(b"\xff\xd8\xff",)),
    "image/gif": FormatSpec(kind="image", magic=(b"GIF87a", b"GIF89a")),
    "image/webp": FormatSpec(kind="image", magic=(b"RIFF",)),
    "application/pdf": FormatSpec(kind="pdf", magic=(b"%PDF-",), placeholder="[PDF 文档 - 解析失败]"),
    "application/msword": FormatSpec(
        kind="none", magic=(b"\xd0\xcf\x11\xe0",), placeholder="[Word 文档 - 暂不支持解析]"
    ),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": FormatSpec(
        kind="docx", magic=(b"PK\x03\x04",)
    ),
    "text/plain": FormatSpec(kind="text"),
    "text/markdown": FormatSpec(kind="text"),
    "text/csv": FormatSpec(kind="text"),
    "application/json": FormatSpec(kind="text"),
}

ALLOWED_CONTENT_TYPES = frozenset(FORMAT_REGISTRY)


def validate_upload(content_type: str, size: int) -> None:
    """Reject oversized files and content types outside the whitelist."""
    from core.error_codes import ErrorCode, error_response

    if size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise error_response(ErrorCode.ATTACHMENT_TOO_LARGE, detail=f"文件超过 {MAX_FILE_SIZE_MB}MB 限制")
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail=f"不支持的文件类型: {content_type}")


def validate_magic(content: bytes, content_type: str) -> None:
    """Reject files whose bytes don't match their declared type.

    Text types carry no signature — reject embedded NUL bytes instead.
    """
    from core.error_codes import ErrorCode, error_response

    spec = FORMAT_REGISTRY.get(content_type)
    if spec is None:
        return
    if spec.kind == "text":
        if b"\x00" in content:
            raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail="文件内容与类型不符")
        return
    if content_type == "image/webp":
        # RIFF container + WEBP fourcc at offset 8
        if not (content[:4] == b"RIFF" and content[8:12] == b"WEBP"):
            raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail="文件内容与类型不符")
        return
    if spec.magic is not None and not any(content.startswith(p) for p in spec.magic):
        raise error_response(ErrorCode.ATTACHMENT_TYPE_INVALID, detail="文件内容与类型不符")
