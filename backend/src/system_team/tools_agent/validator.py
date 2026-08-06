"""Tool code validator — checks generated code for quality and completeness."""

from typing import Any

from core.infra.logging_config import get_logger

logger = get_logger(__name__)


class ToolValidator:
    """Validates generated tool code for structural issues."""

    def validate(self, code: str, language: str = "python") -> dict[str, Any]:
        """Validate generated code and return suggestions for improvement."""
        suggestions = []

        if language == "python":
            suggestions = self._validate_python(code)
        elif language in ["javascript", "typescript"]:
            suggestions = self._validate_javascript(code)

        is_valid = len([s for s in suggestions if "缺少" in s]) == 0

        return {
            "is_valid": is_valid,
            "suggestions": suggestions,
        }

    @staticmethod
    def _validate_python(code: str) -> list[str]:
        """Check Python code for missing definitions, imports, and error handling."""
        suggestions = []

        if "def " not in code:
            suggestions.append("缺少函数定义")

        if '"""' not in code and "'''" not in code:
            suggestions.append("建议添加文档字符串")

        if "import" not in code:
            suggestions.append("检查是否需要导入模块")

        if "try" not in code and "except" not in code:
            suggestions.append("建议添加异常处理")

        return suggestions

    @staticmethod
    def _validate_javascript(code: str) -> list[str]:
        """Check JavaScript code for missing definitions and error handling."""
        suggestions = []

        if "function " not in code and "=>" not in code:
            suggestions.append("缺少函数定义")

        if "/**" not in code:
            suggestions.append("建议添加JSDoc注释")

        if "try" not in code and "catch" not in code:
            suggestions.append("建议添加异常处理")

        return suggestions
