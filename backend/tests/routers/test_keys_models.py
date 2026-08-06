"""Unit tests for """

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit
from pydantic import ValidationError


class TestKeysModels:
    """Test KeyCreateRequest/KeyUpdateRequest validation, Fernet encryption roundtrip."""

    def test_key_create_request_valid(self):
        from routers.keys import KeyCreateRequest

        req = KeyCreateRequest(
            provider="openai",
            label="My OpenAI Key",
            api_key="sk-test123",
        )
        assert req.provider == "openai"
        assert req.label == "My OpenAI Key"
        assert req.api_key == "sk-test123"
        assert req.usage_type == "chat"
        assert req.models == []
        assert req.is_default is False

    def test_key_create_request_with_all_fields(self):
        from routers.keys import KeyCreateRequest

        req = KeyCreateRequest(
            provider="deepseek",
            usage_type="general",
            label="DeepSeek Key",
            api_key="sk-ds-test",
            base_url="https://api.deepseek.com",
            models=["deepseek-chat", "deepseek-coder"],
            is_default=True,
        )
        assert req.provider == "deepseek"
        assert req.usage_type == "general"
        assert req.base_url == "https://api.deepseek.com"
        assert len(req.models) == 2
        assert req.is_default is True

    def test_key_create_request_invalid_provider_pattern(self):
        from routers.keys import KeyCreateRequest

        with pytest.raises(ValidationError):
            KeyCreateRequest(
                provider="OpenAI!",
                label="test",
                api_key="sk-test",
            )

    def test_key_create_request_invalid_usage_type(self):
        from routers.keys import KeyCreateRequest

        with pytest.raises(ValidationError):
            KeyCreateRequest(
                provider="openai",
                usage_type="invalid",
                label="test",
                api_key="sk-test",
            )

    def test_key_create_request_empty_provider(self):
        from routers.keys import KeyCreateRequest

        with pytest.raises(ValidationError):
            KeyCreateRequest(
                provider="",
                label="test",
                api_key="sk-test",
            )

    def test_key_create_request_label_max_length(self):
        from routers.keys import KeyCreateRequest

        with pytest.raises(ValidationError):
            KeyCreateRequest(
                provider="openai",
                label="x" * 65,
                api_key="sk-test",
            )

    def test_key_update_request_partial(self):
        from routers.keys import KeyUpdateRequest

        req = KeyUpdateRequest(label="Updated Label")
        assert req.label == "Updated Label"
        assert req.api_key is None
        assert req.is_active is None

    def test_key_update_request_invalid_usage_type(self):
        from routers.keys import KeyUpdateRequest

        with pytest.raises(ValidationError):
            KeyUpdateRequest(usage_type="bad_type")

    def test_fetch_models_request(self):
        from routers.keys import FetchModelsRequest

        req = FetchModelsRequest(api_key="sk-test", base_url="https://api.test.com")
        assert req.api_key == "sk-test"
        assert req.base_url == "https://api.test.com"
        assert req.provider == "custom"

    def test_key_response_model_fields(self):
        from routers.keys import KeyResponse

        resp = KeyResponse(
            id="key-1",
            provider="openai",
            usage_type="llm",
            label="test",
            key_masked="sk-...est",
            base_url=None,
            models=["gpt-4"],
            is_active=True,
            is_default=False,
            last_used_at=None,
            created_at=None,
        )
        assert resp.key_masked == "sk-...est"
        assert resp.is_active is True
        assert resp.models == ["gpt-4"]

    def test_encrypt_decrypt_roundtrip(self):
        from core.infra.key_vault import decrypt_api_key, encrypt_api_key

        with patch.dict("os.environ", {"KEY_VAULT_SECRET": "a" * 32}):
            plaintext = "sk-my-secret-api-key-12345"
            encrypted = encrypt_api_key(plaintext)
            assert encrypted != plaintext
            decrypted = decrypt_api_key(encrypted)
            assert decrypted == plaintext

    def test_mask_api_key(self):
        from core.infra.key_vault import mask_api_key

        masked = mask_api_key("sk-my-secret-key-xyz")
        assert masked == "sk-...-xyz"

    def test_mask_short_key(self):
        from core.infra.key_vault import mask_api_key

        masked = mask_api_key("abc")
        assert masked == "ab***"

    def test_encrypt_empty_key_raises(self):
        from core.infra.key_vault import encrypt_api_key

        with pytest.raises(ValueError, match="must not be empty"):
            encrypt_api_key("")

    def test_decrypt_empty_key_raises(self):
        from core.infra.key_vault import decrypt_api_key

        with pytest.raises(ValueError, match="must not be empty"):
            decrypt_api_key("")

    def test_user_api_key_model_columns(self):
        from core.infra.database import UserApiKey

        cols = {c.name for c in UserApiKey.__table__.columns}
        assert "encrypted_key" in cols
        assert "provider" in cols
        assert "usage_type" in cols
        assert "is_default" in cols
        assert "is_active" in cols

    def test_user_api_key_defaults(self):
        from core.infra.database import UserApiKey

        c_map = {c.name: c for c in UserApiKey.__table__.columns}
        assert c_map["usage_type"].default.arg == "chat"
        assert c_map["is_active"].default.arg is True
        assert c_map["is_default"].default.arg is False


# ─────────────────────────────────────────────────────────────────────
# 10. backend/streaming.py — StreamEmitter edge cases
# ─────────────────────────────────────────────────────────────────────


