"""Unit tests for backend/services/tool_generator.py."""


import pytest

from services.tool_generator import (
    ToolValidateRequest,
    ToolValidateResponse,
    _execute_tool_sandbox,
    _validate_tool_code,
)


class TestToolValidateRequest:
    def test_default_language(self):
        req = ToolValidateRequest(code="def foo(): pass")
        assert req.language == "python"

    def test_custom_language(self):
        req = ToolValidateRequest(code="function foo() {}", language="javascript")
        assert req.language == "javascript"


class TestToolValidateResponse:
    def test_valid_defaults(self):
        resp = ToolValidateResponse(is_valid=True)
        assert resp.error_message is None
        assert resp.suggestions == []

    def test_invalid_with_error(self):
        resp = ToolValidateResponse(is_valid=False, error_message="bad code", suggestions=["fix it"])
        assert resp.error_message == "bad code"
        assert resp.suggestions == ["fix it"]


class TestValidateToolCode:
    def test_python_complete_code(self):
        code = '''"""
My tool.
"""
import os

def my_tool(x: int) -> int:
    try:
        return x * 2
    except Exception:
        return 0
'''
        resp = _validate_tool_code(code, "python")
        assert resp.is_valid is True

    def test_python_missing_docstring(self):
        code = "def foo(): pass"
        resp = _validate_tool_code(code, "python")
        suggestions = " ".join(resp.suggestions)
        assert "建议添加文档字符串" in suggestions

    def test_python_missing_def(self):
        code = "x = 1"
        resp = _validate_tool_code(code, "python")
        assert "建议添加函数定义" in " ".join(resp.suggestions)

    def test_python_missing_import_check(self):
        code = "def foo(): pass"
        resp = _validate_tool_code(code, "python")
        assert "检查是否需要导入模块" in " ".join(resp.suggestions)

    def test_python_missing_try_except(self):
        code = "def foo(): pass"
        resp = _validate_tool_code(code, "python")
        assert "建议添加异常处理" in " ".join(resp.suggestions)

    def test_javascript_complete_code(self):
        code = """/**
 * My function.
 */
function myTool(x) {
    try {
        return x * 2;
    } catch (e) {
        return 0;
    }
}
"""
        resp = _validate_tool_code(code, "javascript")
        assert resp.is_valid is True

    def test_javascript_missing_jsdoc(self):
        code = "function foo() { return 1; }"
        resp = _validate_tool_code(code, "javascript")
        assert "建议添加JSDoc注释" in " ".join(resp.suggestions)

    def test_javascript_missing_function(self):
        code = "const x = 1;"
        resp = _validate_tool_code(code, "javascript")
        assert "建议添加函数定义" in " ".join(resp.suggestions)

    def test_javascript_missing_try_catch(self):
        code = "function foo() { return 1; }"
        resp = _validate_tool_code(code, "javascript")
        assert "建议添加异常处理" in " ".join(resp.suggestions)

    def test_unknown_language_no_validation(self):
        code = "some code"
        resp = _validate_tool_code(code, "ruby")
        assert resp.is_valid is True
        assert resp.suggestions == []


class TestExecuteToolSandbox:
    def test_valid_python_code(self):
        result = _execute_tool_sandbox("x = 1", "python")
        assert "语法检查通过" in result

    def test_invalid_syntax(self):
        with pytest.raises(Exception) as exc:
            _execute_tool_sandbox("def foo(:", "python")
        assert "语法错误" in str(exc.value)

    def test_javascript_returns_message(self):
        result = _execute_tool_sandbox("function f() {}", "javascript")
        assert "需要Node.js环境" in result
