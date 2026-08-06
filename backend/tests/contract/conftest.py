"""Contract test fixtures — shared HTTP client for integration contract testing."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

BASE_URL = "http://localhost:8080"


@pytest.fixture(scope="session")
async def contract_client() -> Any:
    """Session-scoped httpx.AsyncClient pointing at the local backend.

    Unlike the root conftest's ``test_client`` (which uses ASGI transport
    directly), this fixture connects via real HTTP — suitable for contract
    tests that verify responses over the wire.

    Auth token is obtained once per session and cached on the client.
    """
    token: str | None = _obtain_token()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        if token:
            client.headers.update({"Authorization": f"Bearer {token}"})
        yield client


def _obtain_token() -> str | None:
    """Obtain a Bearer token. Falls back to legacy login."""
    try:
        resp = httpx.get(
            f"{BASE_URL}/api/auth/config",
            timeout=5,
        )
        cfg = resp.json() if resp.status_code == 200 else {}
    except Exception:
        cfg = {}

    if cfg.get("mode") == "rbac":
        # In rbac mode, registration flow may be needed — skip for contract tests
        return None

    try:
        resp = httpx.post(
            f"{BASE_URL}/api/auth/login",
            json={
                "username": "admin",
                "password": "admin123",
            },
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception:
        pass

    return None
