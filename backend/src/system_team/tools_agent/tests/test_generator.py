"""工具生成器测试."""

from system_team.tools_agent.generator import ToolGenerator


class TestToolGenerator:
    def setup_method(self):
        self.generator = ToolGenerator()

    def test_generate_weather_tool(self):
        result = self.generator.generate("查询天气", "python")
        assert result["name"] == "get_weather"
        assert result["language"] == "python"
        assert result["is_valid"] is True

    def test_generate_file_tool(self):
        result = self.generator.generate("读取文件", "python")
        assert result["name"] == "read_file"
        assert result["language"] == "python"
        assert result["is_valid"] is True

    def test_generate_http_tool(self):
        result = self.generator.generate("HTTP请求", "python")
        assert result["name"] == "http_request"
        assert result["language"] == "python"
        assert result["is_valid"] is True

    def test_generate_custom_tool(self):
        result = self.generator.generate("自定义功能", "python")
        assert result["language"] == "python"
        assert result["is_valid"] is True

    def test_list_tools(self):
        tools = self.generator.list_tools()
        assert isinstance(tools, list)
