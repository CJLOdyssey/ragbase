"""Key capability enumeration — single source of truth for the 8-type system.

Aligned with Dify ModelType (llm/text-embedding/rerank/speech2text/tts/moderation)
plus Tool (Dify plugin category) and a dedicated Image category (image generation
providers are tracked separately from tool providers).
"""

CAPABILITIES: tuple[str, ...] = (
    "llm",
    "embedding",
    "rerank",
    "speech2text",
    "tts",
    "moderation",
    "image",
    "tool",
)

VALID = frozenset(CAPABILITIES)

# Legacy single-value usage_type → capabilities mapping (migration only).
USAGE_TYPE_TO_CAPABILITIES: dict[str, list[str]] = {
    "chat": ["llm"],
    "vector": ["embedding"],
    "general": ["llm", "embedding"],
    "image": ["image"],
    "tool": ["tool"],
    "audio": [],
}


def validate_capabilities(caps: list[str]) -> str | None:
    """Return an error message for unknown capabilities, else None."""
    for c in caps:
        if c not in VALID:
            return f"未知能力: {c}"
    return None
