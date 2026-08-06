"""Python tool template definitions — extracted from python_tools.py.

Each template is a dict with keys:
  keywords  — trigger words for keyword matching
  name      — generated function name
  desc      — short description
  code      — function source string
  params    — JSON Schema parameter definitions
"""

from typing import Any

ToolTemplate = dict[str, Any]

TOOL_TEMPLATES: list[ToolTemplate] = [
    # ── read_file ─────────────────────────────────────────────────
    {
        "keywords": ["读取", "read", "文件", "file"],
        "name": "read_file",
        "desc": "读取文件内容",
        "code": '''import os
from typing import Optional

def read_file(file_path: str, encoding: str = "utf-8") -> str:
    """
    读取文件内容

    Args:
        file_path: 文件路径
        encoding: 文件编码，默认UTF-8

    Returns:
        文件内容字符串
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    with open(file_path, "r", encoding=encoding) as f:
        return f.read()
''',
        "params": {
            "file_path": {"type": "string", "required": True},
            "encoding": {"type": "string", "default": "utf-8"},
        },
    },
    # ── write_file ────────────────────────────────────────────────
    {
        "keywords": ["写入", "write", "保存", "save"],
        "name": "write_file",
        "desc": "写入内容到文件",
        "code": '''import os
from typing import Optional

def write_file(file_path: str, content: str, encoding: str = "utf-8", append: bool = False) -> bool:
    """
    写入内容到文件

    Args:
        file_path: 文件路径
        content: 要写入的内容
        encoding: 文件编码，默认UTF-8
        append: 是否追加模式，默认False（覆盖写入）

    Returns:
        是否写入成功
    """
    try:
        mode = "a" if append else "w"
        parent_dir = os.path.dirname(file_path) or "."
        os.makedirs(parent_dir, exist_ok=True)
        with open(file_path, mode, encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        raise Exception(f"写入文件失败: {e}")
''',
        "params": {
            "file_path": {"type": "string", "required": True},
            "content": {"type": "string", "required": True},
            "encoding": {"type": "string", "default": "utf-8"},
            "append": {"type": "boolean", "default": False},
        },
    },
    # ── search_code ───────────────────────────────────────────────
    {
        "keywords": ["搜索", "search", "grep", "查找", "find"],
        "name": "search_code",
        "desc": "搜索代码中的内容",
        "code": '''import os
import re
from typing import List, Dict

def search_code(directory: str, pattern: str, file_extension: str = None) -> List[Dict]:
    """
    在代码目录中搜索匹配的内容

    Args:
        directory: 搜索目录
        pattern: 搜索模式（支持正则表达式）
        file_extension: 文件扩展名过滤，如.py, .js

    Returns:
        包含文件路径、行号、内容的列表
    """
    results = []
    regex = re.compile(pattern)

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file_extension and not file.endswith(file_extension):
                continue
            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_num, line in enumerate(f, 1):
                        if regex.search(line):
                            results.append({
                                "file": file_path,
                                "line": line_num,
                                "content": line.strip()
                            })
            except Exception:
                continue

    return results
''',
        "params": {
            "directory": {"type": "string", "required": True},
            "pattern": {"type": "string", "required": True},
            "file_extension": {"type": "string", "required": False},
        },
    },
    # ── run_command ───────────────────────────────────────────────
    {
        "keywords": ["执行", "exec", "运行", "run", "命令", "command", "shell"],
        "name": "run_command",
        "desc": "执行Shell命令",
        "code": '''import subprocess
from typing import Optional

def run_command(command: str, cwd: str = None, timeout: int = 60) -> dict:
    """
    执行Shell命令并返回结果

    Args:
        command: 要执行的命令
        cwd: 工作目录
        timeout: 超时时间（秒），默认60秒

    Returns:
        包含stdout、stderr、returncode的字典
    """
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "命令执行超时", "returncode": -1, "success": False}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1, "success": False}
''',
        "params": {
            "command": {"type": "string", "required": True},
            "cwd": {"type": "string", "required": False},
            "timeout": {"type": "integer", "default": 60},
        },
    },
    # ── http_request ──────────────────────────────────────────────
    {
        "keywords": ["http", "请求", "request", "api", "接口"],
        "name": "http_request",
        "desc": "发送HTTP请求",
        "code": '''import requests
from typing import Optional, Dict, Any

def http_request(
    url: str,
    method: str = "GET",
    headers: Dict = None,
    data: Any = None,
    json_data: Any = None,
    timeout: int = 30,
) -> Dict:
    """
    发送HTTP请求

    Args:
        url: 请求URL
        method: 请求方法，默认GET
        headers: 请求头
        data: 表单数据
        json_data: JSON数据
        timeout: 超时时间（秒），默认30秒

    Returns:
        包含status_code、headers、text、json的字典
    """
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            json=json_data,
            timeout=timeout
        )
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "text": response.text,
            "json": (
                response.json()
                if response.headers.get("content-type", "").startswith("application/json")
                else None
            ),
            "success": 200 <= response.status_code < 300
        }
    except requests.RequestException as e:
        return {"status_code": 0, "headers": {}, "text": str(e), "json": None, "success": False}
''',
        "params": {
            "url": {"type": "string", "required": True},
            "method": {"type": "string", "default": "GET"},
            "headers": {"type": "object", "required": False},
            "json_data": {"type": "object", "required": False},
        },
    },
    # ── parse_json ────────────────────────────────────────────────
    {
        "keywords": ["json", "解析", "parse"],
        "name": "parse_json",
        "desc": "解析JSON数据",
        "code": '''import json
from typing import Any

def parse_json(json_string: str) -> Any:
    """
    解析JSON字符串

    Args:
        json_string: JSON字符串

    Returns:
        解析后的Python对象
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON解析失败: {e}")
''',
        "params": {"json_string": {"type": "string", "required": True}},
    },
    # ── get_weather ───────────────────────────────────────────────
    {
        "keywords": ["天气", "weather", "气温", "温度", "forecast"],
        "name": "get_weather",
        "desc": "查询城市天气信息",
        "code": '''import requests
from typing import Dict, Any

def get_weather(city: str, api_key: str = None) -> Dict[str, Any]:
    """
    查询指定城市的天气信息（使用 OpenWeatherMap API）

    Args:
        city: 城市名称（英文），如 "Beijing", "Shanghai"
        api_key: OpenWeatherMap API Key，不传则使用免费接口

    Returns:
        包含温度、天气状况、湿度等信息的字典
    """
    if not api_key:
        url = f"https://wttr.in/{city}?format=j1"
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            current = data.get("current_condition", [{}])[0]
            return {
                "city": city,
                "temperature": current.get("temp_C", ""),
                "weather": current.get("weatherDesc", [{}])[0].get("value", ""),
                "humidity": current.get("humidity", ""),
                "wind_speed": current.get("windspeedKmph", ""),
                "pressure": data.get("main", {}).get("pressure", ""),
                "success": True
            }
        except Exception as e:
            return {"city": city, "success": False, "error": str(e)}
''',
        "params": {
            "city": {"type": "string", "required": True},
            "api_key": {"type": "string", "required": False},
        },
    },
    # ── query_database ────────────────────────────────────────────
    {
        "keywords": ["数据库", "database", "sql"],
        "name": "query_database",
        "desc": "执行SQL查询",
        "code": '''import sqlite3
from typing import List, Dict

def query_database(db_path: str, query: str, params: tuple = None) -> List[Dict]:
    """
    执行SQL查询并返回结果

    Args:
        db_path: 数据库文件路径
        query: SQL查询语句
        params: 查询参数

    Returns:
        查询结果列表
    """
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        if query.strip().upper().startswith("SELECT"):
            results = [dict(row) for row in cursor.fetchall()]
        else:
            conn.commit()
            results = [{"affected_rows": cursor.rowcount}]

        conn.close()
        return results
    except Exception as e:
        raise Exception(f"数据库查询失败: {e}")
''',
        "params": {
            "db_path": {"type": "string", "required": True},
            "query": {"type": "string", "required": True},
            "params": {"type": "tuple", "required": False},
        },
    },
]
