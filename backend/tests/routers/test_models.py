"""Models API router tests — capability type inference.

Each DB-backed test runs under its own X-User-ID so keys created by one test
can never leak into another (the router-level in-memory SQLite engine is
shared per xdist worker; _reset_db isolation must not be relied on).
"""


def test_model_type_inference():
    from routers.models import infer_model_type

    assert infer_model_type("text-embedding-3-small", "openai") == "embedding"
    assert infer_model_type("bge-large-zh", "ollama") == "embedding"
    assert infer_model_type("rerank-multilingual-v3", "cohere") == "rerank"
    assert infer_model_type("gpt-4o", "openai") == "llm"
    assert infer_model_type("", "tavily") == "tool"


def test_model_type_inference_with_org_prefix():
    from routers.models import infer_model_type

    assert infer_model_type("BAAI/bge-m3", "custom") == "embedding"
    assert infer_model_type("Pro/BAAI/bge-m3", "custom") == "embedding"
    assert infer_model_type("Qwen/Qwen3-Reranker-8B", "custom") == "rerank"
    assert infer_model_type("zai-org/GLM-5.2", "custom") == "llm"


def _create_key(client, *, models, model_types=None, label="models-test", user):
    resp = client.post(
        "/api/keys",
        headers={"X-User-ID": user},
        json={
            "provider": "custom",
            "capabilities": ["llm"],
            "label": label,
            "api_key": "sk-test",
            "models": models,
            "is_default": False,
            **({"model_types": model_types} if model_types is not None else {}),
        },
    )
    assert resp.status_code == 201
    return resp.json()


def _model_types_by_id(client, user):
    resp = client.get("/api/models", headers={"X-User-ID": user})
    assert resp.status_code == 200
    return {m["id"]: m["type"] for m in resp.json()}


def test_models_uses_stored_type_over_heuristic(client):
    # gpt-4o would heuristically infer "llm", but the stored map says embedding.
    _create_key(client, models=["gpt-4o"], model_types={"gpt-4o": "embedding"}, user="models-stored")
    assert _model_types_by_id(client, "models-stored")["gpt-4o"] == "embedding"


def test_models_heuristic_without_model_types(client):
    _create_key(client, models=["gpt-4o"], user="models-heuristic")
    assert _model_types_by_id(client, "models-heuristic")["gpt-4o"] == "llm"
    _create_key(client, models=["text-embedding-3-small"], label="models-test-2", user="models-heuristic")
    assert _model_types_by_id(client, "models-heuristic")["text-embedding-3-small"] == "embedding"


def test_models_ignores_stored_type_for_unknown_model(client):
    # model_types entry whose model is not in the key's models list must not
    # crash and must not affect listed models.
    _create_key(client, models=["gpt-4o"], model_types={"other-model": "rerank"}, user="models-ignores")
    assert _model_types_by_id(client, "models-ignores")["gpt-4o"] == "llm"
