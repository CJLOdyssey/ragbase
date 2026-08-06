import pytest
pytestmark = pytest.mark.integration

"""E2E Test: Session + Run operations."""

from tests.conftest import Api, _cleanup


class TestSessionAndRun:
    def test_create_session(self, api: Api):

        r = api.post("/api/sessions", json={"title": "E2E-Session"})
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["title"] == "E2E-Session"
        _cleanup((body["id"], "/api/sessions"))

    def test_list_sessions(self, api: Api):
        r = api.get("/api/sessions")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_get_session_detail(self, api: Api):

        r = api.post("/api/sessions", json={"title": "Detail-Test"})
        assert r.status_code == 201, r.text
        sid = r.json()["id"]
        r2 = api.get(f"/api/sessions/{sid}")
        assert r2.status_code == 200
        body = r2.json()
        assert body["id"] == sid
        assert "runs" in body
        _cleanup((sid, "/api/sessions"))
