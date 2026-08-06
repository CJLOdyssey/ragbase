"""Unit tests for """

from unittest.mock import patch

import pytest
from pydantic import ValidationError


class TestLLMConfig:
    def test_default_values(self):
        from core.config import LLMConfig

        cfg = LLMConfig()
        assert cfg.api_key == ""
        assert cfg.api_base is None
        assert cfg.model == "deepseek-v4-flash"
        assert cfg.temperature == 0.7
        assert cfg.max_rounds == 5
        assert cfg.timeout == 120
        assert cfg.max_retries == 3
        assert cfg.max_requirement_length == 2000

    def test_extra_fields_forbidden(self):
        from core.config import LLMConfig

        with pytest.raises(ValidationError):
            LLMConfig(unknown_field="nope")

    def test_model_min_length_validation(self):
        from core.config import LLMConfig

        with pytest.raises(ValidationError):
            LLMConfig(model="")

    def test_temperature_range(self):
        from core.config import LLMConfig

        with pytest.raises(ValidationError):
            LLMConfig(temperature=-0.1)
        with pytest.raises(ValidationError):
            LLMConfig(temperature=1.1)

    def test_max_rounds_ge_1(self):
        from core.config import LLMConfig

        with pytest.raises(ValidationError):
            LLMConfig(max_rounds=0)

    def test_timeout_ge_10(self):
        from core.config import LLMConfig

        with pytest.raises(ValidationError):
            LLMConfig(timeout=5)

    def test_max_requirement_length_range(self):
        from core.config import LLMConfig

        with pytest.raises(ValidationError):
            LLMConfig(max_requirement_length=0)
        with pytest.raises(ValidationError):
            LLMConfig(max_requirement_length=20000)

    def test_repr_masks_api_key(self):
        from core.config import LLMConfig

        cfg = LLMConfig(api_key="secret123")
        rep = repr(cfg)
        assert "***" in rep
        assert "secret123" not in rep

    def test_repr_unset_key(self):
        from core.config import LLMConfig

        rep = repr(LLMConfig())
        assert "(unset)" in rep




class TestSafeFloat:
    def test_returns_value_when_env_set(self):
        from core.config import _safe_float

        with patch("core.config.os.environ", {"TEST_KEY": "0.85"}):
            assert _safe_float("TEST_KEY", 0.7) == 0.85

    def test_returns_default_on_missing_key(self):
        from core.config import _safe_float

        with patch("core.config.os.environ", {}):
            assert _safe_float("MISSING", 0.5) == 0.5

    def test_returns_default_on_invalid_value(self):
        from core.config import _safe_float

        with patch("core.config.os.environ", {"BAD": "not-a-number"}):
            assert _safe_float("BAD", 0.3) == 0.3




class TestSafeInt:
    def test_returns_value_when_env_set(self):
        from core.config import _safe_int

        with patch("core.config.os.environ", {"TEST_KEY": "42"}):
            assert _safe_int("TEST_KEY", 10) == 42

    def test_returns_default_on_missing_key(self):
        from core.config import _safe_int

        with patch("core.config.os.environ", {}):
            assert _safe_int("MISSING", 7) == 7

    def test_returns_default_on_invalid_value(self):
        from core.config import _safe_int

        with patch("core.config.os.environ", {"BAD": "xyz"}):
            assert _safe_int("BAD", 3) == 3




class TestLoadConfig:
    def test_loads_from_env(self):
        from core.config import load_config

        env = {
            "DEEPSEEK_API_KEY": "sk-test",
            "OPENAI_BASE_URL": "https://custom.example.com",
            "OPENAI_MODEL": "gpt-4",
            "TEMPERATURE": "0.5",
            "MAX_ROUNDS": "10",
            "TIMEOUT": "60",
            "MAX_RETRIES": "5",
            "MAX_REQUIREMENT_LENGTH": "5000",
        }
        with patch("core.config.os.environ", env):
            cfg = load_config()
            assert cfg.api_key == "sk-test"
            assert cfg.api_base == "https://custom.example.com"
            assert cfg.model == "gpt-4"
            assert cfg.temperature == 0.5
            assert cfg.max_rounds == 10
            assert cfg.timeout == 60
            assert cfg.max_retries == 5
            assert cfg.max_requirement_length == 5000

    def test_uses_openai_api_key_fallback(self):
        from core.config import load_config

        with patch("core.config.os.environ", {"OPENAI_API_KEY": "sk-fallback"}):
            cfg = load_config()
            assert cfg.api_key == "sk-fallback"

    def test_deepseek_takes_precedence(self):
        from core.config import load_config

        env = {"DEEPSEEK_API_KEY": "sk-deepseek", "OPENAI_API_KEY": "sk-openai"}
        with patch("core.config.os.environ", env):
            cfg = load_config()
            assert cfg.api_key == "sk-deepseek"

    def test_defaults_when_no_env(self):
        from core.config import load_config

        with patch("core.config.os.environ", {}):
            cfg = load_config()
            assert cfg.api_key == ""
            assert cfg.model == "deepseek-v4-flash"
            assert cfg.temperature == 0.7


# ─────────────────────────────────────────────────────────────────────
# 2. backend/broker.py — Redis pub/sub & Celery setup
# ─────────────────────────────────────────────────────────────────────


