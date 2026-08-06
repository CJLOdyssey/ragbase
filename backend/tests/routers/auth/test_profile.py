"""Profile tests — split from test_routers_auth.py."""

from unittest.mock import AsyncMock, MagicMock, patch


class TestAuthProfile:
    """Profile-related tests from coverage_boost."""

    def test_auth_config(self, client):
        resp = client.get("/api/auth/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "mode" in data

    def test_me(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "email" in data
        assert "roles" in data

    def test_me_user_not_found(self, client):
        with patch("routers.auth.profile.get_user_by_email", new_callable=AsyncMock, return_value=None), \
             patch("routers.auth.profile.get_user_by_id", new_callable=AsyncMock, return_value=None):
            resp = client.get("/api/auth/me")
            assert resp.status_code == 404

    def test_me_fallback_to_id(self, client):
        mock_user = MagicMock()
        mock_user.id = "u1"
        mock_user.email = "test@test.com"
        mock_user.username = "test"
        mock_user.is_verified = True
        with patch("routers.auth.profile.get_user_by_email", new_callable=AsyncMock, return_value=None), \
             patch("routers.auth.profile.get_user_by_id", new_callable=AsyncMock, return_value=mock_user), \
             patch("routers.auth.profile.get_user_roles", new_callable=AsyncMock, return_value=["admin"]):
            resp = client.get("/api/auth/me")
            assert resp.status_code == 200

    def test_merge_guest_data(self, client):
        with patch("routers.auth.profile._merge_guest_data", new_callable=AsyncMock):
            resp = client.post("/api/auth/merge", json={"guest_id": "guest-123"})
            assert resp.status_code == 200
            assert resp.json()["status"] == "merged"

    def test_merge_guest_data_with_x_user_id(self, client):
        with patch("routers.auth.profile._merge_guest_data", new_callable=AsyncMock) as mock_merge:
            resp = client.post("/api/auth/merge", json={"guest_id": "guest-456"},
                               headers={"X-User-ID": "header-id"})
            assert resp.status_code == 200
            mock_merge.assert_called_once()
            call_args = mock_merge.call_args
            ids = call_args[0][0]
            assert "guest-456" in ids
            assert "header-id" in ids
            assert "anonymous" in ids
