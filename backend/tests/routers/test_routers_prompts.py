"""Prompts router tests — merged from test_coverage_boost, test_coverage_gaps, test_remaining_coverage."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit



class TestPrompts:
    """Merged: TestPrompts + TestPromptsGaps + TestPromptsRemainingGaps."""

    # ── CRUD basics ──────────────────────────────────────────────────────

    def test_list_prompts(self, client):
        resp = client.get("/api/prompts")
        assert resp.status_code == 200

    def test_list_prompts_by_category(self, client):
        resp = client.get("/api/prompts?category=general")
        assert resp.status_code == 200

    def test_create_prompt(self, client):
        resp = client.post("/api/prompts", json={
            "name": "test-prompt", "category": "general", "content": "Be helpful."
        })
        assert resp.status_code == 201

    def test_create_prompt_with_description(self, client):
        resp = client.post("/api/prompts", json={
            "name": "desc-prompt", "description": "用途说明", "category": "general", "content": "Be helpful."
        })
        assert resp.status_code == 201
        assert resp.json()["description"] == "用途说明"

    def test_list_prompts_include_description(self, client):
        client.post("/api/prompts", json={
            "name": "list-desc-prompt", "description": "desc-1", "category": "general", "content": "x"
        })
        resp = client.get("/api/prompts")
        assert resp.status_code == 200
        assert all("description" in p for p in resp.json())

    def test_update_prompt(self, client):
        resp = client.post("/api/prompts", json={
            "name": "upd-prompt", "category": "general", "content": "Original."
        })
        prompt_id = resp.json()["id"]
        resp = client.put(f"/api/prompts/{prompt_id}", json={"name": "updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "updated"

    def test_update_prompt_description(self, client):
        resp = client.post("/api/prompts", json={
            "name": "upd-desc-prompt", "description": "old", "category": "general", "content": "Original."
        })
        prompt_id = resp.json()["id"]
        resp = client.put(f"/api/prompts/{prompt_id}", json={"description": "new desc"})
        assert resp.status_code == 200
        assert resp.json()["description"] == "new desc"

    def test_update_prompt_not_found(self, client):
        resp = client.put("/api/prompts/nonexistent", json={"name": "x"})
        assert resp.status_code == 404

    def test_delete_prompt(self, client):
        resp = client.post("/api/prompts", json={
            "name": "del-prompt", "category": "general", "content": "Delete me."
        })
        prompt_id = resp.json()["id"]
        resp = client.delete(f"/api/prompts/{prompt_id}")
        assert resp.status_code == 204

    def test_delete_prompt_not_found(self, client):
        resp = client.delete("/api/prompts/nonexistent")
        assert resp.status_code == 404

    def test_delete_prompt_does_not_load_all(self, client):
        """Delete must look up a single prompt, not load the whole table."""
        with patch("repository.get_prompts", new_callable=AsyncMock, side_effect=RuntimeError("boom")):
            resp = client.delete("/api/prompts/nonexistent")
            assert resp.status_code == 404

    # ── Exception handler paths ──────────────────────────────────────────

    def test_list_prompts_exception(self, client):
        with patch("routers.prompts.get_prompts_as_dicts", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.get("/api/prompts")
            assert resp.status_code == 500

    def test_create_prompt_exception(self, client):
        with patch("routers.prompts.create_prompt", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.post("/api/prompts", json={"name": "x", "category": "c", "content": "y"})
            assert resp.status_code == 500

    def test_update_prompt_exception(self, client):
        with patch("routers.prompts.update_prompt", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.put("/api/prompts/t", json={"name": "x"})
            assert resp.status_code == 500

    def test_delete_prompt_exception(self, client):
        with patch("repository.get_prompt", new_callable=AsyncMock, side_effect=RuntimeError("err")):
            resp = client.delete("/api/prompts/t")
            assert resp.status_code == 500

    # ── Edge cases ───────────────────────────────────────────────────────

    def test_snapshot_prompt_item_not_found(self, client):
        from routers.prompts import _snapshot_prompt
        with patch("repository.prompts.get_prompt", new_callable=AsyncMock, return_value=None), \
             patch("repository.snapshot_helper.with_session", new_callable=AsyncMock) as mock_ws:
            async def capture_call(fn, **kwargs):
                await fn(MagicMock(), "prompt", "p-1")
            mock_ws.side_effect = capture_call
            asyncio.run(_snapshot_prompt("p-1"))

    def test_edit_prompt_generic_exception(self, client):
        resp = client.post("/api/prompts", json={
            "name": "exc-prompt", "category": "general", "content": "x"
        })
        prompt_id = resp.json()["id"]
        with patch("routers.prompts.update_prompt", new_callable=AsyncMock, side_effect=Exception("err")):
            resp = client.put(f"/api/prompts/{prompt_id}", json={"name": "y"})
            assert resp.status_code == 500

    def test_delete_prompt_generic_exception(self, client):
        resp = client.post("/api/prompts", json={
            "name": "del-exc-prompt", "category": "general", "content": "x"
        })
        prompt_id = resp.json()["id"]
        with patch("repository.get_prompt", new_callable=AsyncMock, side_effect=Exception("err")):
            resp = client.delete(f"/api/prompts/{prompt_id}")
            assert resp.status_code == 500
