from unittest.mock import AsyncMock, patch


class TestModels:

    def test_list_models(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_models_from_keys(self, client):
        with patch("routers.models.get_api_keys", new_callable=AsyncMock) as mock_keys:
            mock_keys.return_value = [
                {"is_active": True, "provider": "openai", "models": ["gpt-4", "gpt-3.5-turbo"]},
                {"is_active": False, "provider": "deepseek", "models": ["deepseek-chat"]},
                {"is_active": True, "provider": "unknown", "models": ["custom-model"]},
            ]
            resp = client.get("/api/models")
            assert resp.status_code == 200
            data = resp.json()
            ids = [m["id"] for m in data]
            assert "gpt-4" in ids
            assert "gpt-3.5-turbo" in ids
            assert "custom-model" in ids
            assert "deepseek-chat" not in ids

    def test_models_dedup(self, client):
        with patch("routers.models.get_api_keys", new_callable=AsyncMock) as mock_keys:
            mock_keys.return_value = [
                {"is_active": True, "provider": "openai", "models": ["gpt-4"]},
                {"is_active": True, "provider": "custom", "models": ["gpt-4"]},
            ]
            resp = client.get("/api/models")
            data = resp.json()
            assert len(data) == 1

    def test_models_error(self, client):
        with patch("routers.models.get_api_keys", new_callable=AsyncMock, side_effect=Exception("error")):
            resp = client.get("/api/models")
            assert resp.status_code == 200
            assert resp.json() == []
