"""Supplementary tests for assets router — coverage gap fill.

Covers pure helpers and routes not exercised by existing test files.
"""

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from routers.assets import (
    _candidate_import_urls,
    _extract_format,
    _sanitize_tags,
    _validate,
)

pytestmark = pytest.mark.unit


def _fake_asset(**overrides) -> SimpleNamespace:
    defaults = dict(
        id="a1",
        user_id="admin-login",
        name="doc.pdf",
        asset_type="document",
        format="pdf",
        indexed=True,
        index_error=None,
        knowledge_base_id=None,
        source="upload",
        source_ref=None,
        tags=[],
        updated_at=None,
        usage_count=0,
        size_bytes=100,
        storage_path="/tmp/doc.pdf",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


# ── Pure helpers ─────────────────────────────────────────────────────


class TestExtractFormat:
    def test_pdf(self):
        assert _extract_format("report.pdf") == "pdf"

    def test_no_extension(self):
        assert _extract_format("README") == "unknown"

    def test_uppercase(self):
        assert _extract_format("FILE.PDF") == "pdf"

    def test_dot_prefix_stripped(self):
        assert _extract_format("file.tar.gz") == "gz"


class TestValidate:
    def test_image_png(self):
        assert _validate("image/png", 1000) == "image"

    def test_image_jpeg(self):
        assert _validate("image/jpeg", 1000) == "image"

    def test_image_webp(self):
        assert _validate("image/webp", 1000) == "image"

    def test_image_gif(self):
        assert _validate("image/gif", 1000) == "image"

    def test_image_bmp(self):
        assert _validate("image/bmp", 1000) == "image"

    def test_image_too_large(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _validate("image/png", 11 * 1024 * 1024)

    def test_data_csv(self):
        assert _validate("text/csv", 1000) == "data"

    def test_data_xlsx(self):
        ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert _validate(ct, 1000) == "data"

    def test_data_ms_excel(self):
        assert _validate("application/vnd.ms-excel", 1000) == "data"

    def test_doc_pdf(self):
        assert _validate("application/pdf", 1000) == "document"

    def test_doc_text(self):
        assert _validate("text/plain", 1000) == "document"

    def test_doc_markdown(self):
        assert _validate("text/markdown", 1000) == "document"

    def test_doc_html(self):
        assert _validate("text/html", 1000) == "document"

    def test_doc_word(self):
        assert _validate("application/msword", 1000) == "document"

    def test_doc_docx(self):
        ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert _validate(ct, 1000) == "document"

    def test_doc_ppt(self):
        assert _validate("application/vnd.ms-powerpoint", 1000) == "document"

    def test_doc_pptx(self):
        ct = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        assert _validate(ct, 1000) == "document"

    def test_doc_too_large(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _validate("application/pdf", 21 * 1024 * 1024)

    def test_unsupported_type(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _validate("application/x-executable", 1000)


class TestSanitizeTags:
    def test_basic(self):
        assert _sanitize_tags(["API", "部署"]) == ["api", "部署"]

    def test_dedup(self):
        assert _sanitize_tags(["api", "API", "Api"]) == ["api"]

    def test_max_20(self):
        tags = [f"tag{i}" for i in range(30)]
        assert len(_sanitize_tags(tags)) == 20

    def test_truncate_long_tag(self):
        result = _sanitize_tags(["a" * 100])
        assert len(result[0]) == 32

    def test_empty_string_filtered(self):
        assert _sanitize_tags(["", "  ", "valid"]) == ["valid"]

    def test_empty_input(self):
        assert _sanitize_tags([]) == []


class TestCandidateImportUrls:
    def test_google_doc(self):
        url = "https://docs.google.com/document/d/ABC123/edit"
        candidates = _candidate_import_urls(url)
        assert any("export?format=docx" in c for c in candidates)
        assert any("export?format=pdf" in c for c in candidates)
        assert url in candidates

    def test_google_sheet(self):
        url = "https://docs.google.com/spreadsheets/d/XYZ789/edit"
        candidates = _candidate_import_urls(url)
        assert any("export?format=xlsx" in c for c in candidates)
        assert any("export?format=pdf" in c for c in candidates)

    def test_google_slides(self):
        url = "https://docs.google.com/presentation/d/SLD456/edit"
        candidates = _candidate_import_urls(url)
        assert any("export?format=pptx" in c for c in candidates)
        assert any("export?format=pdf" for c in candidates)

    def test_google_drive_file(self):
        url = "https://drive.google.com/file/d/FILE789/view"
        candidates = _candidate_import_urls(url)
        assert any("uc?export=download" in c for c in candidates)

    def test_non_google_returns_original(self):
        url = "https://example.com/file.pdf"
        candidates = _candidate_import_urls(url)
        assert candidates == [url]

    def test_dedup(self):
        url = "https://example.com/file.pdf"
        candidates = _candidate_import_urls(url)
        assert len(candidates) == len(set(candidates))


# ── Router routes ────────────────────────────────────────────────────


class TestGetAssetContent:
    async def test_image_returns_empty(self, client):
        asset = _fake_asset(asset_type="image")
        with (
            patch("routers.assets.get_asset_for_user", return_value=asset),
            patch("pathlib.Path.exists", return_value=True),
        ):
            resp = client.get("/api/assets/a1/content")
        assert resp.status_code == 200
        assert resp.json()["content"] == ""
        assert resp.json()["assetType"] == "image"

    async def test_asset_not_found(self, client):
        with patch("routers.assets.get_asset_for_user", return_value=None):
            resp = client.get("/api/assets/a1/content")
        assert resp.status_code == 404

    async def test_file_not_on_disk(self, client):
        asset = _fake_asset(storage_path="/nonexistent/path.pdf")
        with patch("routers.assets.get_asset_for_user", return_value=asset):
            resp = client.get("/api/assets/a1/content")
        assert resp.status_code == 404

    async def test_text_content(self, client):
        asset = _fake_asset(asset_type="document", storage_path="/tmp/doc.pdf")
        with (
            patch("routers.assets.get_asset_for_user", return_value=asset),
            patch("pathlib.Path.exists", return_value=True),
            patch("rag.rag_parsing.extract_text", return_value="hello world"),
        ):
            resp = client.get("/api/assets/a1/content")
        assert resp.status_code == 200
        assert resp.json()["content"] == "hello world"
        assert resp.json()["truncated"] is False

    async def test_text_truncated_at_20k(self, client):
        asset = _fake_asset(asset_type="document", storage_path="/tmp/doc.pdf")
        long_text = "x" * 25000
        with (
            patch("routers.assets.get_asset_for_user", return_value=asset),
            patch("pathlib.Path.exists", return_value=True),
            patch("rag.rag_parsing.extract_text", return_value=long_text),
        ):
            resp = client.get("/api/assets/a1/content")
        assert resp.status_code == 200
        assert resp.json()["truncated"] is True
        assert len(resp.json()["content"]) == 20000

    async def test_extract_failure_returns_500(self, client):
        asset = _fake_asset(asset_type="document", storage_path="/tmp/doc.pdf")
        with (
            patch("routers.assets.get_asset_for_user", return_value=asset),
            patch("pathlib.Path.exists", return_value=True),
            patch("rag.rag_parsing.extract_text", side_effect=Exception("parse error")),
        ):
            resp = client.get("/api/assets/a1/content")
        assert resp.status_code == 500


class TestGetAssetProgress:
    async def test_no_progress(self, client):
        asset = _fake_asset()
        with (
            patch("routers.assets.get_asset_for_user", return_value=asset),
            patch(
                "repository.index_progress.get_index_progress",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            resp = client.get("/api/assets/a1/progress")
        assert resp.status_code == 200
        assert resp.json() == {"stage": None}

    async def test_with_progress(self, client):
        asset = _fake_asset()
        with (
            patch("routers.assets.get_asset_for_user", return_value=asset),
            patch(
                "repository.index_progress.get_index_progress",
                new_callable=AsyncMock,
                return_value={"stage": "chunking", "progress": 50},
            ),
        ):
            resp = client.get("/api/assets/a1/progress")
        assert resp.status_code == 200
        assert resp.json()["stage"] == "chunking"

    async def test_asset_not_found(self, client):
        with patch("routers.assets.get_asset_for_user", return_value=None):
            resp = client.get("/api/assets/a1/progress")
        assert resp.status_code == 404


class TestTouchAsset:
    async def test_touch_increments(self, client):
        asset = _fake_asset(usage_count=5)
        updated_asset = _fake_asset(usage_count=6)
        with (
            patch("routers.assets.get_asset_for_user", side_effect=[asset, updated_asset]),
            patch(
                "repository.assets.increment_asset_usage",
                new_callable=AsyncMock,
            ),
            patch("routers.assets._chunk_counts_for", new_callable=AsyncMock, return_value={}),
        ):
            resp = client.post("/api/assets/a1/touch")
        assert resp.status_code == 200

    async def test_touch_asset_not_found(self, client):
        with patch("routers.assets.get_asset_for_user", return_value=None):
            resp = client.post("/api/assets/a1/touch")
        assert resp.status_code == 404


class TestRetryIndexAsset:
    async def test_retry_no_kb(self, client):
        asset = _fake_asset(knowledge_base_id=None)
        with patch("routers.assets.get_asset_for_user", return_value=asset):
            resp = client.post("/api/assets/a1/retry-index")
        assert resp.status_code == 400

    async def test_retry_not_document(self, client):
        asset = _fake_asset(asset_type="image", knowledge_base_id="kb1")
        with patch("routers.assets.get_asset_for_user", return_value=asset):
            resp = client.post("/api/assets/a1/retry-index")
        assert resp.status_code == 400

    async def test_retry_asset_not_found(self, client):
        with patch("routers.assets.get_asset_for_user", return_value=None):
            resp = client.post("/api/assets/a1/retry-index")
        assert resp.status_code == 404

    async def test_retry_success(self, client):
        asset = _fake_asset(knowledge_base_id="kb1")
        with (
            patch("routers.assets.get_asset_for_user", return_value=asset),
            patch(
                "repository.assets.set_asset_index_result",
                new_callable=AsyncMock,
            ),
            patch(
                "tasks.registry.index_asset",
            ) as mock_task,
        ):
            mock_task.delay = MagicMock()
            resp = client.post("/api/assets/a1/retry-index")
        assert resp.status_code == 200
        assert resp.json()["retrying"] is True
        mock_task.delay.assert_called_once_with("a1", "admin-login")


class TestGetAssetFile:
    async def test_file_not_found(self, client):
        asset = _fake_asset(storage_path="/nonexistent.pdf")
        with patch("routers.assets.get_asset_for_user", return_value=asset):
            resp = client.get("/api/assets/a1/file")
        assert resp.status_code == 404

    async def test_asset_not_found(self, client):
        with patch("routers.assets.get_asset_for_user", return_value=None):
            resp = client.get("/api/assets/a1/file")
        assert resp.status_code == 404
