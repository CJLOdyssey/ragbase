"""LLM configuration — env-driven, Pydantic-validated, BYOK by default."""

import os

from pydantic import BaseModel, Field

from core.env import env_float, env_int, load_dotenv
from core.infra.logging_config import get_logger

logger = get_logger(__name__)

load_dotenv()


class LLMConfig(BaseModel):
    """LLM runtime settings with Pydantic validation (bounds enforced)."""

    # Reject unknown keys so a mapping typo fails loudly instead of silently
    # being ignored downstream.
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
        """Safe string representation with the API key masked."""
        safe = self.model_dump()
        safe["api_key"] = "***" if self.api_key else "(unset)"
        return f"LLMConfig({safe})"


def load_config() -> LLMConfig:
    """Load configuration from environment variables.

    Reads DEEPSEEK_API_KEY/OPENAI_API_KEY for backward compatibility only —
    the server never uses them as a fallback (BYOK pattern). Users configure
    their own keys through the frontend key vault instead.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
    api_base = os.environ.get("OPENAI_BASE_URL") or None
    model = os.environ.get("OPENAI_MODEL", "deepseek-v4-flash")
    temperature = env_float("TEMPERATURE", 0.7)
    max_rounds = env_int("MAX_ROUNDS", 5)
    timeout = env_int("TIMEOUT", 120)
    max_retries = env_int("MAX_RETRIES", 3)
    max_requirement_length = env_int("MAX_REQUIREMENT_LENGTH", 2000)
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
