"""Python tool code generator.

Dispatches to template definitions in :mod:`python_templates` based on
keyword matching.  The fallback produces a minimal stub.
"""

from services.generators._models import GeneratedTool
from services.generators.python_templates import TOOL_TEMPLATES


def _generate_python_tool(tool_id: str, description: str) -> GeneratedTool:
    """Return a :class:`GeneratedTool` matching *description*.

    Iterates over :data:`TOOL_TEMPLATES` and picks the first template
    whose keyword list intersects the description (case-insensitive).
    If none match, a generic ``custom_tool`` stub is returned.
    """
    desc_lower = description.lower()

    for tpl in TOOL_TEMPLATES:
        if any(kw in desc_lower for kw in tpl["keywords"]):
            return GeneratedTool(
                id=tool_id,
                name=tpl["name"],
                description=tpl["desc"],
                code=tpl["code"],
                language="python",
                parameters=tpl["params"],
                is_valid=True,
            )

    # ── Fallback: custom_tool stub ────────────────────────────────
    name = "custom_tool"
    code = f'''from typing import Any

def custom_tool(input_data: Any = None) -> Any:
    """
    {description}

    Args:
        input_data: 输入数据

    Returns:
        处理结果
    """
    result = input_data
    return result
'''

    return GeneratedTool(
        id=tool_id,
        name=name,
        description=description[:50],
        code=code,
        language="python",
        parameters={"input_data": {"type": "any", "required": False}},
        is_valid=True,
    )
