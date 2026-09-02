"""Tests for require_role() — RBAC role-checking dependency factory."""

from __future__ import annotations

import pytest
from auth.auth_rbac import CurrentUser, require_role
from fastapi import HTTPException


def _make_user(roles: list[str] | None = None) -> CurrentUser:
    return CurrentUser(id="u1", username="tester", email="t@t.com", roles=roles or ["member"])


class TestRequireRoleReturnsCallable:
    """require_role(*names) returns a dependency callable, not a result."""

    def test_returns_callable(self):
        dep = require_role("admin")
        assert callable(dep)

    def test_multiple_names(self):
        dep = require_role("admin", "manager", "editor")
        assert callable(dep)



class TestRBACMode:
    """In RBAC mode, role checks are enforced."""

    def test_matching_role_passes(self):
        checker = require_role("admin")
        user = _make_user(["admin"])
        result = checker(current_user=user)
        assert result is user

    def test_no_matching_role_raises_403(self):
        checker = require_role("admin")
        user = _make_user(["member"])
        with pytest.raises(HTTPException) as exc:
            checker(current_user=user)
        assert exc.value.status_code == 403
        assert "Insufficient role" in exc.value.detail

    def test_any_of_multiple_roles_passes(self):
        checker = require_role("admin", "manager", "editor")
        user = _make_user(["editor"])
        result = checker(current_user=user)
        assert result is user

    def test_multiple_roles_none_match_raises_403(self):
        checker = require_role("admin", "manager")
        user = _make_user(["viewer", "guest"])
        with pytest.raises(HTTPException) as exc:
            checker(current_user=user)
        assert exc.value.status_code == 403

    def test_user_with_multiple_roles_one_match_passes(self):
        checker = require_role("admin")
        user = _make_user(["member", "admin", "viewer"])
        result = checker(current_user=user)
        assert result is user

    def test_first_role_matches(self):
        """OR semantics: first listed role matches."""
        checker = require_role("viewer", "admin")
        user = _make_user(["viewer"])
        result = checker(current_user=user)
        assert result is user

    def test_second_role_matches(self):
        """OR semantics: second listed role matches."""
        checker = require_role("admin", "viewer")
        user = _make_user(["viewer"])
        result = checker(current_user=user)
        assert result is user
