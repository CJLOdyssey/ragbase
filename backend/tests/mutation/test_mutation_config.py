"""Verify mutmut (mutation testing) is available and configured.

The suite's mutation jobs (CI) rely on mutmut; a missing install or an
empty mutation config should fail loudly here rather than silently in CI.
"""


import pytest


def test_mutmut_installed():
    pytest.importorskip("mutmut", reason="mutmut not installed — mutation jobs unavailable")


def test_mutmut_importable():
    mutmut = pytest.importorskip("mutmut")
    assert hasattr(mutmut, "run"), "mutmut.run entry point missing"
