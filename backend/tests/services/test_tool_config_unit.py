"""Unit tests for _ToolWrapper init and build_tool_definition."""
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

from services.tool_config import ToolConfig, _ToolWrapper, build_tool_definition, sanitize_tool_name

_API_NAME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _sanitize_under_seed(seed: str, name: str) -> str:
    """Run sanitize_tool_name in a fresh process under a fixed PYTHONHASHSEED."""
    src_dir = Path(__file__).resolve().parents[2] / "src"
    env = dict(os.environ, PYTHONPATH=str(src_dir), PYTHONHASHSEED=seed)
    code = (
        "from services.tool_config import sanitize_tool_name as s; "
        "import sys; print(s(sys.argv[1]))"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code, name],
        capture_output=True, text=True, env=env, timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


class TestSanitizeToolName:
    def test_allows_alphanumeric_and_underscores(self):
        assert sanitize_tool_name("hello_world-123") == "hello_world-123"

    def test_strips_special_chars(self):
        assert sanitize_tool_name("foo@bar#baz") == "foobarbaz"

    def test_empty_fallback_is_regex_compliant(self):
        name = sanitize_tool_name("!!!")
        assert name.startswith("tool_")
        assert _API_NAME_RE.fullmatch(name)

    def test_cjk_fallback_matches_known_digest(self):
        out = sanitize_tool_name("中文工具")
        assert out == f"tool_{hashlib.sha256('中文工具'.encode()).hexdigest()[:8]}"
        assert _API_NAME_RE.fullmatch(out)

    def test_cjk_fallback_is_stable_across_calls(self):
        assert sanitize_tool_name("中文工具") == sanitize_tool_name("中文工具")

    def test_cjk_fallback_is_stable_across_hash_seeds(self):
        outputs = {_sanitize_under_seed(str(seed), "中文工具") for seed in (1, 2, 42, 314159)}
        assert len(outputs) == 1
        assert _API_NAME_RE.fullmatch(next(iter(outputs)))


class TestToolWrapperInit:
    def test_sets_all_fields(self):
        tw = _ToolWrapper(
            name="test_tool",
            description="A test",
            instructions="do stuff",
            mcp_type="remote",
            mcp_endpoint="https://mcp.example.com",
            mcp_tool_name="my_tool",
            endpoint="https://api.example.com",
            method="POST",
            headers='{"X-Api-Key": "secret"}',
        )
        assert tw.name == "test_tool"
        assert tw.description == "A test"
        assert tw.mcp_type == "remote"
        assert tw.mcp_endpoint == "https://mcp.example.com"
        assert tw.endpoint == "https://api.example.com"

    def test_llm_and_run_id_default_none(self):
        tw = _ToolWrapper(name="t")
        assert tw._llm is None
        assert tw._run_id is None


class TestResolveHandler:
    def test_mcp_when_mcp_type(self):
        tw = _ToolWrapper(name="t", mcp_type="remote")
        assert tw._resolve_handler() == "mcp"

    def test_http_when_endpoint_is_url(self):
        tw = _ToolWrapper(name="t", endpoint="https://api.example.com")
        assert tw._resolve_handler() == "http"

    def test_skill_when_instructions(self):
        tw = _ToolWrapper(name="t", instructions="do something")
        assert tw._resolve_handler() == "skill"

    def test_none_when_no_fields(self):
        tw = _ToolWrapper(name="t")
        assert tw._resolve_handler() is None


class TestBuildToolDefinition:
    def test_builds_wrapper_and_definition(self):
        tc = ToolConfig(name="my_api", description="Call API", endpoint="https://api.example.com")
        llm = MagicMock()
        api_name, wrapper, definition = build_tool_definition(tc, llm=llm)
        assert api_name == "my_api"
        assert isinstance(wrapper, _ToolWrapper)
        assert wrapper._llm is llm
        assert definition["type"] == "function"
        assert definition["function"]["name"] == "my_api"
        assert definition["function"]["description"] == "Call API"
