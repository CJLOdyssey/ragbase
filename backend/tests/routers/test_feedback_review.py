"""Bad-feedback review queue route tests (in-memory sqlite + TestClient)."""

import pytest

pytestmark = pytest.mark.unit

from datetime import UTC, datetime

from core.infra.database import FeedbackLog, get_session_factory

OWNER = "admin-login"


async def _seed_feedback(
    feedback_id: str,
    rating: str = "bad",
    user_id: str = OWNER,
) -> None:
    factory = get_session_factory()
    async with factory() as session:
        session.add(
            FeedbackLog(
                id=feedback_id,
                run_id=f"run-{feedback_id}",
                user_id=user_id,
                rating=rating,
                query="测试问题",
                answer="测试回答",
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()


class TestBadFeedbackQueue:

    def test_list_empty(self, client):
        resp = client.get("/api/monitoring/bad-feedback")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_lists_only_bad_and_owned(self, client):
        client.portal.call(_seed_feedback, "fb-1", "bad", OWNER)
        client.portal.call(_seed_feedback, "fb-2", "good", OWNER)
        client.portal.call(_seed_feedback, "fb-3", "bad", "someone-else")

        resp = client.get("/api/monitoring/bad-feedback")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert [i["feedbackId"] for i in items] == ["fb-1"]

    def test_review_upsert_flow(self, client):
        client.portal.call(_seed_feedback, "fb-1")

        resp = client.post(
            "/api/monitoring/bad-feedback/fb-1/review",
            json={
                "status": "resolved",
                "root_cause": "retrieval_miss",
                "note": "知识库缺该文档",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["root_cause"] == "retrieval_miss"

        # resolved 状态过滤可见；pending 过滤不可见
        pending = client.get(
            "/api/monitoring/bad-feedback", params={"status": "pending"}
        ).json()
        assert pending["total"] == 0
        resolved = client.get(
            "/api/monitoring/bad-feedback", params={"status": "resolved"}
        ).json()
        assert resolved["total"] == 1
        assert resolved["items"][0]["review"]["note"] == "知识库缺该文档"

    def test_cannot_review_good_rating_or_foreign_row(self, client):
        client.portal.call(_seed_feedback, "fb-good", "good", OWNER)
        client.portal.call(_seed_feedback, "fb-foreign", "bad", "other")

        for fid in ("fb-good", "fb-foreign"):
            resp = client.post(
                f"/api/monitoring/bad-feedback/{fid}/review",
                json={"status": "resolved"},
            )
            assert resp.status_code == 404

    def test_rejects_invalid_payloads(self, client):
        client.portal.call(_seed_feedback, "fb-1")
        bad_status = client.post(
            "/api/monitoring/bad-feedback/fb-1/review",
            json={"status": "nope"},
        )
        assert bad_status.status_code == 422
        bad_cause = client.post(
            "/api/monitoring/bad-feedback/fb-1/review",
            json={"status": "resolved", "root_cause": "made_up"},
        )
        assert bad_cause.status_code == 422
