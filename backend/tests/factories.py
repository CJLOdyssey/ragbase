"""Test data factories for AgentStudio backend tests."""

import uuid
from dataclasses import dataclass, field
from typing import Optional


def _uid() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class AgentFactory:
    name: str = ""
    role_identifier: str = ""
    system_prompt: str = "You are a helpful assistant."
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    is_active: bool = True
    is_approver: bool = False
    icon: str = "🤖"

    def build(self, **overrides) -> dict:
        data = {
            "name": self.name or f"test-agent-{_uid()}",
            "role_identifier": self.role_identifier or f"role_{_uid()}",
            "system_prompt": self.system_prompt,
            "model": self.model,
            "temperature": self.temperature,
            "is_active": self.is_active,
            "is_approver": self.is_approver,
            "icon": self.icon,
        }
        data.update(overrides)
        return data


@dataclass
class TeamFactory:
    name: str = ""
    description: str = "A test team"

    def build(self, **overrides) -> dict:
        data = {
            "name": self.name or f"test-team-{_uid()}",
            "description": self.description,
        }
        data.update(overrides)
        return data


@dataclass
class SessionFactory:
    title: str = ""

    def build(self, **overrides) -> dict:
        data = {
            "title": self.title or f"test-session-{_uid()}",
        }
        data.update(overrides)
        return data


@dataclass
class ToolFactory:
    name: str = ""
    category: str = "api"
    description: str = "A test tool"

    def build(self, **overrides) -> dict:
        data = {
            "name": self.name or f"test-tool-{_uid()}",
            "category": self.category,
            "description": self.description,
        }
        data.update(overrides)
        return data


@dataclass
class PromptFactory:
    name: str = ""
    content: str = "You are a helpful assistant."
    category: str = "general"

    def build(self, **overrides) -> dict:
        data = {
            "name": self.name or f"test-prompt-{_uid()}",
            "content": self.content,
            "category": self.category,
        }
        data.update(overrides)
        return data


@dataclass
class SkillFactory:
    name: str = ""
    category: str = "general"
    description: str = "A test skill"

    def build(self, **overrides) -> dict:
        data = {
            "name": self.name or f"test-skill-{_uid()}",
            "category": self.category,
            "description": self.description,
        }
        data.update(overrides)
        return data


@dataclass
class McpFactory:
    name: str = ""
    server_type: str = "stdio"
    command: str = "python"
    args: list = field(default_factory=lambda: ["-m", "mcp"])

    def build(self, **overrides) -> dict:
        data = {
            "name": self.name or f"test-mcp-{_uid()}",
            "type": self.server_type,
            "command": self.command,
            "args": self.args,
            "env": {},
        }
        data.update(overrides)
        return data


# Singleton instances for convenience
agent_factory = AgentFactory()
team_factory = TeamFactory()
session_factory = SessionFactory()
tool_factory = ToolFactory()
prompt_factory = PromptFactory()
skill_factory = SkillFactory()
mcp_factory = McpFactory()
