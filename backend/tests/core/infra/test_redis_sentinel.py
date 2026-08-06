"""Redis Sentinel: create_redis direct/Sentinel paths + defaults."""

import importlib
from unittest.mock import patch


def _reload(monkeypatch, **env):
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    mod = importlib.import_module("core.infra.redis_sentinel")
    importlib.reload(mod)
    return mod


class TestDirectConnection:
    def test_default_disabled(self, monkeypatch):
        monkeypatch.delenv("REDIS_SENTINEL_ENABLED", raising=False)
        assert _reload(monkeypatch).SENTINEL_ENABLED is False

    def test_disabled_strings(self, monkeypatch):
        for val in ("0", "no", "false", "off", ""):
            mod = _reload(monkeypatch, REDIS_SENTINEL_ENABLED=val)
            assert mod.SENTINEL_ENABLED is False

    def test_default_url(self, monkeypatch):
        monkeypatch.delenv("REDIS_SENTINEL_ENABLED", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        mod = _reload(monkeypatch)
        with patch.object(mod.AsyncRedis, "from_url") as m:
            m.return_value = "redis"
            mod.create_redis()
            assert m.call_args[0][0] == "redis://localhost:6380/0"

    def test_custom_url(self, monkeypatch):
        monkeypatch.delenv("REDIS_SENTINEL_ENABLED", raising=False)
        mod = _reload(monkeypatch, REDIS_URL="redis://custom:7777/3")
        with patch.object(mod.AsyncRedis, "from_url") as m:
            mod.create_redis()
            assert "custom:7777" in m.call_args[0][0]


class TestSentinelEnabled:
    def test_enabled_strings(self, monkeypatch):
        for val in ("1", "true", "yes", "TRUE"):
            assert _reload(monkeypatch, REDIS_SENTINEL_ENABLED=val).SENTINEL_ENABLED is True

    def test_uses_sentinel_master_for(self, monkeypatch):
        mod = _reload(monkeypatch, REDIS_SENTINEL_ENABLED="1", REDIS_SENTINEL_HOSTS="s1:26379,s2:26380")
        with patch.object(mod, "_get_sentinel") as mgs:
            mgs.return_value.master_for.return_value = "sentinel_redis"
            result = mod.create_redis()
            mgs.assert_called_once()
            assert result == "sentinel_redis"

    def test_with_password(self, monkeypatch):
        mod = _reload(monkeypatch, REDIS_SENTINEL_ENABLED="1", REDIS_PASSWORD="pw")
        with patch.object(mod, "_get_sentinel") as mgs:
            mod.create_redis()
            assert mgs.return_value.master_for.call_args[1].get("password") == "pw"

    def test_no_password(self, monkeypatch):
        mod = _reload(monkeypatch, REDIS_SENTINEL_ENABLED="1")
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)
        with patch.object(mod, "_get_sentinel") as mgs:
            mod.create_redis()
            assert "password" not in mgs.return_value.master_for.call_args[1]


class TestDefaults:
    def test_hosts_default(self, monkeypatch):
        monkeypatch.delenv("REDIS_SENTINEL_HOSTS", raising=False)
        mod = _reload(monkeypatch)
        assert "sentinel-1:26379" in mod.SENTINEL_HOSTS_STR

    def test_service_default(self, monkeypatch):
        monkeypatch.delenv("REDIS_SENTINEL_SERVICE", raising=False)
        assert _reload(monkeypatch).SERVICE_NAME == "agent-studio-redis"

    def test_service_custom(self, monkeypatch):
        assert _reload(monkeypatch, REDIS_SENTINEL_SERVICE="my").SERVICE_NAME == "my"

    def test_db_default(self, monkeypatch):
        monkeypatch.delenv("REDIS_SENTINEL_DB", raising=False)
        assert _reload(monkeypatch).SENTINEL_DB == 0

    def test_db_custom(self, monkeypatch):
        assert _reload(monkeypatch, REDIS_SENTINEL_DB="5").SENTINEL_DB == 5
