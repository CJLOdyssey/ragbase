"""Enterprise API Key Vault — Fernet-encrypted at-rest key storage.

Keys are encrypted with AES-128-CBC + HMAC-SHA256 (Fernet) before
touching the database. The master encryption secret is set via the
KEY_VAULT_SECRET environment variable and MUST be:

  - At least 32 bytes of high-entropy random data
  - Rotated via key-rotation protocol (supports multiple secrets)
  - Never logged, never exposed via API

Architecture:
  User configures key ONCE → server encrypts & stores → never leaves server again.
  Subsequent LLM calls reference the key by ID; the server decrypts on-the-fly.
"""

import base64
import hashlib
import os
import platform
import uuid

from core.infra.logging_config import get_logger
from cryptography.fernet import Fernet, MultiFernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = get_logger(__name__)


def _derive_fernet_key(secret: str) -> bytes:
    """Derive a 32-byte Fernet key from any-length secret via PBKDF2."""
    salt = b"ragbase-key-vault-v2"  # static salt — secret provides the entropy
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return key


def _get_fernet() -> Fernet | MultiFernet:
    """Get the Fernet instance for the current master secret.

    If KEY_VAULT_SECRET_ROTATED is set, returns a MultiFernet that
    supports decryption with old keys while encrypting with the new one.
    This enables zero-downtime key rotation.
    """
    primary_secret = os.environ.get("KEY_VAULT_SECRET", "")
    rotated_secret = os.environ.get("KEY_VAULT_SECRET_ROTATED", "")

    if not primary_secret:
        # Fallback: derive from a machine fingerprint (NOT for multi-instance deploys)
        logger.warning(
            "KEY_VAULT_SECRET not set — using machine-local derivation. "
            "Keys will be unreadable on other instances."
        )
        primary_secret = _machine_fingerprint()

    primary_key = _derive_fernet_key(primary_secret)

    if rotated_secret:
        rotated_key = _derive_fernet_key(rotated_secret)
        return MultiFernet([Fernet(primary_key), Fernet(rotated_key)])

    return Fernet(primary_key)


def _machine_fingerprint() -> str:
    """Derive a deterministic secret from machine identity.

    Uses hostname + filesystem UUID as entropy source.
    This is a last-resort fallback — production MUST set KEY_VAULT_SECRET.
    """

    fingerprint = f"{platform.node()}-{uuid.getnode()}"
    return hashlib.sha256(fingerprint.encode()).hexdigest()


def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key for database storage.

    Returns a Fernet token (base64-encoded ciphertext + HMAC).
    The plaintext key is never logged.
    """
    if not plaintext:
        raise ValueError("API key must not be empty")
    f = _get_fernet()
    return f.encrypt(plaintext.encode()).decode()


def decrypt_api_key(ciphertext: str) -> str:
    """Decrypt an API key from database storage.

    Raises cryptography.fernet.InvalidToken if the ciphertext is
    tampered with or the encryption secret has changed.
    """
    if not ciphertext:
        raise ValueError("Ciphertext must not be empty")
    f = _get_fernet()
    return f.decrypt(ciphertext.encode()).decode()


def mask_api_key(plaintext: str) -> str:
    """Return a human-safe masked version: 'sk-...xyz'.

    Only shows first 3 and last 4 characters. Used for display
    in the frontend key list and audit logs.
    """
    if len(plaintext) <= 8:
        return plaintext[:2] + "***"
    return plaintext[:3] + "..." + plaintext[-4:]
