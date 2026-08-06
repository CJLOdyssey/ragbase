from unittest.mock import AsyncMock, MagicMock, patch


class TestRunContinue:

    @patch("routers.run_continue.run_service", new_callable=MagicMock)
    def test_continue_run_success(self, mock_service, client):
        mock_service.continue_run = AsyncMock(return_value={
            "run_id": "r-1", "status": "running", "session_id": "s-1",
        })
        resp = client.post("/api/runs/complete", json={
            "content": "continue here", "session_id": "s-1",
        }, headers={"X-User-ID": "admin"})
        assert resp.status_code == 200
        assert resp.json()["run_id"] == "r-1"

    @patch("routers.run_continue.run_service", new_callable=MagicMock)
    def test_continue_run_empty_content(self, mock_service, client):
        mock_service.continue_run = AsyncMock(return_value={
            "run_id": "r-2", "status": "running",
        })
        resp = client.post("/api/runs/complete", json={
            "content": "", "session_id": "s-1",
        }, headers={"X-User-ID": "admin"})
        assert resp.status_code == 200

    @patch("routers.run_continue.run_service", new_callable=MagicMock)
    def test_continue_run_value_error(self, mock_service, client):
        mock_service.continue_run = AsyncMock(side_effect=ValueError("bad"))
        resp = client.post("/api/runs/complete", json={
            "content": "test",
        }, headers={"X-User-ID": "admin"})
        assert resp.status_code == 400

    @patch("routers.run_continue.run_service", new_callable=MagicMock)
    def test_continue_run_http_exception(self, mock_service, client):
        from fastapi import HTTPException
        mock_service.continue_run = AsyncMock(side_effect=HTTPException(status_code=400, detail="bad"))
        resp = client.post("/api/runs/complete", json={"content": "x"}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 400

    @patch("routers.run_continue.run_service", new_callable=MagicMock)
    def test_continue_run_generic_error(self, mock_service, client):
        mock_service.continue_run = AsyncMock(side_effect=RuntimeError("error"))
        resp = client.post("/api/runs/complete", json={
            "content": "test",
        }, headers={"X-User-ID": "admin"})
        assert resp.status_code == 500

    def test_complete_run_request_model(self):
        from routers.run_continue import CompleteRunRequest
        req = CompleteRunRequest(content="hello")
        assert req.content == "hello"
        assert req.session_id is None
        assert req.thinking is None
