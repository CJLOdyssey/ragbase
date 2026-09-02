"""Asset URL-import route tests — SSRF guard + happy path (unit, mocked HTTP)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from routers.assets import _validate, import_asset_from_url

pytestmark = pytest.mark.unit


class _FakeRequest:
    def __init__(self, user_id: str = "u1"):
        self._user_id = user_id

    def __getattribute__(self, name: str):
        if name == "_user_id":
            return super().__getattribute__(name)
        raise AttributeError(name)


def _patch_get_user_id(user_id: str = "u1"):
    """Context manager：patch 作用域限定在用例内，杜绝跨测试泄漏。"""
    return patch("routers.assets.get_user_id", side_effect=lambda request: user_id)


class TestValidate:
    def test_accepts_docx(self):
        assert (
            _validate(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 100
            )
            == "document"
        )

    def test_accepts_xlsx(self):
        assert (
            _validate(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 100
            )
            == "data"
        )

    def test_rejects_unknown_type(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            _validate("application/zip", 100)


class TestImportUrl:
    @pytest.mark.asyncio
    async def test_rejects_non_http_scheme(self):
        with _patch_get_user_id():
            from fastapi import HTTPException

            with pytest.raises(HTTPException):
                await import_asset_from_url(
                    type("UrlImportIn", (), {"url": "file:///etc/passwd", "name": None})(),
                    _FakeRequest(),
                )

    @pytest.mark.asyncio
    async def test_rejects_loopback_url(self):
        with _patch_get_user_id():
            from fastapi import HTTPException

            with pytest.raises(HTTPException):
                await import_asset_from_url(
                    type("UrlImportIn", (), {"url": "http://127.0.0.1/x", "name": None})(),
                    _FakeRequest(),
                )

    @pytest.mark.asyncio
    async def test_rejects_private_ip(self):
        with _patch_get_user_id():
            from fastapi import HTTPException

            with pytest.raises(HTTPException):
                await import_asset_from_url(
                    type("UrlImportIn", (), {"url": "http://10.0.0.8/x", "name": None})(),
                    _FakeRequest(),
                )

    @pytest.mark.asyncio
    async def test_rejects_redirect_to_internal(self):
        """SSRF: a redirect to a private address must be rejected (OWASP)."""
        with _patch_get_user_id():
            from fastapi import HTTPException

            redirect_resp = MagicMock()
            redirect_resp.status_code = 302
            redirect_resp.headers = {
                "location": "http://127.0.0.1/secret",
                "content-type": "text/markdown",
            }
            redirect_resp.content = b"# redirected doc"
            redirect_resp.raise_for_status = MagicMock()
            client_mock = MagicMock()
            client_mock.get = AsyncMock(return_value=redirect_resp)
            client_cm = AsyncMock()
            client_cm.__aenter__.return_value = client_mock
            client_cm.__aexit__ = AsyncMock(return_value=False)

            with patch("httpx.AsyncClient", return_value=client_cm), patch(
                "routers.assets.create_asset", new_callable=AsyncMock
            ):
                with pytest.raises(HTTPException):
                    await import_asset_from_url(
                        type("UrlImportIn", (), {"url": "http://1.1.1.1/doc", "name": None})(),
                        _FakeRequest(),
                    )

    @pytest.mark.asyncio
    async def test_redirect_loop_capped(self):
        """Redirect chains longer than _MAX_REDIRECTS are rejected."""
        with _patch_get_user_id():
            from fastapi import HTTPException

            redirect_resp = MagicMock()
            redirect_resp.status_code = 302
            redirect_resp.headers = {
                "location": "http://1.1.1.1/again",
                "content-type": "text/html",
            }
            redirect_resp.content = b""
            redirect_resp.raise_for_status = MagicMock()
            client_mock = MagicMock()
            client_mock.get = AsyncMock(return_value=redirect_resp)
            client_cm = AsyncMock()
            client_cm.__aenter__.return_value = client_mock
            client_cm.__aexit__ = AsyncMock(return_value=False)

            with patch("httpx.AsyncClient", return_value=client_cm):
                with pytest.raises(HTTPException):
                    await import_asset_from_url(
                        type("UrlImportIn", (), {"url": "http://1.1.1.1/start", "name": None})(),
                        _FakeRequest(),
                    )
            assert client_mock.get.await_count == 4

    @pytest.mark.asyncio
    async def test_imports_public_url(self):
        with _patch_get_user_id():
            from routers.assets import ASSET_DIR

            content = b"# remote doc\ncontent"
            resp = MagicMock()
            resp.status_code = 200
            resp.content = content
            resp.headers = {"content-type": "text/markdown"}
            resp.raise_for_status = MagicMock()
            client_mock = MagicMock()
            client_mock.get = AsyncMock(return_value=resp)
            client_cm = AsyncMock()
            client_cm.__aenter__.return_value = client_mock
            client_cm.__aexit__ = AsyncMock(return_value=False)

            asset = MagicMock()
            asset.id = "a1"
            asset.name = "doc.md"
            asset.asset_type = "document"
            asset.format = "md"
            asset.size_bytes = len(content)
            asset.usage_count = 0
            asset.indexed = False
            asset.index_error = None
            asset.knowledge_base_id = None
            asset.source = "url"
            asset.source_ref = "http://1.1.1.1/doc.md"
            asset.tags = []

            with patch(
                "httpx.AsyncClient", return_value=client_cm
            ) as mock_cls, patch(
                "routers.assets.create_asset", new_callable=AsyncMock, return_value=asset
            ) as mock_create:
                result = await import_asset_from_url(
                    type("UrlImportIn", (), {"url": "http://1.1.1.1/doc.md", "name": None})(),
                    _FakeRequest(),
                )
            mock_cls.assert_called_once()
            mock_create.assert_awaited_once()
            assert result.source == "url"
            assert result.source_ref == "http://1.1.1.1/doc.md"

            # cleanup stray file if the mocked path wrote one
            import contextlib

            with contextlib.suppress(IndexError, OSError):
                list(ASSET_DIR.glob("u1-*-doc.md"))[0].unlink()
