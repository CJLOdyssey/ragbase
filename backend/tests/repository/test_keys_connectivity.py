"""Tests for keys_connectivity.py — connection testing and model parsing."""

import json
import os
import unittest.mock

os.environ.setdefault("KEY_VAULT_SECRET", "0123456789abcdef0123456789abcdef")
os.environ.setdefault("AUTH_MODE", "legacy")
os.environ.setdefault("AUTH_ENABLED", "0")
os.environ.setdefault("CHECKPOINTER_BACKEND", "memory")
os.environ.setdefault("DATABASE_POOL_SIZE", "0")

from repository.keys_connectivity import (
    _classify_models,
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


def _canned_response(model_ids):
    resp = unittest.mock.MagicMock()
    resp.status = 200
    resp.read.return_value = json.dumps({
        "data": [{"id": mid} for mid in model_ids]
    }).encode()
    resp.__enter__ = unittest.mock.MagicMock(return_value=resp)
    resp.__exit__ = unittest.mock.MagicMock(return_value=False)
    return resp


def _urlopen_side_effect(buckets, fallback=()):
    def side_effect(req, *args, **kwargs):
        url = req.full_url
        for key, model_ids in buckets.items():
            if f"sub_type={key}" in url or f"type={key}" in url:
                return _canned_response(model_ids)
        return _canned_response(fallback)
    return side_effect


class TestClassifyModels:
    def test_chat_maps_to_llm(self):
        with unittest.mock.patch("urllib.request.urlopen", side_effect=_urlopen_side_effect({
            "chat": ["Qwen/Qwen2.5-7B-Instruct"],
        })):
            models, types = _classify_models(
                "https://api.siliconflow.cn/v1/models", "sk-test", "siliconflow"
            )
        assert "Qwen/Qwen2.5-7B-Instruct" in models
        assert types["Qwen/Qwen2.5-7B-Instruct"] == "llm"

    def test_all_sub_types_mapped(self):
        buckets = {
            "chat": ["sf/chat-1"],
            "embedding": ["sf/embed-1"],
            "reranker": ["sf/rerank-1"],
            "text-to-image": ["sf/tti-1"],
            "image-to-image": ["sf/iti-1"],
            "text-to-video": ["sf/ttv-1"],
            "speech-to-text": ["sf/stt-1"],
        }
        with unittest.mock.patch("urllib.request.urlopen", side_effect=_urlopen_side_effect(buckets)):
            models, types = _classify_models(
                "https://api.siliconflow.cn/v1/models", "sk-test", "custom"
            )
        assert set(models) == set(sum(buckets.values(), []))
        assert types == {
            "sf/chat-1": "llm",
            "sf/embed-1": "embedding",
            "sf/rerank-1": "rerank",
            "sf/tti-1": "tool",
            "sf/iti-1": "tool",
            "sf/ttv-1": "tool",
            "sf/stt-1": "speech2text",
        }

    def test_audio_heuristic_tts_asr_split(self):
        with unittest.mock.patch("urllib.request.urlopen", side_effect=_urlopen_side_effect({
            "audio": [
                "FunAudioLLM/CosyVoice2-0.5B",
                "FunAudioLLM/SenseVoiceSmall",
                "Kokoro-82M",
            ],
        })):
            models, types = _classify_models(
                "https://api.siliconflow.cn/v1/models", "sk-test", "siliconflow"
            )
        assert types["FunAudioLLM/CosyVoice2-0.5B"] == "tts"
        assert types["FunAudioLLM/SenseVoiceSmall"] == "speech2text"
        assert "Kokoro-82M" in models
        assert "Kokoro-82M" not in types

    def test_audio_asr_wins_over_voice_marker(self):
        with unittest.mock.patch("urllib.request.urlopen", side_effect=_urlopen_side_effect({
            "audio": ["iic/SenseVoiceSmall"],
        })):
            _, types = _classify_models(
                "https://api.siliconflow.cn/v1/models", "sk-test", "siliconflow"
            )
        assert types["iic/SenseVoiceSmall"] == "speech2text"

    def test_provider_detected_by_chinese_name(self):
        with unittest.mock.patch("urllib.request.urlopen", side_effect=_urlopen_side_effect({
            "chat": ["sf/chat-1"],
        })):
            models, types = _classify_models("https://api.siliconflow.cn/v1/models", "sk-test", "硅基流动")
        assert types["sf/chat-1"] == "llm"
        assert "sf/chat-1" in models

    def test_base_url_detected(self):
        with unittest.mock.patch("urllib.request.urlopen", side_effect=_urlopen_side_effect({
            "embedding": ["sf/embed-1"],
        })):
            _, types = _classify_models(
                "https://proxy.siliconflow.example/v1/models", "sk-test", "custom"
            )
        assert types["sf/embed-1"] == "embedding"

    def test_non_siliconflow_types_empty(self):
        with unittest.mock.patch("urllib.request.urlopen", side_effect=_urlopen_side_effect(
            {}, fallback=["gpt-4", "gpt-3.5"]
        )) as mock_open:
            models, types = _classify_models(
                "https://api.openai.com/v1/models", "sk-test", "openai"
            )
        assert models == ["gpt-4", "gpt-3.5"]
        assert types == {}
        assert mock_open.call_count == 1

    def test_fetch_failure_degrades_to_single_fetch(self):
        def side_effect(req, *args, **kwargs):
            if "sub_type=" in req.full_url or "type=audio" in req.full_url:
                raise ConnectionError("boom")
            return _canned_response(["m1", "m2"])

        with unittest.mock.patch("urllib.request.urlopen", side_effect=side_effect):
            models, types = _classify_models(
                "https://api.siliconflow.cn/v1/models", "sk-test", "siliconflow"
            )
        assert models == ["m1", "m2"]
        assert types == {}

    def test_partial_failure_degrades(self):
        def side_effect(req, *args, **kwargs):
            if "sub_type=embedding" in req.full_url:
                raise ConnectionError("boom")
            if "sub_type=" in req.full_url or "type=audio" in req.full_url:
                return _canned_response(["sf/chat-1"])
            return _canned_response(["m1"])

        with unittest.mock.patch("urllib.request.urlopen", side_effect=side_effect):
            models, types = _classify_models(
                "https://api.siliconflow.cn/v1/models", "sk-test", "siliconflow"
            )
        assert models == ["m1"]
        assert types == {}

    def test_single_fetch_failure_returns_empty(self):
        def side_effect(req, *args, **kwargs):
            raise ConnectionError("boom")

        with unittest.mock.patch("urllib.request.urlopen", side_effect=side_effect):
            models, types = _classify_models(
                "https://api.siliconflow.cn/v1/models", "sk-test", "siliconflow"
            )
        assert models == []
        assert types == {}

    def test_dedup_models_across_buckets(self):
        with unittest.mock.patch("urllib.request.urlopen", side_effect=_urlopen_side_effect({
            "chat": ["sf/shared"],
            "audio": ["sf/shared", "sf/tts-only"],
        })):
            models, types = _classify_models(
                "https://api.siliconflow.cn/v1/models", "sk-test", "siliconflow"
            )
        assert models.count("sf/shared") == 1
        assert types["sf/shared"] == "llm"


class TestTestConnectionSyncTypes:
    def test_siliconflow_connection_includes_types(self):
        with unittest.mock.patch("urllib.request.urlopen", side_effect=_urlopen_side_effect({
            "chat": ["sf/chat-1"],
            "embedding": ["sf/embed-1"],
        })):
            result = _test_connection_sync({
                "api_key": "sk-test",
                "provider": "siliconflow",
                "base_url": "https://api.siliconflow.cn/v1",
            })
        assert result["success"] is True
        assert result["types"]["sf/chat-1"] == "llm"
        assert result["types"]["sf/embed-1"] == "embedding"

    def test_non_siliconflow_types_empty_in_connection(self):
        with unittest.mock.patch("urllib.request.urlopen", side_effect=_urlopen_side_effect(
            {}, fallback=["gpt-4"]
        )):
            result = _test_connection_sync({
                "api_key": "sk-test",
                "provider": "openai",
                "base_url": "https://api.openai.com/v1",
            })
        assert result["success"] is True
        assert result["types"] == {}

    def test_connection_failure_includes_empty_types(self):
        with unittest.mock.patch("urllib.request.urlopen", side_effect=ConnectionError("refused")):
            result = _test_connection_sync({
                "api_key": "sk-test",
                "provider": "openai",
                "base_url": "https://bad.host",
            })
        assert result["success"] is False
        assert result["types"] == {}
