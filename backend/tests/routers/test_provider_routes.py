
import pytest

pytestmark = pytest.mark.unit



class TestProviderRoutes:

    def test_list_providers(self, client):
        resp = client.get("/api/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert "openai" in data
        assert "deepseek" in data
        assert "anthropic" in data
        assert "dashscope" in data
        assert "custom_llm" in data

    def test_list_providers_has_capabilities(self, client):
        resp = client.get("/api/providers")
        data = resp.json()
        for _provider_name, provider_info in data.items():
            assert "name" in provider_info
            assert "capabilities" in provider_info
            assert isinstance(provider_info["capabilities"], list)

    def test_openai_has_chat_and_vector(self, client):
        resp = client.get("/api/providers")
        data = resp.json()
        caps = data["openai"]["capabilities"]
        assert "chat" in caps
        assert "vector" in caps

    def test_deepseek_only_chat(self, client):
        resp = client.get("/api/providers")
        data = resp.json()
        caps = data["deepseek"]["capabilities"]
        assert "chat" in caps
        assert "vector" not in caps

    def test_provider_has_base_url(self, client):
        resp = client.get("/api/providers")
        data = resp.json()
        assert data["openai"]["base_url"] == "https://api.openai.com/v1"
        assert data["deepseek"]["base_url"] == "https://api.deepseek.com/v1"
        assert data["zhipu"]["base_url"] == "https://open.bigmodel.cn/api/paas/v4"
        assert data["siliconflow"]["base_url"] == "https://api.siliconflow.cn/v1"
