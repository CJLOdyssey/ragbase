"""Reusable domain validation rules — pure functions, transport-agnostic.

Each validator has a single responsibility (SRP) and returns normalized
values so callers never re-implement cleanup logic (PoLA).
"""

from urllib.parse import urlparse


def validate_base_url(v: str | None) -> str | None:
    """Normalize and validate an optional API base URL.

    - ``None`` / empty / whitespace → ``None`` (caller uses provider default)
    - Must be an absolute http(s) URL, otherwise raise ``ValueError``.

    Guards against garbage being stored and later concatenated into request
    paths like ``{base_url}/embeddings`` (e.g. an email leaking in produced
    ``admin@example.com/embeddings`` → hard failure at call time).
    """
    if v is None:
        return None
    v = v.strip()
    if not v:
        return None
    parsed = urlparse(v)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(
            "base_url 必须是合法的 http(s) 地址"
            "（如 https://api.siliconflow.cn/v1），"
            f"收到: {v!r}"
        )
    return v
