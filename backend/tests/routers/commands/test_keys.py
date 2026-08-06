from unittest.mock import AsyncMock, patch


class TestKeys:

    def test_list_keys(self, client):
        resp = client.get("/api/keys", headers={"X-User-ID": "admin"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_key_embedding_type(self, client):
        resp = client.post("/api/keys", json={
            "provider": "openai", "usage_type": "vector",
            "label": "emb-key", "api_key": "sk-emb-test",
        }, headers={"X-User-ID": "admin"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["provider"] == "openai"
        assert data["usage_type"] == "vector"

    def test_create_key_both_type(self, client):
        # usage_type != vector → hits test_api_key_connection (real network).
        # Mock it to avoid a 15s real connection attempt.
        with patch("routers.keys.test_api_key_connection", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": True, "models": ["gpt-4"]}
            resp = client.post("/api/keys", json={
                "provider": "openai", "usage_type": "general",
                "label": "both-key", "api_key": "sk-both-test",
            }, headers={"X-User-ID": "admin"})
        assert resp.status_code == 201
        assert resp.json()["usage_type"] == "general"

    def test_create_key_llm_type_success(self, client):
        with patch("routers.keys.test_api_key_connection", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": True, "models": ["gpt-4"]}
            resp = client.post("/api/keys", json={
                "provider": "openai", "usage_type": "chat",
                "label": "llm-key", "api_key": "sk-llm-test",
            }, headers={"X-User-ID": "admin"})
            assert resp.status_code == 201
            assert resp.json()["models"] == ["gpt-4"]

    def test_create_key_llm_type_test_fails(self, client):
        with patch("routers.keys.test_api_key_connection", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": False, "message": "connection refused"}
            resp = client.post("/api/keys", json={
                "provider": "openai", "usage_type": "chat",
                "label": "llm-key-fail", "api_key": "sk-llm-test",
            }, headers={"X-User-ID": "admin"})
            assert resp.status_code == 201

    def test_create_key_llm_type_no_models_fetched(self, client):
        with patch("routers.keys.test_api_key_connection", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": True, "models": []}
            resp = client.post("/api/keys", json={
                "provider": "openai", "usage_type": "chat",
                "label": "llm-key-no-models", "api_key": "sk-llm-test",
                "models": ["gpt-4"],
            }, headers={"X-User-ID": "admin"})
            assert resp.status_code == 201

    def test_create_key_empty_body(self, client):
        resp = client.post("/api/keys", json={}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 422

    def test_edit_key_not_found(self, client):
        with patch("routers.keys.update_api_key", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = None
            resp = client.put("/api/keys/nonexistent", json={"label": "updated"}, headers={"X-User-ID": "admin"})
            assert resp.status_code == 404

    def test_edit_key_success(self, client):
        result = {
            "id": "k1", "provider": "openai", "usage_type": "llm",
            "label": "key-1", "key_masked": "sk-...est",
            "base_url": None, "models": [], "is_active": True,
            "is_default": False, "last_used_at": None, "created_at": None,
        }
        with patch("routers.keys.update_api_key", new_callable=AsyncMock) as mock_update, \
             patch("routers.keys.log_audit", new_callable=AsyncMock):
            mock_update.return_value = result
            resp = client.put("/api/keys/k1", json={"label": "updated"}, headers={"X-User-ID": "admin"})
            assert resp.status_code == 200
            assert resp.json()["label"] == "key-1"

    def test_edit_key_revalidates_on_new_api_key(self, client):
        result = {
            "id": "k1", "provider": "openai", "usage_type": "llm",
            "label": "key-1", "key_masked": "sk-...est",
            "base_url": None, "models": [], "is_active": True,
            "is_default": False, "last_used_at": None, "created_at": None,
        }
        with patch("routers.keys.update_api_key", new_callable=AsyncMock) as mock_update, \
             patch("routers.keys.test_api_key_connection", new_callable=AsyncMock) as mock_test, \
             patch("routers.keys.log_audit", new_callable=AsyncMock):
            mock_update.return_value = result
            mock_test.return_value = {"success": True, "models": ["gpt-4"]}
            resp = client.put("/api/keys/k1", json={"api_key": "new-key"}, headers={"X-User-ID": "admin"})
            assert resp.status_code == 200

    def test_edit_key_revalidates_on_new_base_url(self, client):
        result = {
            "id": "k1", "provider": "openai", "usage_type": "llm",
            "label": "key-1", "key_masked": "sk-...est",
            "base_url": None, "models": [], "is_active": True,
            "is_default": False, "last_used_at": None, "created_at": None,
        }
        with patch("routers.keys.update_api_key", new_callable=AsyncMock) as mock_update, \
             patch("routers.keys.test_api_key_connection", new_callable=AsyncMock) as mock_test, \
             patch("routers.keys.log_audit", new_callable=AsyncMock):
            mock_update.return_value = result
            mock_test.return_value = {"success": False, "message": "fail"}
            resp = client.put("/api/keys/k1", json={"base_url": "https://new.api.com"}, headers={"X-User-ID": "admin"})
            assert resp.status_code == 200

    def test_delete_key_success(self, client):
        keys = [{"id": "k1", "label": "key-to-delete"}]
        with patch("routers.keys.get_api_keys", new_callable=AsyncMock) as mock_keys, \
             patch("routers.keys.delete_api_key", new_callable=AsyncMock) as mock_del, \
             patch("routers.keys.log_audit", new_callable=AsyncMock):
            mock_keys.return_value = keys
            mock_del.return_value = True
            resp = client.delete("/api/keys/k1", headers={"X-User-ID": "admin"})
            assert resp.status_code == 200

    def test_delete_key_not_found(self, client):
        with patch("routers.keys.get_api_keys", new_callable=AsyncMock) as mock_keys, \
             patch("routers.keys.delete_api_key", new_callable=AsyncMock) as mock_del:
            mock_keys.return_value = []
            mock_del.return_value = False
            resp = client.delete("/api/keys/nonexistent", headers={"X-User-ID": "admin"})
            assert resp.status_code == 404

    def test_test_key_connection_success(self, client):
        with patch("routers.keys.test_api_key_connection", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": True, "message": "OK"}
            resp = client.post("/api/keys/k1/test", headers={"X-User-ID": "admin"})
            assert resp.status_code == 200
            assert resp.json()["success"] is True

    def test_test_key_connection_failure(self, client):
        with patch("routers.keys.test_api_key_connection", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": False, "message": "Failed"}
            resp = client.post("/api/keys/k1/test", headers={"X-User-ID": "admin"})
            assert resp.status_code == 200
            assert resp.json()["success"] is False

    def test_fetch_models_from_provider_success(self, client):
        with patch("repository.keys._test_connection_sync") as mock_sync:
            mock_sync.return_value = {"success": True, "models": ["gpt-4"]}
            resp = client.post("/api/keys/fetch-models", json={
                "api_key": "sk-test", "provider": "openai",
            })
            assert resp.status_code == 200
            assert resp.json()["models"] == ["gpt-4"]

    def test_fetch_models_from_provider_failure(self, client):
        with patch("repository.keys._test_connection_sync") as mock_sync:
            mock_sync.return_value = {"success": False, "message": "Connection refused"}
            resp = client.post("/api/keys/fetch-models", json={
                "api_key": "sk-test", "provider": "openai",
            })
            assert resp.status_code == 200
            assert resp.json()["models"] == []
            assert "warning" in resp.json()

    def test_key_usage(self, client):
        with patch("routers.keys.get_key_usage_stats", new_callable=AsyncMock) as mock_stats:
            mock_stats.return_value = {"total_tokens": 1000, "total_cost": 0.5}
            resp = client.get("/api/keys/usage", headers={"X-User-ID": "admin"})
            assert resp.status_code == 200

    def test_key_usage_error(self, client):
        with patch("routers.keys.get_key_usage_stats", new_callable=AsyncMock) as mock_stats:
            mock_stats.side_effect = RuntimeError("db error")
            resp = client.get("/api/keys/usage", headers={"X-User-ID": "admin"})
            assert resp.status_code == 500


class TestKeysIntegration:
    """Integration tests: create key → list → verify persistence across requests."""

    USER_ID = "integration-test-user"
    X_USER_ID = "u_test_anonymous_xyz"

    def test_create_and_list_key(self, client):
        """POST /api/keys → 201 → GET /api/keys returns the created key."""
        with patch("routers.keys.test_api_key_connection", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": True, "models": ["gpt-4"]}
            create_resp = client.post("/api/keys", json={
                "provider": "openai",
                "usage_type": "chat",
                "label": "integration-key",
                "api_key": "sk-integration-test-12345",
            }, headers={"X-User-ID": self.USER_ID})
            assert create_resp.status_code == 201
            created = create_resp.json()
            assert created["provider"] == "openai"
            assert created["label"] == "integration-key"
            assert "..." in created["key_masked"]

        # Verify the key appears in the list (simulates page refresh)
        list_resp = client.get("/api/keys", headers={"X-User-ID": self.USER_ID})
        assert list_resp.status_code == 200
        keys = list_resp.json()
        key_ids = [k["id"] for k in keys]
        assert created["id"] in key_ids, (
            f"Created key {created['id']} not found in list: {key_ids}"
        )

    def test_create_key_then_list_with_different_user_shows_fallback(self, client):
        """Keys created under X-User-ID are visible when queried with a different
        user_id but the X-User-ID passed as fallback."""
        with patch("routers.keys.test_api_key_connection", new_callable=AsyncMock) as mock_test:
            mock_test.return_value = {"success": True, "models": ["gpt-4"]}
            create_resp = client.post("/api/keys", json={
                "provider": "openai",
                "usage_type": "chat",
                "label": "fallback-key",
                "api_key": "sk-fallback-test",
            }, headers={"X-User-ID": self.X_USER_ID})
            assert create_resp.status_code == 201
            created_id = create_resp.json()["id"]

        # Query with a different user_id but include X_USER_ID as fallback header
        list_resp = client.get("/api/keys", headers={
            "X-User-ID": self.X_USER_ID,
        })
        assert list_resp.status_code == 200
        keys = list_resp.json()
        key_ids = [k["id"] for k in keys]
        assert created_id in key_ids, (
            f"Key not found when queried with same X-User-ID: {key_ids}"
        )

    def test_create_multiple_keys_and_list_all(self, client):
        """Create 3 keys for the same user → list returns all."""
        ids = []
        for i, provider in enumerate(["openai", "deepseek", "anthropic"]):
            with patch("routers.keys.test_api_key_connection", new_callable=AsyncMock) as mock_test:
                mock_test.return_value = {"success": True, "models": [f"model-{i}"]}
                resp = client.post("/api/keys", json={
                    "provider": provider,
                    "usage_type": "chat",
                    "label": f"multi-key-{i}",
                    "api_key": f"sk-multi-{i}",
                }, headers={"X-User-ID": self.USER_ID})
                assert resp.status_code == 201
                ids.append(resp.json()["id"])

        list_resp = client.get("/api/keys", headers={"X-User-ID": self.USER_ID})
        assert list_resp.status_code == 200
        returned_ids = [k["id"] for k in list_resp.json()]
        for kid in ids:
            assert kid in returned_ids, f"Key {kid} missing after listing"
