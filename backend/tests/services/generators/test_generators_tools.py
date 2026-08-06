"""Tests for tool code generators — PythonToolGenerator and JavascriptToolGenerator."""



from services.generators._models import GeneratedTool


class TestPythonToolGenerator:
    def test_import(self):
        from services.generators.python_tools import _generate_python_tool
        assert _generate_python_tool is not None

    def test_generate_with_read_keyword(self):
        from services.generators.python_tools import _generate_python_tool

        tool = _generate_python_tool("t1", "读取文件内容")
        assert isinstance(tool, GeneratedTool)
        assert tool.id == "t1"
        assert tool.language == "python"
        assert tool.is_valid is True
        assert "def read_file" in tool.code
        assert "read_file" in tool.name

    def test_generate_with_search_keyword(self):
        from services.generators.python_tools import _generate_python_tool

        tool = _generate_python_tool("t2", "搜索代码片段")
        assert isinstance(tool, GeneratedTool)
        assert tool.id == "t2"
        assert "def search_code" in tool.code
        assert "search_code" in tool.name

    def test_generate_with_write_keyword(self):
        from services.generators.python_tools import _generate_python_tool

        tool = _generate_python_tool("t3", "写入内容到磁盘")
        assert isinstance(tool, GeneratedTool)
        assert tool.id == "t3"
        assert "def write_file" in tool.code
        assert "write_file" in tool.name

    def test_fallback_to_custom_tool(self):
        from services.generators.python_tools import _generate_python_tool

        tool = _generate_python_tool("t4", "some completely unknown description that matches nothing")
        assert isinstance(tool, GeneratedTool)
        assert tool.id == "t4"
        assert tool.name == "custom_tool"
        assert "def custom_tool" in tool.code
        assert tool.language == "python"
        assert tool.is_valid is True

    def test_description_truncated_to_50_chars_in_fallback(self):
        from services.generators.python_tools import _generate_python_tool

        long_desc = "a" * 200
        tool = _generate_python_tool("t5", long_desc)
        assert len(tool.description) == 50

    def test_parameters_in_matched_template(self):
        from services.generators.python_tools import _generate_python_tool

        tool = _generate_python_tool("t6", "读取文件")
        assert "file_path" in tool.parameters
        assert tool.parameters["file_path"]["type"] == "string"
        assert tool.parameters["file_path"]["required"] is True

    def test_parameters_in_fallback(self):
        from services.generators.python_tools import _generate_python_tool

        tool = _generate_python_tool("t7", "nonsense no match")
        assert "input_data" in tool.parameters
        assert tool.parameters["input_data"]["type"] == "any"

    def test_generated_code_has_function_def(self):
        from services.generators.python_tools import _generate_python_tool

        tool = _generate_python_tool("t8", "读取文件内容")
        assert "def " in tool.code
        assert tool.code.strip().startswith("import") or "def " in tool.code

    def test_case_insensitive_matching(self):
        from services.generators.python_tools import _generate_python_tool

        tool = _generate_python_tool("t9", "READ THE FILE NOW")
        assert tool.name == "read_file"


class TestJavascriptToolGenerator:
    def test_import(self):
        from services.generators.javascript_tools import _generate_javascript_tool
        assert _generate_javascript_tool is not None

    def test_generate_with_read_keyword(self):
        from services.generators.javascript_tools import _generate_javascript_tool

        tool = _generate_javascript_tool("j1", "读取文件")
        assert isinstance(tool, GeneratedTool)
        assert tool.id == "j1"
        assert tool.language == "javascript"
        assert tool.is_valid is True
        assert "readFile" in tool.name
        assert "async function readFile" in tool.code

    def test_generate_with_weather_keyword(self):
        from services.generators.javascript_tools import _generate_javascript_tool

        tool = _generate_javascript_tool("j2", "查询北京天气")
        assert isinstance(tool, GeneratedTool)
        assert tool.id == "j2"
        assert "getWeather" in tool.name
        assert "async function getWeather" in tool.code

    def test_fallback_to_custom_tool(self):
        from services.generators.javascript_tools import _generate_javascript_tool

        tool = _generate_javascript_tool("j3", "something totally unmatched")
        assert isinstance(tool, GeneratedTool)
        assert tool.id == "j3"
        assert tool.name == "customTool"
        assert "async function customTool" in tool.code
        assert tool.language == "javascript"

    def test_description_truncated(self):
        from services.generators.javascript_tools import _generate_javascript_tool

        long_desc = "z" * 200
        tool = _generate_javascript_tool("j4", long_desc)
        assert len(tool.description) == 50

    def test_parameters_for_read_file(self):
        from services.generators.javascript_tools import _generate_javascript_tool

        tool = _generate_javascript_tool("j5", "file read")
        assert "filePath" in tool.parameters
        assert tool.parameters["filePath"]["type"] == "string"

    def test_parameters_for_fallback(self):
        from services.generators.javascript_tools import _generate_javascript_tool

        tool = _generate_javascript_tool("j6", "no match at all")
        assert "inputData" in tool.parameters
        assert tool.parameters["inputData"]["type"] == "any"

    def test_generated_code_has_async_function(self):
        from services.generators.javascript_tools import _generate_javascript_tool

        tool = _generate_javascript_tool("j7", "查询天气")
        assert "async function" in tool.code
        assert "module.exports" in tool.code

    def test_english_file_keyword(self):
        from services.generators.javascript_tools import _generate_javascript_tool

        tool = _generate_javascript_tool("j8", "read the file please")
        assert tool.name == "readFile"

    def test_weather_temperature_keyword(self):
        from services.generators.javascript_tools import _generate_javascript_tool

        tool = _generate_javascript_tool("j9", "当前气温是多少")
        assert tool.name == "getWeather"
