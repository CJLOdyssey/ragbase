"""Models API router tests — capability type inference."""


def test_model_type_inference():
    from routers.models import infer_model_type

    assert infer_model_type("text-embedding-3-small", "openai") == "embedding"
    assert infer_model_type("bge-large-zh", "ollama") == "embedding"
    assert infer_model_type("rerank-multilingual-v3", "cohere") == "rerank"
    assert infer_model_type("gpt-4o", "openai") == "llm"
    assert infer_model_type("", "tavily") == "tool"
