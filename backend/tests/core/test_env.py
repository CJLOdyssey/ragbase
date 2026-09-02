"""Unit tests for core.env — .env loading and safe typed reads."""

from unittest.mock import patch

from core.env import env_float, env_int, load_dotenv


class TestEnvInt:
    def test_returns_value_when_env_set(self):
        with patch("core.env.os.environ", {"TEST_KEY": "42"}):
            assert env_int("TEST_KEY", 10) == 42

    def test_returns_default_on_missing_key(self):
        with patch("core.env.os.environ", {}):
            assert env_int("MISSING", 7) == 7

    def test_returns_default_on_invalid_value(self):
        with patch("core.env.os.environ", {"BAD": "xyz"}):
            assert env_int("BAD", 3) == 3


class TestEnvFloat:
    def test_returns_value_when_env_set(self):
        with patch("core.env.os.environ", {"TEST_KEY": "0.85"}):
            assert env_float("TEST_KEY", 0.7) == 0.85

    def test_returns_default_on_missing_key(self):
        with patch("core.env.os.environ", {}):
            assert env_float("MISSING", 0.5) == 0.5

    def test_returns_default_on_invalid_value(self):
        with patch("core.env.os.environ", {"BAD": "not-a-number"}):
            assert env_float("BAD", 0.3) == 0.3


class TestLoadDotenv:
    def test_loads_key_value_pairs(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\nBAZ =  qux\n")

        with patch("core.env.os.environ", {}):
            load_dotenv(env_file)
            from os import environ

            assert environ["FOO"] == "bar"
            assert environ["BAZ"] == "qux"

    def test_skips_comments_blank_and_malformed_lines(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nNO_EQUALS\n=orphan-value\nKEY=value\n")

        with patch("core.env.os.environ", {}):
            load_dotenv(env_file)
            from os import environ

            assert environ.get("NO_EQUALS") is None
            assert environ.get("KEY") == "value"

    def test_strips_surrounding_quotes(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text('QUOTED="hello world"\nSINGLE=\'abc\'\n')

        with patch("core.env.os.environ", {}):
            load_dotenv(env_file)
            from os import environ

            assert environ["QUOTED"] == "hello world"
            assert environ["SINGLE"] == "abc"

    def test_never_overrides_existing_env(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("ALREADY_SET=from-file\n")

        with patch("core.env.os.environ", {"ALREADY_SET": "from-shell"}):
            load_dotenv(env_file)
            from os import environ

            assert environ["ALREADY_SET"] == "from-shell"

    def test_missing_file_is_noop(self, tmp_path):
        with patch("core.env.os.environ", {}):
            load_dotenv(tmp_path / "does-not-exist.env")
            from os import environ

            assert environ == {}
