"""技能生成器测试."""

from system_team.skill_agent.generator import SkillGenerator


class TestSkillGenerator:
    def setup_method(self):
        self.generator = SkillGenerator()

    def test_generate_code_review_skill(self):
        result = self.generator.generate("代码审查规范", "code-quality")
        assert result["name"] == "code-review-standard"
        assert result["category"] == "code-quality"
        assert result["is_valid"] is True
        assert "---" in result["content"]

    def test_generate_security_skill(self):
        result = self.generator.generate("安全审计", "security")
        assert result["name"] == "security-audit"
        assert result["category"] == "security"
        assert result["is_valid"] is True

    def test_generate_api_design_skill(self):
        result = self.generator.generate("API设计规范", "architecture")
        assert result["name"] == "api-design-guidelines"
        assert result["category"] == "architecture"
        assert result["is_valid"] is True

    def test_generate_custom_skill(self):
        result = self.generator.generate("自定义技能", "general")
        assert result["category"] == "general"
        assert result["is_valid"] is True

    def test_list_skills(self):
        skills = self.generator.list_skills()
        assert isinstance(skills, list)
