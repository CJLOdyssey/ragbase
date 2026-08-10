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


def test_key_list_returns_model_types(client):
    created = client.post(
        "/api/keys",
        json={
            "provider": "custom",
            "capabilities": ["llm"],
            "label": "types",
            "api_key": "sk-test",
            "models": ["gpt-4o"],
            "model_types": {"gpt-4o": "embedding"},
            "is_default": False,
        },
    )
    assert created.status_code == 201

    resp = client.get("/api/keys")
    assert resp.status_code == 200
    row = next(k for k in resp.json() if k["label"] == "types")
    assert row["model_types"] == {"gpt-4o": "embedding"}
