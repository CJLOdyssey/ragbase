"""密钥模型/加密工具测试：请求校验、Fernet 加解密、掩码、ORM 默认值。"""

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
        assert req.capabilities == ["llm"]
        assert req.models == []
        assert req.is_default is False

    def test_key_create_request_with_all_fields(self):
        from routers.keys import KeyCreateRequest

        req = KeyCreateRequest(
            provider="deepseek",
            capabilities=["llm", "embedding"],
            label="DeepSeek Key",
            api_key="sk-ds-test",
            base_url="https://api.deepseek.com",
            models=["deepseek-chat", "deepseek-coder"],
            is_default=True,
        )
        assert req.provider == "deepseek"
        assert req.capabilities == ["llm", "embedding"]
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

    def test_key_create_request_invalid_capability(self):
        from routers.keys import KeyCreateRequest

        with pytest.raises(ValidationError):
            KeyCreateRequest(
                provider="openai",
                capabilities=["bogus"],
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

    def test_key_update_request_invalid_capability(self):
        from routers.keys import KeyUpdateRequest

        with pytest.raises(ValidationError):
            KeyUpdateRequest(capabilities=["bad_type"])

    def test_key_create_request_with_model_types(self):
        from routers.keys import KeyCreateRequest

        req = KeyCreateRequest(
            provider="custom",
            label="SiliconFlow",
            api_key="sk-test",
            models=["gpt-4o"],
            model_types={"gpt-4o": "embedding"},
        )
        assert req.model_types == {"gpt-4o": "embedding"}

    def test_key_create_request_invalid_model_type_value(self):
        from routers.keys import KeyCreateRequest

        with pytest.raises(ValidationError):
            KeyCreateRequest(
                provider="custom",
                label="test",
                api_key="sk-test",
                model_types={"gpt-4o": "bogus"},
            )

    def test_key_update_request_model_types(self):
        from routers.keys import KeyUpdateRequest

        req = KeyUpdateRequest(model_types={"gpt-4o": "llm"})
        assert req.model_types == {"gpt-4o": "llm"}

    def test_key_update_request_invalid_model_type_value(self):
        from routers.keys import KeyUpdateRequest

        with pytest.raises(ValidationError):
            KeyUpdateRequest(model_types={"gpt-4o": "bogus"})

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
            capabilities=["llm"],
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

    def test_key_response_model_types_field(self):
        from routers.keys import KeyResponse

        resp = KeyResponse(
            id="key-1",
            provider="custom",
            capabilities=["llm"],
            label="test",
            key_masked="sk-...est",
            base_url=None,
            models=["gpt-4o"],
            model_types={"gpt-4o": "embedding"},
            is_active=True,
            is_default=False,
            last_used_at=None,
            created_at=None,
        )
        assert resp.model_types == {"gpt-4o": "embedding"}


# ── /api/keys HTTP round-trip ───────────────────────────────────────────────


def test_model_types_roundtrip_create_and_update(client):
    created = client.post(
        "/api/keys",
        json={
            "provider": "custom",
            "capabilities": ["llm"],
            "label": "roundtrip",
            "api_key": "sk-test",
            "models": ["gpt-4o"],
            "model_types": {"gpt-4o": "embedding"},
            "is_default": False,
        },
    )
    assert created.status_code == 201
    assert created.json()["model_types"] == {"gpt-4o": "embedding"}

    updated = client.put(
        f"/api/keys/{created.json()['id']}",
        json={"model_types": {"gpt-4o": "rerank"}},
    )
    assert updated.status_code == 200
    assert updated.json()["model_types"] == {"gpt-4o": "rerank"}


def test_add_key_rejects_unknown_model_type_value(client):
    resp = client.post(
        "/api/keys",
        json={
            "provider": "custom",
            "capabilities": ["llm"],
            "label": "bad",
            "api_key": "sk-test",
            "models": ["gpt-4o"],
            "model_types": {"gpt-4o": "bogus"},
            "is_default": False,
        },
    )
    assert resp.status_code == 422


def test_encrypt_decrypt_roundtrip():
    from core.infra.key_vault import decrypt_api_key, encrypt_api_key

    with patch.dict("os.environ", {"KEY_VAULT_SECRET": "a" * 32}):
        plaintext = "sk-my-secret-api-key-12345"
        encrypted = encrypt_api_key(plaintext)
        assert encrypted != plaintext
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == plaintext


def test_mask_api_key():
    from core.infra.key_vault import mask_api_key

    masked = mask_api_key("sk-my-secret-key-xyz")
    assert masked == "sk-...-xyz"


def test_mask_short_key():
    from core.infra.key_vault import mask_api_key

    masked = mask_api_key("abc")
    assert masked == "ab***"


def test_encrypt_empty_key_raises():
    from core.infra.key_vault import encrypt_api_key

    with pytest.raises(ValueError, match="must not be empty"):
        encrypt_api_key("")


def test_decrypt_empty_key_raises():
    from core.infra.key_vault import decrypt_api_key

    with pytest.raises(ValueError, match="must not be empty"):
        decrypt_api_key("")


def test_user_api_key_model_columns():
    from core.infra.database import UserApiKey

    cols = {c.name for c in UserApiKey.__table__.columns}
    assert "encrypted_key" in cols
    assert "provider" in cols
    assert "capabilities" in cols
    assert "is_default" in cols
    assert "is_active" in cols


def test_user_api_key_defaults():
    from core.infra.database import UserApiKey

    c_map = {c.name: c for c in UserApiKey.__table__.columns}
    caps_default = c_map["capabilities"].default.arg
    assert callable(caps_default) and caps_default(None) == []
    assert c_map["is_active"].default.arg is True
    assert c_map["is_default"].default.arg is False


# ─────────────────────────────────────────────────────────────────────
# 10. backend/streaming.py — StreamEmitter edge cases
# ─────────────────────────────────────────────────────────────────────


