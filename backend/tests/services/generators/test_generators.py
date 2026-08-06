"""Unit tests for """






class TestGeneratedToolModel:
    """Test GeneratedTool Pydantic model validation, field defaults."""

    def test_import(self):
        from services.generators._models import GeneratedTool

        assert GeneratedTool is not None

    def test_valid_tool_creation(self):
        from services.generators._models import GeneratedTool

        tool = GeneratedTool(
            id="tool-1",
            name="search_tool",
            description="A search tool",
            code="def search(): pass",
            language="python",
            parameters={"query": "str"},
            is_valid=True,
        )
        assert tool.id == "tool-1"
        assert tool.name == "search_tool"
        assert tool.error_message is None

    def test_error_message_defaults_to_none(self):
        from services.generators._models import GeneratedTool

        tool = GeneratedTool(
            id="tool-2",
            name="broken_tool",
            description="",
            code="",
            language="python",
            parameters={},
            is_valid=False,
        )
        assert tool.error_message is None

    def test_error_message_set(self):
        from services.generators._models import GeneratedTool

        tool = GeneratedTool(
            id="tool-3",
            name="failing_tool",
            description="fails",
            code="bad code",
            language="python",
            parameters={},
            is_valid=False,
            error_message="Syntax error",
        )
        assert tool.error_message == "Syntax error"

    def test_field_types(self):
        from typing import get_type_hints

        from services.generators._models import GeneratedTool

        hints = get_type_hints(GeneratedTool)
        assert hints["id"] is str
        assert hints["name"] is str
        assert hints["is_valid"] is bool


# ─────────────────────────────────────────────────────────────────────
# 9. backend/routers/keys.py — Key models & encryption
# ─────────────────────────────────────────────────────────────────────


