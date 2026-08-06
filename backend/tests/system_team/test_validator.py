"""Tests for tool code validator (backend/system_team/tools_agent/validator.py)."""

from system_team.tools_agent.validator import ToolValidator


class TestToolValidator:
    def setup_method(self):
        self.v = ToolValidator()

    def test_validate_valid_python(self):
        code = 'def hello():\n    """Say hello."""\n    import os\n    try:\n        return "hi"\n    except Exception:\n        pass'
        result = self.v.validate(code)
        assert result["is_valid"] is True

    def test_validate_missing_function(self):
        result = self.v.validate("x = 1")
        assert result["is_valid"] is False
        assert any("缺少函数定义" in s for s in result["suggestions"])

    def test_validate_suggests_docstring(self):
        code = "def f():\n    return 1"
        result = self.v.validate(code)
        assert any("文档字符串" in s for s in result["suggestions"])

    def test_validate_suggests_error_handling(self):
        code = "def f():\n    pass"
        result = self.v.validate(code)
        assert any("异常处理" in s for s in result["suggestions"])

    def test_validate_javascript_valid(self):
        code = "/** JSDoc */\nfunction hello() { try { return 'hi' } catch(e) {} }"
        result = self.v.validate(code, language="javascript")
        assert result["is_valid"] is True

    def test_validate_javascript_missing_function(self):
        result = self.v.validate("x = 1", language="javascript")
        assert result["is_valid"] is False

    def test_validate_typescript(self):
        code = "/** doc */\nconst f = () => { try { } catch(e) { } }"
        result = self.v.validate(code, language="typescript")
        assert result["is_valid"] is True

    def test_validate_unknown_language(self):
        result = self.v.validate("code", language="ruby")
        assert result["is_valid"] is True
        assert result["suggestions"] == []

    def test_empty_code(self):
        result = self.v.validate("")
        assert result["is_valid"] is False
