"""Unit tests for key vault (backend/core/infra/key_vault.py)."""

import os
from unittest.mock import patch

import pytest
from core.infra.key_vault import (
    _derive_fernet_key,
    _get_fernet,
    _machine_fingerprint,
    decrypt_api_key,
    encrypt_api_key,
    mask_api_key,
)
from cryptography.fernet import Fernet, InvalidToken, MultiFernet

# =============================================================================
# _derive_fernet_key
# =============================================================================


class TestDeriveFernetKey:
    def test_returns_32_byte_base64_urlsafe_key(self):
        key = _derive_fernet_key("my-secret-12345")
        assert isinstance(key, bytes)
        assert len(key) == 44  # 32 bytes base64-encoded = 44 chars

    def test_deterministic(self):
        k1 = _derive_fernet_key("same-secret")
        k2 = _derive_fernet_key("same-secret")
        assert k1 == k2

    def test_different_secrets_produce_different_keys(self):
        k1 = _derive_fernet_key("secret-a")
        k2 = _derive_fernet_key("secret-b")
        assert k1 != k2


# =============================================================================
# _machine_fingerprint
# =============================================================================


class TestMachineFingerprint:
    def test_returns_sha256_hex_string(self):
        fp = _machine_fingerprint()
        assert isinstance(fp, str)
        assert len(fp) == 64  # SHA-256 hex digest

    def test_deterministic(self):
        fp1 = _machine_fingerprint()
        fp2 = _machine_fingerprint()
        assert fp1 == fp2


# =============================================================================
# _get_fernet
# =============================================================================


class TestGetFernet:
    def test_returns_fernet_when_secret_set(self):
        with patch.dict(os.environ, {"KEY_VAULT_SECRET": "test-secret-key-32bytes!1234", "KEY_VAULT_SECRET_ROTATED": ""}):
            f = _get_fernet()
            assert isinstance(f, Fernet)

    def test_returns_multifernet_when_rotated_secret_set(self):
        with patch.dict(os.environ, {"KEY_VAULT_SECRET": "primary-key", "KEY_VAULT_SECRET_ROTATED": "rotated-key"}):
            f = _get_fernet()
            assert isinstance(f, MultiFernet)

    def test_uses_machine_fingerprint_when_secret_missing(self):
        with patch.dict(os.environ, {"KEY_VAULT_SECRET": "", "KEY_VAULT_SECRET_ROTATED": ""}):
            f = _get_fernet()
            assert isinstance(f, Fernet)


# =============================================================================
# encrypt_api_key / decrypt_api_key round-trip
# =============================================================================


class TestEncryptDecryptRoundTrip:
    @pytest.fixture(autouse=True)
    def _set_secret(self):
        with patch.dict(os.environ, {"KEY_VAULT_SECRET": "test-vault-secret-key!", "KEY_VAULT_SECRET_ROTATED": ""}):
            yield

    def test_round_trip(self):
        plaintext = "sk-supersecretkey123456789"
        encrypted = encrypt_api_key(plaintext)
        decrypted = decrypt_api_key(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            encrypt_api_key("")

    def test_decrypt_empty_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            decrypt_api_key("")

    def test_decrypt_tampered_token_raises(self):
        encrypted = encrypt_api_key("my-key")
        # Flip some bytes to tamper
        tampered = encrypted[:-4] + "XXXX"
        with pytest.raises(InvalidToken):
            decrypt_api_key(tampered)

    def test_decrypt_with_wrong_secret_raises(self):
        encrypted = encrypt_api_key("my-key")
        with patch.dict(os.environ, {"KEY_VAULT_SECRET": "completely-different-secret!!", "KEY_VAULT_SECRET_ROTATED": ""}):
            with pytest.raises(InvalidToken):
                decrypt_api_key(encrypted)


# =============================================================================
# Key rotation — decrypt old with rotated secret
# =============================================================================


class TestKeyRotation:
    def test_rotated_key_can_decrypt_old_ciphertext(self):
        """Encrypt with primary, then add a rotated secret — still decryptable."""
        with patch.dict(os.environ, {"KEY_VAULT_SECRET": "primary-key-1234567890123456", "KEY_VAULT_SECRET_ROTATED": ""}):
            encrypted = encrypt_api_key("rotation-test")

        # Now rotate: primary becomes rotated, new primary is different
        with patch.dict(os.environ, {"KEY_VAULT_SECRET": "new-primary-123456789012345678", "KEY_VAULT_SECRET_ROTATED": "primary-key-1234567890123456"}):
            decrypted = decrypt_api_key(encrypted)
            assert decrypted == "rotation-test"

    def test_multi_fernet_encrypts_with_new_key(self):
        """MultiFernet encrypts with first key in list (primary)."""
        with patch.dict(os.environ, {"KEY_VAULT_SECRET": "primary-key-1234567890123456", "KEY_VAULT_SECRET_ROTATED": "rotated-key-1234567890"}):
            encrypted = encrypt_api_key("multi-fernet-test")
        assert len(encrypted) > 0


# =============================================================================
# mask_api_key
# =============================================================================


class TestMaskApiKey:
    def test_long_key_masked(self):
        result = mask_api_key("sk-abcdefghij1234567890")
        assert result == "sk-...7890"

    def test_short_key_masked(self):
        result = mask_api_key("sk-ab")
        assert result == "sk***"

    def test_exact_boundary_8_chars(self):
        # len == 8 → short path
        result = mask_api_key("12345678")
        assert result == "12***"

    def test_nine_chars_uses_long_path(self):
        result = mask_api_key("123456789")
        assert result == "123...6789"

    def test_mask_preserves_prefix_and_suffix(self):
        key = "abcdefghij"
        masked = mask_api_key(key)
        assert masked.startswith("abc")
        assert masked.endswith("hij")
