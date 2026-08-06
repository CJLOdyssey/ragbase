"""Schema tests — split from test_routers_auth.py."""


class TestAuthSchemas:
    """Schema-related tests from remaining_coverage."""

    def test_auth_config_endpoint(self, client):
        """Cover schemas auth config response."""
        resp = client.get("/api/auth/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "enabled" in data
        assert "mode" in data
