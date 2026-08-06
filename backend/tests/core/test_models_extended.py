"""Additional tests for backend/core/models.py — edge cases on missed lines."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError


class TestRoleEnum:
    def test_display_name_pm(self):
        from core.models import Role

        assert Role.PM.display_name == "产品经理"

    def test_display_name_programmer(self):
        from core.models import Role

        assert Role.PROGRAMMER.display_name == "资深程序员"

    def test_display_name_tester(self):
        from core.models import Role

        assert Role.TESTER.display_name == "测试工程师"

    def test_all_roles_have_display_names(self):
        from core.models import Role

        for role in Role:
            assert role.display_name != ""


class TestMessageValidation:
    def test_content_not_empty_rejects_whitespace(self):
        from core.models import Message

        with pytest.raises(ValidationError, match="must not be empty"):
            Message(role="pm", content="   ")

    def test_content_not_empty_rejects_empty_string(self):
        from core.models import Message

        with pytest.raises(ValidationError, match="must not be empty"):
            Message(role="programmer", content="")

    def test_content_not_empty_strips_whitespace(self):
        from core.models import Message

        msg = Message(role="pm", content="  hello  ")
        assert msg.content == "hello"

    def test_content_not_empty_accepts_non_empty(self):
        from core.models import Message

        msg = Message(role="tester", content="valid content")
        assert msg.content == "valid content"


class TestAgentConfigValidation:
    def test_role_identifier_pattern_validation(self):
        from core.models import AgentConfig

        with pytest.raises(ValidationError):
            AgentConfig(
                name="Test",
                role_identifier="Invalid Role",
                system_prompt="You are helpful",
            )

    def test_role_identifier_accepts_valid(self):
        from core.models import AgentConfig

        cfg = AgentConfig(
            name="Test Agent",
            role_identifier="test_role",
            system_prompt="You are helpful",
        )
        assert cfg.role_identifier == "test_role"

    def test_name_too_long(self):
        from core.models import AgentConfig

        with pytest.raises(ValidationError):
            AgentConfig(
                name="x" * 65,
                role_identifier="test",
                system_prompt="You are helpful",
            )

    def test_temperature_out_of_range(self):
        from core.models import AgentConfig

        with pytest.raises(ValidationError):
            AgentConfig(
                name="Test",
                role_identifier="test",
                system_prompt="You are helpful",
                temperature=1.5,
            )

    def test_default_values(self):
        from core.models import AgentConfig

        cfg = AgentConfig(
            name="Test",
            role_identifier="test",
            system_prompt="You are helpful",
        )
        assert cfg.is_active is True
        assert cfg.is_approver is False
        assert cfg.order == 0
        assert cfg.icon == "🤖"
        assert cfg.model is None
        assert cfg.temperature is None


class TestMemoryEntryItemValidation:
    def test_content_type_pattern_validation(self):
        from core.models import MemoryEntryItem

        with pytest.raises(ValidationError):
            MemoryEntryItem(
                id="m1",
                agent_role="pm",
                content_type="invalid_type",
                summary="test",
                details="test",
                created_at=datetime.now(UTC),
            )

    def test_content_type_accepts_valid(self):
        from core.models import MemoryEntryItem

        for valid_type in ("pm_document", "code", "review", "decision"):
            item = MemoryEntryItem(
                id="m1",
                agent_role="pm",
                content_type=valid_type,
                summary="test",
                details="test",
                created_at=datetime.now(UTC),
            )
            assert item.content_type == valid_type


class TestSessionDetailResponse:
    def test_defaults(self):
        from core.models import SessionDetailResponse

        resp = SessionDetailResponse(
            id="s1",
            title="Test",
        )
        assert resp.runs == []
        assert resp.memories == []


class TestTeamOutput:
    def test_requirement_min_length(self):
        from core.models import TeamOutput

        with pytest.raises(ValidationError):
            TeamOutput(
                requirement="",
                pm_document="doc",
                code="code",
                review="review",
            )

    def test_valid_team_output(self):
        from core.models import TeamOutput

        output = TeamOutput(
            requirement="Build a website",
            pm_document="Design doc",
            code="<div>hello</div>",
            review="Looks good",
            approved=True,
        )
        assert output.requirement == "Build a website"
        assert output.approved is True
