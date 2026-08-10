import pytest
from domain.capabilities import CAPABILITIES, USAGE_TYPE_TO_CAPABILITIES, validate_capabilities


def test_capabilities_enum_matches_spec():
    assert CAPABILITIES == (
        "llm", "embedding", "rerank", "speech2text", "tts", "moderation", "tool",
    )


@pytest.mark.parametrize(
    "caps,expected_error",
    [
        (["llm"], None),
        (["llm", "embedding", "tool"], None),
        ([], None),
        (["general"], "未知能力: general"),
        (["llm", "audio"], "未知能力: audio"),
    ],
)
def test_validate_capabilities(caps, expected_error):
    assert validate_capabilities(caps) == expected_error


def test_legacy_mapping():
    assert USAGE_TYPE_TO_CAPABILITIES["chat"] == ["llm"]
    assert USAGE_TYPE_TO_CAPABILITIES["vector"] == ["embedding"]
    assert USAGE_TYPE_TO_CAPABILITIES["general"] == ["llm", "embedding"]
    assert USAGE_TYPE_TO_CAPABILITIES["image"] == ["tool"]
    assert USAGE_TYPE_TO_CAPABILITIES["tool"] == ["tool"]
    assert USAGE_TYPE_TO_CAPABILITIES["audio"] == []
