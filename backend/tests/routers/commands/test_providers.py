class TestProviders:

    def test_list_providers(self, client):
        resp = client.get("/api/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert "openai" in data
        assert "deepseek" in data
        assert "anthropic" in data
        assert "dashscope" in data
        assert "custom_llm" in data
        assert "custom_embedding" in data

    def test_test_provider(self, client):
        resp = client.post("/api/providers/test", json={
            "provider": "openai", "api_key": "sk-test",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_provider_capabilities(self, client):
        resp = client.get("/api/providers")
        data = resp.json()
        assert "chat" in data["openai"]["capabilities"]
        assert "vector" in data["openai"]["capabilities"]
        assert "chat" in data["deepseek"]["capabilities"]
