"""ORM model smoke tests for P9 additions."""

import pytest
from orm.infra import AssetDB, ComposeTemplateDB
from orm.session import ProjectRun


@pytest.mark.unit
def test_project_run_has_generation_columns() -> None:
    cols = {c.name for c in ProjectRun.__table__.columns}
    assert {"content_type", "generation_mode", "topic", "result_json", "template_id"} <= cols


@pytest.mark.unit
def test_assets_table_shape() -> None:
    cols = {c.name for c in AssetDB.__table__.columns}
    assert {"id", "user_id", "name", "asset_type", "storage_path", "indexed"} <= cols


@pytest.mark.unit
def test_compose_template_table_shape() -> None:
    cols = {c.name for c in ComposeTemplateDB.__table__.columns}
    assert {"id", "name", "layout_json", "is_default"} <= cols
