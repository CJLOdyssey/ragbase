"""Runs router tests — merged from test_coverage_boost, test_coverage_gaps, test_remaining_coverage."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit



class TestRuns:
    """Merged: TestRuns + TestRunsGaps + TestRunsRemainingGaps."""

    # ── Create run ───────────────────────────────────────────────────────

    def test_create_run_empty_requirement(self, client):
        resp = client.post("/api/runs", json={"requirement": ""}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 422

    def test_create_run_whitespace_only(self, client):
        resp = client.post("/api/runs", json={"requirement": "   "}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 400

    def test_create_run_max_length(self, client):
        resp = client.post("/api/runs", json={
            "requirement": "x" * 20000
        }, headers={"X-User-ID": "admin"})
        assert resp.status_code == 422

    @patch("routers.runs.load_config")
    def test_create_run_max_config_length(self, mock_config, client):
        mock_cfg = MagicMock()
        mock_cfg.max_requirement_length = 10
        mock_config.return_value = mock_cfg
        resp = client.post("/api/runs", json={
            "requirement": "x" * 20
        }, headers={"X-User-ID": "admin"})
        assert resp.status_code == 400

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_create_run_success(self, mock_service, client):
        mock_service.create_run = AsyncMock(return_value={
            "run_id": "r-1", "status": "running", "session_id": "s-1",
        })
        resp = client.post("/api/runs", json={"requirement": "build a website"}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == "r-1"
        assert data["status"] == "running"

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_create_run_value_error(self, mock_service, client):
        mock_service.create_run = AsyncMock(side_effect=ValueError("bad input"))
        resp = client.post("/api/runs", json={"requirement": "test"}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 400

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_create_run_http_exception_reraise(self, mock_service, client):
        from fastapi import HTTPException
        mock_service.create_run = AsyncMock(side_effect=HTTPException(status_code=400, detail="bad"))
        resp = client.post("/api/runs", json={"requirement": "test"}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 400

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_create_run_generic_error(self, mock_service, client):
        mock_service.create_run = AsyncMock(side_effect=RuntimeError("something broke"))
        resp = client.post("/api/runs", json={"requirement": "test"}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 500

    # ── Get run detail ───────────────────────────────────────────────────

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_get_run_detail_found(self, mock_service, client):
        mock_service.get_run = AsyncMock(return_value={
            "id": "r-1", "requirement": "test", "status": "converged",
            "session_id": "s-1", "messages": [],
        })
        resp = client.get("/api/runs/r-1")
        assert resp.status_code == 200

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_get_run_detail_not_found(self, mock_service, client):
        mock_service.get_run = AsyncMock(return_value=None)
        resp = client.get("/api/runs/nonexistent")
        assert resp.status_code == 404

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_get_run_detail_http_exception(self, mock_service, client):
        from fastapi import HTTPException
        mock_service.get_run = AsyncMock(side_effect=HTTPException(status_code=404, detail="not found"))
        resp = client.get("/api/runs/notfound")
        assert resp.status_code == 404

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_get_run_detail_error(self, mock_service, client):
        mock_service.get_run = AsyncMock(side_effect=RuntimeError("db error"))
        resp = client.get("/api/runs/r-error")
        assert resp.status_code == 500

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_get_run_detail_scoped_to_caller(self, mock_service, client):
        """GET /runs/{id} 必须携带调用者身份 → 服务层归属校验 (BOLA 防护)。"""
        mock_service.get_run = AsyncMock(return_value={
            "id": "r-1", "requirement": "test", "status": "converged",
            "session_id": "s-1", "messages": [],
        })
        resp = client.get("/api/runs/r-1")
        assert resp.status_code == 200
        assert mock_service.get_run.await_args.args[1] == "admin-login"

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_list_runs_scoped_to_caller(self, mock_service, client):
        """GET /runs 列表必须按调用者归属过滤，不再返回全局 runs。"""
        mock_service.list_runs = AsyncMock(return_value=[])
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        assert mock_service.list_runs.await_args.kwargs["user_id"] == "admin-login"

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_cancel_run_not_owner_returns_404(self, mock_service, client):
        """非本人 run 取消 → 服务层回 not_found → 404（不泄露存在性）。"""
        mock_service.cancel_run = AsyncMock(return_value={
            "run_id": "r-other", "status": "not_found", "cancelled": False,
        })
        resp = client.post("/api/runs/r-other/cancel")
        assert resp.status_code == 404

    # ── List runs ────────────────────────────────────────────────────────

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_list_runs_success(self, mock_service, client):
        mock_service.list_runs = AsyncMock(return_value=[
            {"id": "r-1", "requirement": "t1", "status": "converged", "session_id": "s1"},
        ])
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_list_runs_error(self, mock_service, client):
        mock_service.list_runs = AsyncMock(side_effect=RuntimeError("error"))
        resp = client.get("/api/runs")
        assert resp.status_code == 500

    @patch("routers.runs.run_service", new_callable=MagicMock)
    def test_list_runs_exception(self, mock_service, client):
        mock_service.list_runs = AsyncMock(side_effect=RuntimeError("db error"))
        resp = client.get("/api/runs?limit=10")
        assert resp.status_code == 500

    # ── Model tests ──────────────────────────────────────────────────────

    def test_run_request_validation(self):
        from routers.runs import RunRequest
        req = RunRequest(requirement="hello")
        assert req.requirement == "hello"
        assert req.session_id is None

    def test_run_request_camel_case_aliases(self):
        from routers.runs import RunRequest
        req = RunRequest(requirement="test", sessionId="s1", keyId="k1")
        assert req.session_id == "s1"
        assert req.key_id == "k1"

    def test_run_response_model(self):
        from routers.runs import RunResponse
        resp = RunResponse(run_id="r1", status="running")
        assert resp.run_id == "r1"

    def test_run_response_optional_fields(self):
        from routers.runs import RunResponse
        resp = RunResponse(run_id="r1", status="running", session_id="s1")
        assert resp.session_id == "s1"
