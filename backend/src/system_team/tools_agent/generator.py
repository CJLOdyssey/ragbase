"""Tool generator — creates tool code from natural language descriptions."""

import hashlib
from pathlib import Path
from typing import Any

from core.infra.logging_config import get_logger

from system_team.shared.llm import llm_client

logger = get_logger(__name__)

TOOLS_DIR = Path(__file__).parent / "tools"


class ToolGenerator:
    """Generates tool code from descriptions, with optional LLM enhancement."""

    def __init__(self) -> None:
        """Set up tools output directory."""
        self.tools_dir = TOOLS_DIR
        self.tools_dir.mkdir(exist_ok=True)

    def generate(self, description: str, language: str = "python") -> dict[str, Any]:
        """Generate a tool from description. Uses templates by default."""
        tool_id = f"tool_{hashlib.md5(description.encode(), usedforsecurity=False).hexdigest()[:8]}"

        if language == "python":
            return self._generate_python(tool_id, description)
        return self._generate_javascript(tool_id, description)

    async def generate_with_llm(self, description: str, language: str = "python") -> dict[str, Any]:
        """Generate a tool using LLM if available, falling back to templates."""
        tool_id = f"tool_{hashlib.md5(description.encode(), usedforsecurity=False).hexdigest()[:8]}"

        if llm_client.is_available():
            code = await llm_client.generate_code(description, language)
            if code:
                name = (
                    self._extract_function_name(code) or description.replace(" ", "_").lower()[:30]
                )
                return {
                    "id": tool_id,
                    "name": name,
                    "description": description[:100],
                    "code": code,
                    "language": language,
                    "parameters": {},
                    "is_valid": True,
                    "source": "llm",
                }

        return self.generate(description, language)

    @staticmethod
    def _extract_function_name(code: str) -> str | None:
        """Extract the first function name from generated code."""
        import re

        match = re.search(r"def\s+(\w+)\s*\(", code)
        return match.group(1) if match else None

    def _generate_python(self, tool_id: str, description: str) -> dict[str, Any]:
        """Dispatch to a specific Python tool template based on description keywords."""
        desc_lower = description.lower()

        if any(kw in desc_lower for kw in ["天气", "weather"]):
            return self._create_weather_tool(tool_id, description)
        if any(kw in desc_lower for kw in ["文件", "file", "读取", "read"]):
            return self._create_file_tool(tool_id, description)
        if any(kw in desc_lower for kw in ["http", "请求", "api"]):
            return self._create_http_tool(tool_id, description)

        return self._create_custom_tool(tool_id, description)

    def _generate_javascript(self, tool_id: str, description: str) -> dict[str, Any]:
        """Generate a JavaScript tool from description."""
        return self._create_custom_tool(tool_id, description, language="javascript")

    @staticmethod
    def _create_weather_tool(tool_id: str, description: str) -> dict[str, Any]:
        """Create a weather-query tool definition."""
        code = """import requests
from typing import Dict, Any

def get_weather(city: str) -> Dict[str, Any]:
    url = f"https://wttr.in/{city}?format=j1"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    current = data.get("current_condition", [{}])[0]
    return {
        "city": city,
        "temperature_c": current.get("temp_C", ""),
        "description": current.get("weatherDesc", [{}])[0].get("value", ""),
        "humidity": current.get("humidity", ""),
        "success": True
    }
"""
        return {
            "id": tool_id,
            "name": "get_weather",
            "description": "查询城市天气",
            "code": code,
            "language": "python",
            "parameters": {"city": {"type": "string", "required": True}},
            "is_valid": True,
        }

    @staticmethod
    def _create_file_tool(tool_id: str, description: str) -> dict[str, Any]:
        """Create a file-reader tool definition."""
        code = """import os

def read_file(file_path: str, encoding: str = "utf-8") -> str:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    with open(file_path, "r", encoding=encoding) as f:
        return f.read()
"""
        return {
            "id": tool_id,
            "name": "read_file",
            "description": "读取文件内容",
            "code": code,
            "language": "python",
            "parameters": {
                "file_path": {"type": "string", "required": True},
                "encoding": {"type": "string", "default": "utf-8"},
            },
            "is_valid": True,
        }

    @staticmethod
    def _create_http_tool(tool_id: str, description: str) -> dict[str, Any]:
        """Create an HTTP-request tool definition."""
        code = """import requests
from typing import Dict, Any

def http_request(url: str, method: str = "GET", headers: Dict = None) -> Dict[str, Any]:
    resp = requests.request(method, url, headers=headers, timeout=10)
    return {
        "status_code": resp.status_code,
        "text": resp.text,
        "success": resp.status_code < 400
    }
"""
        return {
            "id": tool_id,
            "name": "http_request",
            "description": "发送HTTP请求",
            "code": code,
            "language": "python",
            "parameters": {
                "url": {"type": "string", "required": True},
                "method": {"type": "string", "default": "GET"},
            },
            "is_valid": True,
        }

    @staticmethod
    def _create_custom_tool(
        tool_id: str, description: str, language: str = "python"
    ) -> dict[str, Any]:
        """Create a generic custom tool from description."""
        name = description.replace(" ", "_").lower()[:30]
        code = f'''from typing import Any

def {name}(input_data: Any = None) -> Any:
    """
    {description}
    """
    result = input_data
    return result
'''
        return {
            "id": tool_id,
            "name": name,
            "description": description[:100],
            "code": code,
            "language": language,
            "parameters": {"input_data": {"type": "any", "required": False}},
            "is_valid": True,
        }

    def save_tool(self, tool_data: dict[str, Any]) -> Path:
        """Write generated tool code to a file and return its path."""
        tool_file = self.tools_dir / f"{tool_data['name']}.py"
        tool_file.write_text(tool_data["code"], encoding="utf-8")
        logger.info("Saved tool to %s", tool_file)
        return tool_file

    def list_tools(self) -> list[dict[str, str]]:
        """List all generated tools in the tools directory."""
        tools = []
        for py_file in self.tools_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            tools.append({"name": py_file.stem, "file": py_file.name})
        return tools
