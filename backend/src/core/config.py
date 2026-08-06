"""LLM configuration via environment variables and .env file."""

import os
from pathlib import Path

from pydantic import BaseModel, Field

from core.infra.logging_config import get_logger

logger = get_logger(__name__)

_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


class LLMConfig(BaseModel):
    """LLM configuration with validation via Pydantic."""

    model_config = {"extra": "forbid"}

    api_key: str = Field(default="", repr=False)
    api_base: str | None = Field(default=None)
    model: str = Field(default="deepseek-v4-flash", min_length=1)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_rounds: int = Field(default=5, ge=1)
    timeout: int = Field(default=120, ge=10)
    max_retries: int = Field(default=3, ge=0)
    max_requirement_length: int = Field(default=2000, ge=1, le=10000)

    def __repr__(self) -> str:
        """Return a safe string representation with masked API key."""
        safe = self.model_dump()
        safe["api_key"] = "***" if self.api_key else "(unset)"
        return f"LLMConfig({safe})"


def load_config() -> LLMConfig:
    """Load configuration from environment variables.

    Note: This reads DEEPSEEK_API_KEY/OPENAI_API_KEY for backward compatibility,
    but the server NEVER uses these as a fallback (BYOK pattern).
    Users must configure their own API keys through the frontend key vault.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    api_base = os.environ.get("OPENAI_BASE_URL") or None
    model = os.environ.get("OPENAI_MODEL", "deepseek-v4-flash")
    temperature = _safe_float("TEMPERATURE", 0.7)
    max_rounds = _safe_int("MAX_ROUNDS", 5)
    timeout = _safe_int("TIMEOUT", 120)
    max_retries = _safe_int("MAX_RETRIES", 3)
    max_requirement_length = _safe_int("MAX_REQUIREMENT_LENGTH", 2000)
    return LLMConfig(
        api_key=api_key,
        api_base=api_base,
        model=model,
        temperature=temperature,
        max_rounds=max_rounds,
        timeout=timeout,
        max_retries=max_retries,
        max_requirement_length=max_requirement_length,
    )


def _safe_float(key: str, default: float) -> float:
    try:
        return float(os.environ[key])
    except (KeyError, ValueError, TypeError):
        return default


def _safe_int(key: str, default: int) -> int:
    try:
        return int(os.environ[key])
    except (KeyError, ValueError, TypeError):
        return default
