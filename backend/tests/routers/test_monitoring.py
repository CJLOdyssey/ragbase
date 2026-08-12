"""Quality monitoring API route tests (in-memory sqlite + TestClient).

Uses the shared routers/conftest.py fixtures: autouse _reset_db (clean schema
per test) and client (TestClient + redis mock + legacy auth). Legacy mode with
no X-User-ID header resolves ownership to ``anonymous``, so seeds use that id.
"""

import pytest

pytestmark = pytest.mark.unit

from datetime import UTC, datetime

from core.infra.database import FeedbackLog, RetrievalLogDB, get_session_factory

OWNER = "anonymous"


async def _seed_row(user_id: str, latency_ms: int, hit_count: int) -> None:
    factory = get_session_factory()
    async with factory() as session:
        session.add(
            RetrievalLogDB(
                user_id=user_id,
                query="q",
                latency_ms=latency_ms,
                hit_count=hit_count,
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()


async def _seed_feedback(user_id: str, rating: str) -> None:
    factory = get_session_factory()
    async with factory() as session:
        session.add(
            FeedbackLog(
                run_id="r1",
                user_id=user_id,
                rating=rating,
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()


class TestMonitoringRoutes:

    def test_summary_empty(self, client):
        resp = client.get("/api/monitoring/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["window_hours"] == 24
        assert data["retrieval"]["total"] == 0
        assert data["feedback"]["good_ratio"] is None
        assert data["alerts"] == []

    def test_summary_with_data_and_alert(self, client):
        for lat, hits in [(100, 3), (200, 0), (300, 1), (400, 2)]:
            client.portal.call(_seed_row, OWNER, lat, hits)
        client.portal.call(_seed_feedback, OWNER, "good")
        client.portal.call(_seed_feedback, OWNER, "bad")

        resp = client.get(
            "/api/monitoring/summary",
            params={"max_empty_recall_pct": 10, "max_p95_latency_ms": 300},
        )
        data = resp.json()
        assert data["retrieval"]["total"] == 4
        assert data["retrieval"]["empty_recall_rate"] == 0.25
        assert data["retrieval"]["latency_p95_ms"] == 400
        assert data["feedback"]["good_ratio"] == 0.5
        codes = [a["code"] for a in data["alerts"]]
        assert "empty_recall_high" in codes
        assert "p95_latency_high" in codes

    def test_summary_scoped_to_current_user(self, client):
        client.portal.call(_seed_row, "other", 999, 0)
        resp = client.get("/api/monitoring/summary")
        assert resp.status_code == 200
        assert resp.json()["retrieval"]["total"] == 0

    def test_validation_rejects_bad_window(self, client):
        resp = client.get("/api/monitoring/summary", params={"window_hours": 0})
        assert resp.status_code == 422
