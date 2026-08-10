"""Model type inference — heuristic classification of model ids by name.

Pure functions with no repository/router dependencies, shared by the models
route and key-connectivity classification.
"""

EMBEDDING_PREFIXES = ("text-embedding", "embedding", "bge-", "m3e-", "jina-embeddings")
RERANK_PREFIXES = ("rerank", "bge-reranker")


def infer_model_type(model: str, provider: str) -> str:
    m = model.lower()
    # Match on the basename (after org/namespace prefix like "BAAI/"), since
    # real model ids carry a prefix (e.g. "BAAI/bge-m3") that would otherwise
    # defeat startswith checks. Substring checks ("embed", "asr") stay on the
    # full name to avoid over-matching vendor names.
    base = m.rsplit("/", 1)[-1]
    if base.startswith(EMBEDDING_PREFIXES) or "embed" in m:
        return "embedding"
    if base.startswith(RERANK_PREFIXES) or "rerank" in m:
        return "rerank"
    if base.startswith(("whisper", "paraformer", "sherpa")) or "asr" in m:
        return "speech2text"
    if base.startswith(("tts", "edge-tts")) or "voice" in m:
        return "tts"
    if "moderation" in m:
        return "moderation"
    if provider in ("tavily", "stability"):
        return "tool"
    return "llm"
