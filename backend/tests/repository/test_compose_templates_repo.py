"""Compose template repository tests."""

import pytest
from orm.infra import ComposeTemplateDB
from repository.compose_templates import get_template, list_templates

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_list_and_get_templates(db_engine) -> None:
    async with db_engine.begin() as conn:
        await conn.execute(
            ComposeTemplateDB.__table__.insert().values(
                id="square", name="square",
                layout_json={"canvas": {"ratio": "1:1"}}, is_default=False,
            )
        )

    templates = await list_templates()
    assert [t.name for t in templates] == ["square"]
    tpl = await get_template("square")
    assert tpl is not None and tpl.layout_json["canvas"]["ratio"] == "1:1"
    assert await get_template("missing") is None
