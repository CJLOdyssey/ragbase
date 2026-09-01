"""Environment bootstrap — .env loading and safe typed reads.

Shared by config/app/database so env-file parsing semantics stay in one place.
"""

from __future__ import annotations

import os
from pathlib import Path

# backend/.env — the backend package's project root.
_DEFAULT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def load_dotenv(path: Path | None = None) -> None:
    """Load ``.env`` into os.environ without overriding existing variables.

    Standard dotenv semantics: a variable already set by the shell (or a test
    fixture) wins over the file value.
    """
    env_file = path or _DEFAULT_ENV_FILE
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key:
            os.environ.setdefault(key, _unquote(value.strip()))


def env_int(key: str, default: int) -> int:
    """Read an integer env var, falling back to ``default`` on any parse error."""
    try:
        return int(os.environ[key])
    except (KeyError, ValueError, TypeError):
        return default


def env_float(key: str, default: float) -> float:
    """Read a float env var, falling back to ``default`` on any parse error."""
    try:
        return float(os.environ[key])
    except (KeyError, ValueError, TypeError):
        return default


def _unquote(value: str) -> str:
    """Strip one pair of matching surrounding quotes, e.g. 'abc' or "abc"."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


__all__ = ["env_float", "env_int", "load_dotenv"]