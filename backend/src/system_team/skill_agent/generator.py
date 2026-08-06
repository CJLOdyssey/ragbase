"""Skill generator — creates skill definitions from natural language descriptions."""

import hashlib
from pathlib import Path
from typing import Any

from core.infra.logging_config import get_logger

logger = get_logger(__name__)

SKILLS_DIR = Path(__file__).parent / "skills"
TEMPLATES_DIR = Path(__file__).parent / "templates"


class SkillGenerator:
    """Generates skill definitions from descriptions and categories."""

    def __init__(self) -> None:
        """Set up skills and templates directories."""
        self.skills_dir = SKILLS_DIR
        self.templates_dir = TEMPLATES_DIR
        self.skills_dir.mkdir(exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)

    def generate(self, description: str, category: str = "general") -> dict[str, Any]:
        """Generate a skill definition matching the given description and category."""
        skill_id = f"skill_{hashlib.md5(description.encode(), usedforsecurity=False).hexdigest()[:8]}"

        if any(kw in description.lower() for kw in ["代码审查", "code review"]):
            return self._create_code_review_skill(skill_id, description)
        if any(kw in description.lower() for kw in ["安全", "security"]):
            return self._create_security_skill(skill_id, description)
        if any(kw in description.lower() for kw in ["api", "接口"]):
            return self._create_api_design_skill(skill_id, description)
        if any(kw in description.lower() for kw in ["测试", "test"]):
            return self._create_testing_skill(skill_id, description)
        if any(kw in description.lower() for kw in ["性能", "performance"]):
            return self._create_performance_skill(skill_id, description)

        return self._create_custom_skill(skill_id, description, category)

    @staticmethod
    def _create_code_review_skill(skill_id: str, description: str) -> dict[str, Any]:
        """Create a code-review skill definition."""
        content = """---
name: code-review-standard
description: 专业代码审查能力，检查安全漏洞、性能问题、命名规范
version: "1.0"
metadata:
  author: system
  category: code-quality
---

# 代码审查规范

## 审查流程

### 1. 安全性检查
- SQL 注入风险
- XSS 漏洞
- 硬编码密钥

### 2. 性能检查
- N+1 查询问题
- 内存泄漏风险

### 3. 代码质量
- 命名规范
- 函数长度
- 异常处理
"""
        return {
            "id": skill_id,
            "name": "code-review-standard",
            "description": "专业代码审查能力",
            "content": content,
            "category": "code-quality",
            "is_valid": True,
        }

    @staticmethod
    def _create_security_skill(skill_id: str, description: str) -> dict[str, Any]:
        """Create a security-audit skill definition."""
        content = """---
name: security-audit
description: 安全审计能力，检查代码中的安全漏洞和风险
version: "1.0"
metadata:
  author: system
  category: security
---

# 安全审计规范

## 审查清单

### 1. 输入验证
- SQL 注入风险
- XSS 漏洞

### 2. 认证与授权
- 密码加密存储
- 权限校验

### 3. 敏感数据
- 硬编码密钥
- 日志泄露
"""
        return {
            "id": skill_id,
            "name": "security-audit",
            "description": "安全审计能力",
            "content": content,
            "category": "security",
            "is_valid": True,
        }

    @staticmethod
    def _create_api_design_skill(skill_id: str, description: str) -> dict[str, Any]:
        """Create an API design guidelines skill definition."""
        content = """---
name: api-design-guidelines
description: API 设计规范，遵循 RESTful 最佳实践
version: "1.0"
metadata:
  author: system
  category: architecture
---

# API 设计规范

## 设计原则

### 1. RESTful 规范
- 使用正确的 HTTP 方法
- 资源命名用复数名词

### 2. 请求/响应格式
- 统一响应结构
- 清晰的错误信息

### 3. 分页规范
- 游标分页
- 偏移分页
"""
        return {
            "id": skill_id,
            "name": "api-design-guidelines",
            "description": "API 设计规范",
            "content": content,
            "category": "architecture",
            "is_valid": True,
        }

    @staticmethod
    def _create_testing_skill(skill_id: str, description: str) -> dict[str, Any]:
        """Create a testing-standards skill definition."""
        content = """---
name: testing-standards
description: 测试规范，覆盖单元测试、集成测试、E2E 测试
version: "1.0"
metadata:
  author: system
  category: quality-assurance
---

# 测试规范

## 测试金字塔

### 1. 单元测试 (70%)
- 覆盖核心业务逻辑
- 使用 Mock 隔离

### 2. 集成测试 (20%)
- 测试模块间交互

### 3. E2E 测试 (10%)
- 测试关键用户流程
"""
        return {
            "id": skill_id,
            "name": "testing-standards",
            "description": "测试规范",
            "content": content,
            "category": "quality-assurance",
            "is_valid": True,
        }

    @staticmethod
    def _create_performance_skill(skill_id: str, description: str) -> dict[str, Any]:
        """Create a performance-optimization skill definition."""
        content = """---
name: performance-optimization
description: 性能优化规范，识别和解决性能瓶颈
version: "1.0"
metadata:
  author: system
  category: performance
---

# 性能优化规范

## 性能检查项

### 1. 数据库优化
- N+1 查询问题
- 缺少索引

### 2. 缓存策略
- 热点数据缓存
- 缓存穿透防护

### 3. 并发处理
- 异步任务队列
"""
        return {
            "id": skill_id,
            "name": "performance-optimization",
            "description": "性能优化规范",
            "content": content,
            "category": "performance",
            "is_valid": True,
        }

    @staticmethod
    def _create_custom_skill(
        skill_id: str, description: str, category: str
    ) -> dict[str, Any]:
        """Create a generic skill from description and category."""
        skill_name = description.replace(" ", "-").lower()[:30]
        content = f"""---
name: {skill_name}
description: {description}
version: "1.0"
metadata:
  author: system
  category: {category}
---

# {description}

## 使用场景
{description}

## 执行步骤

### 1. 分析阶段
- 理解需求

### 2. 执行阶段
- 按规范执行

### 3. 验证阶段
- 检查结果
"""
        return {
            "id": skill_id,
            "name": skill_name,
            "description": description[:100],
            "content": content,
            "category": category,
            "is_valid": True,
        }

    def save_skill(self, skill_data: dict[str, Any]) -> Path:
        """Write skill content to a markdown file and return its path."""
        skill_file = self.skills_dir / f"{skill_data['name']}.md"
        skill_file.write_text(skill_data["content"], encoding="utf-8")
        logger.info("Saved skill to %s", skill_file)
        return skill_file

    def list_skills(self) -> list[dict[str, str]]:
        """List all skills in the skills directory."""
        skills = []
        for md_file in self.skills_dir.glob("*.md"):
            if md_file.name.startswith("_"):
                continue
            skills.append({"name": md_file.stem, "file": md_file.name})
        return skills
