"""Unit tests for backend/auth/auth_jwt.py (JWT token creation and decoding)."""

import json
import time

import pytest

# RFC 7518 要求 HS256 密钥 ≥32 字节；短密钥会触发 PyJWT InsecureKeyLengthWarning
TEST_SECRET = "unit-test-secret-0123456789abcdef-0123456789abcdef"


@pytest.mark.requirement("REQ-AUTH-004")
class TestCreateToken:
    def test_returns_valid_jwt_string(self):
        from auth.auth_jwt import create_token

        token = create_token("user-1", TEST_SECRET, ttl=3600)
        parts = token.split(".")
        assert len(parts) == 3
        assert all(isinstance(p, str) and len(p) > 0 for p in parts)

    def test_token_contains_user_id(self):
        from auth.auth_jwt import create_token, decode_jwt

        token = create_token("alice", TEST_SECRET, ttl=3600)
        payload = decode_jwt(token, TEST_SECRET)
        assert payload is not None
        assert payload["sub"] == "alice"


@pytest.mark.requirement("REQ-AUTH-004")
class TestDecodeJWT:
    def test_valid_token(self):
        from auth.auth_jwt import create_token, decode_jwt

        token = create_token("bob", TEST_SECRET, ttl=3600)
        payload = decode_jwt(token, TEST_SECRET)
        assert payload is not None
        assert payload["sub"] == "bob"
        assert "exp" in payload
        assert "iat" in payload

    def test_expired_token_returns_none(self):
        from auth.auth_jwt import create_token, decode_jwt

        token = create_token("bob", TEST_SECRET, ttl=-1)

        payload = decode_jwt(token, TEST_SECRET)
        assert payload is None

    def test_wrong_secret_returns_none(self):
        from auth.auth_jwt import create_token, decode_jwt

        token = create_token("bob", TEST_SECRET, ttl=3600)
        payload = decode_jwt(token, f"{TEST_SECRET}-wrong")
        assert payload is None

    def test_empty_secret_returns_none(self):
        from auth.auth_jwt import decode_jwt

        payload = decode_jwt("some.token.here", "")
        assert payload is None

    def test_malformed_token_returns_none(self):
        from auth.auth_jwt import decode_jwt

        payload = decode_jwt("not-a-valid-token", TEST_SECRET)
        assert payload is None

    def test_tampered_payload_returns_none(self):
        from auth.auth_jwt import create_token, decode_jwt

        token = create_token("alice", TEST_SECRET, ttl=3600)
        parts = token.split(".")
        tampered = f"{parts[0]}.{parts[1]}.invalidsig"
        payload = decode_jwt(tampered, TEST_SECRET)
        assert payload is None

    def test_base64url_decode_pads_correctly(self):
        from auth.auth_jwt import _base64url_decode

        result = _base64url_decode("eyJzdWIiOiAidGVzdCJ9")
        assert json.loads(result) == {"sub": "test"}

    def test_simplified_token_format(self):
        from auth.auth_jwt import decode_jwt

        now = int(time.time())
        raw = f"testuser:{now}:abcdef1234567890"
        import base64

        token = base64.urlsafe_b64encode(raw.encode()).rstrip(b"=").decode()
        payload = decode_jwt(token, "some_secret")
        assert payload is None  # Wrong signature

    def test_simplified_token_expired(self):
        from auth.auth_jwt import decode_jwt

        past = int(time.time()) - 90000
        import base64
        import hashlib
        import hmac

        raw = f"testuser:{past}"
        sig = hmac.new(b"secret", raw.encode(), hashlib.sha256).hexdigest()[:16]
        token = base64.urlsafe_b64encode(f"{raw}:{sig}".encode()).rstrip(b"=").decode()
        payload = decode_jwt(token, "secret")
        assert payload is None

    def test_simplified_token_valid(self):
        """Create a valid simplified token and verify it decodes correctly."""
        import base64
        import hashlib
        import hmac

        from auth.auth_jwt import decode_jwt

        now = int(time.time())
        raw = f"testuser:{now}"
        sig = hmac.new(b"secret", raw.encode(), hashlib.sha256).hexdigest()[:16]
        token = base64.urlsafe_b64encode(f"{raw}:{sig}".encode()).rstrip(b"=").decode()
        payload = decode_jwt(token, "secret")
        assert payload is not None
        assert payload["sub"] == "testuser"

    def test_simplified_token_malformed_base64(self):
        """Malformed base64 in simplified token returns None."""
        from auth.auth_jwt import decode_jwt
        # Non-base64 string that can't be decoded
        payload = decode_jwt("!!!not@base64!!!", "secret")
        assert payload is None

    def test_decode_jwt_exception_catch_all(self):
        """The catch-all except branch handles unexpected errors gracefully."""
        # A token that causes json.loads to fail on valid-looking base64
        import base64

        from auth.auth_jwt import decode_jwt
        bad_payload = base64.urlsafe_b64encode(b"{not json}").rstrip(b"=").decode()
        bad_token = f"e30.{bad_payload}.e30"
        payload = decode_jwt(bad_token, TEST_SECRET)
        assert payload is None

    def test_token_missing_exp_claim_rejected(self):
        """缺少 exp 声明的令牌必须被拒（decode 侧 require=["exp"] 强制）。"""
        import jwt
        from auth.auth_jwt import decode_jwt
        token = jwt.encode({"sub": "no-exp"}, TEST_SECRET, algorithm="HS256")
        assert decode_jwt(token, TEST_SECRET) is None

    def test_base64url_decode_different_paddings(self):
        """Test base64url_decode with 0, 1, 2 padding chars needed."""
        import base64

        from auth.auth_jwt import _base64url_decode

        # No padding needed (len divisible by 4)
        data = base64.urlsafe_b64encode(b"abcd").rstrip(b"=").decode()
        assert _base64url_decode(data) == b"abcd"

        # 1 padding needed
        data = base64.urlsafe_b64encode(b"abcde").rstrip(b"=").decode()
        assert _base64url_decode(data) == b"abcde"

        # 2 padding needed
        data = base64.urlsafe_b64encode(b"abcdef").rstrip(b"=").decode()
        assert _base64url_decode(data) == b"abcdef"

    def test_create_token_custom_ttl(self):
        from auth.auth_jwt import create_token, decode_jwt
        token = create_token("u1", TEST_SECRET, ttl=7200)
        payload = decode_jwt(token, TEST_SECRET)
        assert payload is not None
        expected_exp = payload["iat"] + 7200
        assert abs(payload["exp"] - expected_exp) <= 1

    def test_rejects_header_alg_forgery(self):
        """Header alg: none 篡改必须被拒（PyJWT algorithms 强制校验）。"""
        import base64
        import json

        from auth.auth_jwt import create_token, decode_jwt

        tok = create_token("u1", TEST_SECRET)
        _, payload, sig = tok.split(".")
        forged_header = base64.urlsafe_b64encode(
            json.dumps({"alg": "none", "typ": "JWT"}).encode()
        ).rstrip(b"=").decode()
        forged = f"{forged_header}.{payload}.{sig}"
        assert decode_jwt(forged, TEST_SECRET) is None


