"""Keys API router tests — capabilities multi-value contract."""


def test_add_key_rejects_unknown_capability(client):
    resp = client.post(
        "/api/keys",
        json={
            "provider": "openai",
            "capabilities": ["llm", "general"],
            "label": "bad",
            "api_key": "sk-test",
            "models": [],
            "is_default": False,
        },
    )
    assert resp.status_code == 422
