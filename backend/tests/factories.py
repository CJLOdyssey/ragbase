"""Test data factories for RagBase backend tests.

仅保留 ragbase 实际存在的资源（session/prompt）；已被裁剪模块
（agents/tools/skills/mcps/teams/workflows）的工厂不得复活。
"""

import uuid
from dataclasses import dataclass


def _uid() -> str:
    return uuid.uuid4().hex[:12]


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


# Singleton instances for convenience
session_factory = SessionFactory()
prompt_factory = PromptFactory()
