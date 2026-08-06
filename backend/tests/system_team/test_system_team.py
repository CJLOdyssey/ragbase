"""Tests for backend/system_team/ — LLM client, validators."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLLMClient:
    def test_import(self):
        from system_team.shared.llm import LLMClient
        assert LLMClient is not None

    def test_init_lazy_config(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        assert client._config is None

    def test_get_config_loads_on_first_call(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        with patch("system_team.shared.llm.load_config") as mock_load:
            mock_load.return_value = MagicMock(api_key="sk-test")
            config = client._get_config()
            assert config.api_key == "sk-test"
            mock_load.assert_called_once()

    def test_get_config_caches(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        with patch("system_team.shared.llm.load_config") as mock_load:
            mock_load.return_value = MagicMock(api_key="sk-test")
            config1 = client._get_config()
            config2 = client._get_config()
            assert config1 is config2
            mock_load.assert_called_once()

    def test_is_available_with_key(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        with patch.object(client, "_get_config") as mock_get:
            mock_get.return_value = MagicMock(api_key="sk-valid")
            assert client.is_available() is True

    def test_is_available_without_key(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        with patch.object(client, "_get_config") as mock_get:
            mock_get.return_value = MagicMock(api_key="")
            assert client.is_available() is False

    def test_is_available_with_none_key(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        with patch.object(client, "_get_config") as mock_get:
            mock_get.return_value = MagicMock(api_key=None)
            assert client.is_available() is False

    @pytest.mark.asyncio
    async def test_generate_code_no_key_returns_none(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        with patch.object(client, "_get_config") as mock_get:
            mock_get.return_value = MagicMock(api_key="")
            result = await client.generate_code("make a calculator")
            assert result is None

    @pytest.mark.asyncio
    async def test_generate_code_success(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        mock_config = MagicMock()
        mock_config.api_key = "sk-test"
        mock_config.api_base = "https://api.deepseek.com"
        mock_config.model = "deepseek-v4-flash"

        with patch.object(client, "_get_config", return_value=mock_config):
            with patch("system_team.shared.llm.httpx.AsyncClient") as mock_httpx:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "choices": [{"message": {"content": "def add(a, b): return a + b"}}]
                }
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.post.return_value = mock_response
                mock_httpx.return_value = mock_client

                result = await client.generate_code("add two numbers")
                assert result == "def add(a, b): return a + b"

    @pytest.mark.asyncio
    async def test_generate_code_custom_language(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        mock_config = MagicMock()
        mock_config.api_key = "sk-test"
        mock_config.api_base = "https://api.deepseek.com"
        mock_config.model = "deepseek-v4-flash"

        with patch.object(client, "_get_config", return_value=mock_config):
            with patch("system_team.shared.llm.httpx.AsyncClient") as mock_httpx:
                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "choices": [{"message": {"content": "fn main() { println!(\"hi\"); }"}}]
                }
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.post.return_value = mock_response
                mock_httpx.return_value = mock_client

                result = await client.generate_code("hello world", language="rust")
                assert "fn main()" in result

    @pytest.mark.asyncio
    async def test_generate_code_api_error_returns_none(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        mock_config = MagicMock()
        mock_config.api_key = "sk-test"
        mock_config.api_base = "https://api.deepseek.com"
        mock_config.model = "deepseek-v4-flash"

        with patch.object(client, "_get_config", return_value=mock_config):
            with patch("system_team.shared.llm.httpx.AsyncClient") as mock_httpx:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.post.side_effect = Exception("API error")
                mock_httpx.return_value = mock_client

                result = await client.generate_code("test")
                assert result is None

    def test_extract_code_from_python_fence(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        content = "Some text\n```python\ndef foo():\n    pass\n```\nmore"
        result = client._extract_code(content)
        assert result == "def foo():\n    pass"

    def test_extract_code_from_generic_fence(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        content = "```\nconsole.log('hi')\n```"
        result = client._extract_code(content)
        assert result == "console.log('hi')"

    def test_extract_code_no_fence(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        content = "  just plain code  "
        result = client._extract_code(content)
        assert result == "just plain code"

    def test_extract_code_empty(self):
        from system_team.shared.llm import LLMClient

        client = LLMClient()
        result = client._extract_code("")
        assert result == ""

    def test_llm_client_singleton(self):
        from system_team.shared.llm import llm_client

        assert llm_client is not None
        assert hasattr(llm_client, "generate_code")


class TestSkillValidator:
    def test_import(self):
        from system_team.skill_agent.validator import SkillValidator
        assert SkillValidator is not None

    def test_validate_valid_content(self):
        from system_team.skill_agent.validator import SkillValidator

        validator = SkillValidator()
        content = "---\nname: test-skill\ndescription: A test skill\n---\n\n# My Skill\n\n## Section\n\nContent here that is quite long and definitely exceeds one hundred characters by a significant margin."
        result = validator.validate(content)
        assert result["is_valid"] is True
        assert len(result["suggestions"]) == 0

    def test_validate_missing_frontmatter(self):
        from system_team.skill_agent.validator import SkillValidator

        validator = SkillValidator()
        content = "# Just a heading\n\nSome content"
        result = validator.validate(content)
        assert result["is_valid"] is False
        assert any("缺少" in s for s in result["suggestions"])

    def test_validate_missing_name(self):
        from system_team.skill_agent.validator import SkillValidator

        validator = SkillValidator()
        content = "---\ndescription: test\n---\n\n# Heading\n\n## Section\nLong enough content that passes the minimum length threshold easily with room to spare."
        result = validator.validate(content)
        assert result["is_valid"] is False
        assert any("name" in s for s in result["suggestions"])

    def test_validate_missing_description(self):
        from system_team.skill_agent.validator import SkillValidator

        validator = SkillValidator()
        content = "---\nname: test\n---\n\n# Heading\n\n## Section\nLong enough content that passes the minimum length threshold easily with room to spare."
        result = validator.validate(content)
        assert result["is_valid"] is False
        assert any("description" in s for s in result["suggestions"])

    def test_validate_missing_headings(self):
        from system_team.skill_agent.validator import SkillValidator

        validator = SkillValidator()
        content = "---\nname: test\ndescription: test\n---\n\nNo headings here at all just plain text that continues for quite a while to make sure we pass the minimum length threshold for this test case."
        result = validator.validate(content)
        assert any("一级标题" in s for s in result["suggestions"])
        assert any("二级标题" in s for s in result["suggestions"])

    def test_validate_short_content(self):
        from system_team.skill_agent.validator import SkillValidator

        validator = SkillValidator()
        content = "---\nname: test\ndescription: test\n---\n\nShort"
        result = validator.validate(content)
        assert any("较短" in s for s in result["suggestions"])

    def test_validate_empty(self):
        from system_team.skill_agent.validator import SkillValidator

        validator = SkillValidator()
        result = validator.validate("")
        assert result["is_valid"] is False
        assert len(result["suggestions"]) > 0
