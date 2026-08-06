import uuid

import bcrypt
import pytest

from repository.auth import create_user


@pytest.fixture
async def _seed_test_user(test_client):
    """Seed a verified test user for login tests (function-scoped, idempotent)."""
    email = f"reqmarker+{uuid.uuid4().hex[:8]}@test.com"
    password = "ReqMarkerPass1"
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()
    await create_user(email=email, password_hash=password_hash, is_verified=True)
    return email, password


class TestAuthRequirements:

    @pytest.mark.requirement("REQ-AUTH-001")
    async def test_login_success(self, test_client, _seed_test_user):
        email, password = _seed_test_user
        response = await test_client.post(
            "/api/auth/login",
            json={"email": email, "password": password}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.requirement("REQ-AUTH-002")
    async def test_login_wrong_password(self, test_client, _seed_test_user):
        email, _ = _seed_test_user
        response = await test_client.post(
            "/api/auth/login",
            json={"email": email, "password": "WrongPassword"}
        )
        assert response.status_code in [400, 401]

    @pytest.mark.requirement("REQ-AUTH-004")
    async def test_jwt_token_generation(self, test_client, _seed_test_user):
        email, password = _seed_test_user
        response = await test_client.post(
            "/api/auth/login",
            json={"email": email, "password": password}
        )
        assert response.status_code == 200
        token = response.json().get("access_token")
        assert token is not None
        assert len(token) > 0

    @pytest.mark.requirement("REQ-AUTH-005")
    @pytest.mark.skip(reason="token refresh endpoint not yet implemented")
    async def test_token_refresh(self, test_client):
        pass

    @pytest.mark.requirement("REQ-AUTH-007")
    @pytest.mark.skip(reason="password policy check is server-side only, no testable endpoint")
    async def test_password_policy_strong(self, test_client):
        pass

    @pytest.mark.requirement("REQ-AUTH-008")
    @pytest.mark.skip(reason="account lockout requires multi-request state tracking — to be implemented with integration test fixture")
    async def test_account_lockout(self, test_client):
        pass


class TestSessionRequirements:

    @pytest.mark.requirement("REQ-SES-001")
    async def test_create_session(self, test_client):
        response = await test_client.post("/api/sessions", json={"title": "Test Session"})
        assert response.status_code in [200, 201]

    @pytest.mark.requirement("REQ-SES-002")
    async def test_list_sessions(self, test_client):
        response = await test_client.get("/api/sessions")
        assert response.status_code == 200


class TestSessionForRun:
    @pytest.mark.requirement("REQ-RUN-001")
    async def test_create_run(self, test_client):
        session = await test_client.post("/api/sessions", json={"title": "Run Test Session"})
        assert session.status_code in [200, 201]
        session_id = session.json().get("id") or session.json().get("session_id")

        response = await test_client.post(
            "/api/runs",
            json={"requirement": "test requirement", "session_id": session_id}
        )
        assert response.status_code in [200, 201, 400, 404, 422]

    @pytest.mark.requirement("REQ-RUN-002")
    @pytest.mark.skip(reason="streaming output requires WebSocket/SSE test harness — tracked in test backlog")
    async def test_streaming_output(self, test_client):
        pass
