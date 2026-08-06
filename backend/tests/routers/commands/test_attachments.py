from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException


class TestAttachments:

    @patch("routers.attachments.get_session", new_callable=AsyncMock, return_value=None)
    async def test_upload_session_not_found(self, mock_get, client):
        resp = client.post(
            "/api/attachments",
            files={"file": ("test.txt", b"content", "text/plain")},
            data={"session_id": "nonexistent"},
        )
        assert resp.status_code == 404

    async def test_upload_too_large(self, client):
        resp = client.post("/api/sessions", json={"title": "att-test"}, headers={"X-User-ID": "admin"})
        assert resp.status_code == 201
        session_id = resp.json()["id"]

        from core.error_codes import ErrorCode, error_response
        with patch("routers.attachments._validate_upload",
                   side_effect=error_response(ErrorCode.ATTACHMENT_TOO_LARGE, detail="文件超过 10MB 限制")):
            large_content = b"x" * 100
            resp = client.post(
                "/api/attachments",
                files={"file": ("big.txt", large_content, "text/plain")},
                data={"session_id": session_id},
            )
            assert resp.status_code == 413

    async def test_upload_text_file(self, client):
        resp = client.post("/api/sessions", json={"title": "att-text"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]

        resp = client.post(
            "/api/attachments",
            files={"file": ("hello.txt", b"hello world", "text/plain")},
            data={"session_id": session_id},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["filename"] == "hello.txt"
        assert data["content_type"] == "text/plain"
        assert data["size_bytes"] == 11

    async def test_upload_json_file(self, client):
        resp = client.post("/api/sessions", json={"title": "att-json"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]

        resp = client.post(
            "/api/attachments",
            files={"file": ("data.json", b'{"key":"value"}', "application/json")},
            data={"session_id": session_id},
        )
        assert resp.status_code == 201
        assert resp.json()["has_extracted_text"] is True

    async def test_upload_pdf_file(self, client):
        resp = client.post("/api/sessions", json={"title": "att-pdf"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]

        resp = client.post(
            "/api/attachments",
            files={"file": ("doc.pdf", b"%PDF-1.4 fake", "application/pdf")},
            data={"session_id": session_id},
        )
        assert resp.status_code == 201
        assert resp.json()["has_extracted_text"] is True

    async def test_upload_image_file(self, client):
        resp = client.post("/api/sessions", json={"title": "att-img"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]

        resp = client.post(
            "/api/attachments",
            files={"file": ("photo.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            data={"session_id": session_id},
        )
        assert resp.status_code == 201
        assert resp.json()["has_extracted_text"] is True

    async def test_upload_binary_content_type(self, client):
        resp = client.post("/api/sessions", json={"title": "att-bin"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]

        resp = client.post(
            "/api/attachments",
            files={"file": ("data.bin", b"\x00\x01\x02", "application/octet-stream")},
            data={"session_id": session_id},
        )
        assert resp.status_code == 415

    async def test_upload_no_filename(self, client):
        resp = client.post("/api/sessions", json={"title": "att-nofn"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]

        resp = client.post(
            "/api/attachments",
            files={"file": ("unnamed.txt", b"content", "text/plain")},
            data={"session_id": session_id},
        )
        assert resp.status_code == 201

    async def test_upload_save_failure(self, client):
        resp = client.post("/api/sessions", json={"title": "att-save-fail"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        with patch("pathlib.Path.write_bytes", side_effect=Exception("disk full")):
            resp = client.post(
                "/api/attachments",
                files={"file": ("fail.txt", b"content", "text/plain")},
                data={"session_id": session_id},
            )
            assert resp.status_code == 500

    async def test_get_attachment_not_found(self, client):
        resp = client.get("/api/attachments/nonexistent-id")
        assert resp.status_code == 404

    async def test_get_attachment_file_missing(self, client):
        resp = client.post("/api/sessions", json={"title": "att-file-miss"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.post(
            "/api/attachments",
            files={"file": ("missing.txt", b"content", "text/plain")},
            data={"session_id": session_id},
        )
        attachment_id = resp.json()["id"]
        with patch("pathlib.Path.exists", return_value=False):
            resp = client.get(f"/api/attachments/{attachment_id}")
            assert resp.status_code == 410

    async def test_list_session_attachments(self, client):
        resp = client.post("/api/sessions", json={"title": "att-list"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]

        client.post(
            "/api/attachments",
            files={"file": ("file.txt", b"content", "text/plain")},
            data={"session_id": session_id},
        )

        resp = client.get(f"/api/sessions/{session_id}/attachments")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    async def test_list_attachments_session_not_found(self, client):
        resp = client.get("/api/sessions/nonexistent/attachments")
        assert resp.status_code == 404

    async def test_delete_attachment_not_found(self, client):
        resp = client.delete("/api/attachments/nonexistent")
        assert resp.status_code == 404

    async def test_delete_attachment_success(self, client):
        resp = client.post("/api/sessions", json={"title": "att-del"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]

        resp = client.post(
            "/api/attachments",
            files={"file": ("del.txt", b"delete me", "text/plain")},
            data={"session_id": session_id},
        )
        attachment_id = resp.json()["id"]

        resp = client.delete(f"/api/attachments/{attachment_id}")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    async def test_delete_attachment_disk_failure(self, client):
        resp = client.post("/api/sessions", json={"title": "att-disk-fail"}, headers={"X-User-ID": "admin"})
        session_id = resp.json()["id"]
        resp = client.post(
            "/api/attachments",
            files={"file": ("diskfail.txt", b"content", "text/plain")},
            data={"session_id": session_id},
        )
        attachment_id = resp.json()["id"]
        with patch("pathlib.Path.unlink", side_effect=Exception("permission denied")):
            resp = client.delete(f"/api/attachments/{attachment_id}")
            assert resp.status_code == 200
            assert resp.json()["success"] is True

    def test_extract_text_failure(self):
        from routers.attachments import _extract_text
        with patch("pathlib.Path.read_text", side_effect=Exception("IO error")):
            result = _extract_text(Path("/fake/path.txt"), "text/plain")
            assert result == ""

    def test_validate_upload_too_large(self):
        from routers.attachments import _validate_upload
        with pytest.raises(HTTPException):
            _validate_upload("text/plain", 11 * 1024 * 1024)

    def test_validate_upload_invalid_type(self):
        from routers.attachments import _validate_upload
        with pytest.raises(HTTPException):
            _validate_upload("application/x-executable", 100)

    def test_upload_dir_creation(self):
        from routers.attachments import UPLOAD_DIR
        assert UPLOAD_DIR.exists()
