"""Tests for keys_connectivity.py — connection testing and model parsing."""

import json
import os
import unittest.mock

import pytest

os.environ.setdefault("KEY_VAULT_SECRET", "0123456789abcdef0123456789abcdef")
os.environ.setdefault("AUTH_MODE", "legacy")
os.environ.setdefault("AUTH_ENABLED", "0")
os.environ.setdefault("CHECKPOINTER_BACKEND", "memory")
os.environ.setdefault("DATABASE_POOL_SIZE", "0")

from repository.keys_connectivity import (
    _parse_models_from_response,
    _test_connection_sync,
)


class TestParseModelsFromResponse:
    def test_parse_valid_response(self):
        resp = unittest.mock.MagicMock()
        resp.read.return_value = json.dumps({
            "data": [
                {"id": "gpt-4"},
                {"id": "gpt-3.5-turbo"},
                {"id": "o1-preview"},
            ]
        }).encode()
        models = _parse_models_from_response(resp, "openai")
        assert models == ["gpt-4", "gpt-3.5-turbo", "o1-preview"]

    def test_parse_empty_data(self):
        resp = unittest.mock.MagicMock()
        resp.read.return_value = json.dumps({"data": []}).encode()
        models = _parse_models_from_response(resp, "openai")
        assert models == []

    def test_parse_no_data_key(self):
        resp = unittest.mock.MagicMock()
        resp.read.return_value = json.dumps({}).encode()
        models = _parse_models_from_response(resp, "openai")
        assert models == []

    def test_parse_invalid_json(self):
        resp = unittest.mock.MagicMock()
        resp.read.return_value = b"not json"
        models = _parse_models_from_response(resp, "openai")
        assert models == []

    def test_parse_items_without_id(self):
        resp = unittest.mock.MagicMock()
        resp.read.return_value = json.dumps({
            "data": [{"name": "model1"}, {"id": ""}]
        }).encode()
        models = _parse_models_from_response(resp, "openai")
        assert models == []


class TestTestConnectionSync:
    def test_no_base_url_known_provider(self):
        result = _test_connection_sync({
            "api_key": "sk-test",
            "provider": "unknown_provider",
            "base_url": "",
        })
        assert result["success"] is False
        assert "No base URL" in result["message"]

    def test_base_url_v1_suffix(self):
        with unittest.mock.patch("urllib.request.urlopen") as mock_open:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps({"data": [{"id": "m1"}]}).encode()
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            result = _test_connection_sync({
                "api_key": "sk-test",
                "provider": "openai",
                "base_url": "https://api.example.com/v1",
            })
            assert result["success"] is True
            assert "m1" in result["models"]
            call_url = mock_open.call_args[0][0].full_url
            assert "/v1/models" in call_url

    def test_base_url_v1_trailing_slash(self):
        with unittest.mock.patch("urllib.request.urlopen") as mock_open:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps({"data": []}).encode()
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            result = _test_connection_sync({
                "api_key": "sk-test",
                "provider": "openai",
                "base_url": "https://api.example.com/v1/",
            })
            assert result["success"] is True

    def test_base_url_no_v1_suffix(self):
        with unittest.mock.patch("urllib.request.urlopen") as mock_open:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps({"data": []}).encode()
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            result = _test_connection_sync({
                "api_key": "sk-test",
                "provider": "openai",
                "base_url": "https://api.example.com",
            })
            assert result["success"] is True
            call_url = mock_open.call_args[0][0].full_url
            assert call_url.endswith("/v1/models")

    def test_known_provider_no_base_url(self):
        with unittest.mock.patch("urllib.request.urlopen") as mock_open:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.status = 200
            mock_resp.read.return_value = json.dumps({"data": [{"id": "gpt-4"}]}).encode()
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            result = _test_connection_sync({
                "api_key": "sk-test",
                "provider": "openai",
                "base_url": "",
            })
            assert result["success"] is True
            call_url = mock_open.call_args[0][0].full_url
            assert "api.openai.com" in call_url

    def test_http_non_200(self):
        with unittest.mock.patch("urllib.request.urlopen") as mock_open:
            mock_resp = unittest.mock.MagicMock()
            mock_resp.status = 401
            mock_resp.__enter__ = unittest.mock.MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            mock_open.return_value = mock_resp

            result = _test_connection_sync({
                "api_key": "sk-bad",
                "provider": "openai",
                "base_url": "",
            })
            assert result["success"] is False
            assert "401" in result["message"]

    def test_connection_exception(self):
        with unittest.mock.patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
            result = _test_connection_sync({
                "api_key": "sk-test",
                "provider": "openai",
                "base_url": "https://bad.host",
            })
            assert result["success"] is False
            assert "refused" in result["message"]


class TestApiKeyConnectionAsync:
    async def test_key_not_found(self, db_engine):
        from repository.keys_connectivity import test_api_key_connection
        result = await test_api_key_connection("nonexistent", "user1")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    async def test_key_found_but_connection_mocked(self, db_engine):
        from repository.keys_connectivity import test_api_key_connection
        from repository.keys_crud import create_api_key
        k = await create_api_key("user1", "openai", plaintext_key="sk-test")

        with unittest.mock.patch(
            "repository.keys_connectivity._test_connection_sync",
            return_value={"success": True, "message": "ok", "models": ["gpt-4"]},
        ):
            result = await test_api_key_connection(k.id, "user1")
            assert result["success"] is True
            assert "gpt-4" in result["models"]
