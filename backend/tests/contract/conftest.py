"""Contract test fixtures — shared HTTP client for integration contract testing."""

from __future__ import annotations

import os
from typing import Any

import httpx
import pytest

#: ragbase 后端实际监听端口（systemd，见 AGENTS.md 端口表）。
BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8081")

CONTRACT_EMAIL = "admin@example.com"
CONTRACT_PASSWORD = "admin123"

_TOKEN_CACHE: str | None = None


@pytest.fixture
async def contract_client() -> Any:
    """httpx.AsyncClient pointing at the local backend (live HTTP).

    Function-scoped: pytest-asyncio runs each test on its own event loop,
    so a session-scoped async client would be finalized on a closed loop
    ("Event loop is closed" teardown error).

    The Bearer token is obtained once per session and cached — contract
    tests must not login per test (live rate limiter would 429 the run).
    """
    token: str | None = _obtain_token()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        if token:
            client.headers.update({"Authorization": f"Bearer {token}"})
        yield client


def _obtain_token() -> str | None:
    """Login as the seeded admin (rbac mode); cache the token per session."""
    global _TOKEN_CACHE
    if _TOKEN_CACHE is not None:
        return _TOKEN_CACHE

    try:
        resp = httpx.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": CONTRACT_EMAIL, "password": CONTRACT_PASSWORD},
            timeout=5,
        )
        if resp.status_code == 200:
            _TOKEN_CACHE = resp.json().get("access_token")
            return _TOKEN_CACHE
    except Exception:
        pass

    _TOKEN_CACHE = ""
    return None
