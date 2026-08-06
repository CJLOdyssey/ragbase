"""Providers image capability assertions."""

import pytest
from routers.providers import PROVIDERS, Capability


@pytest.mark.unit
def test_image_capability_is_valid_literal() -> None:
    cap: Capability = "image"
    assert cap in {"llm", "embedding", "image"}


@pytest.mark.unit
def test_providers_declare_image_capability() -> None:
    assert "image" in PROVIDERS["openai"]["capabilities"]
    assert "image" in PROVIDERS["dashscope"]["capabilities"]


@pytest.mark.unit
def test_stability_provider_registered() -> None:
    assert PROVIDERS["stability"]["base_url"] == "https://api.stability.ai"
    assert "image" in PROVIDERS["stability"]["capabilities"]
