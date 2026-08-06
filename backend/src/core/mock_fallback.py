"""Mock fallback for agent runs — returns canned responses when LLM is unavailable."""

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

from streaming.emitter import StreamEmitter

logger = logging.getLogger(__name__)

ENABLE = os.environ.get("ENABLE_MOCK_FALLBACK", "0") == "1"


async def run_mock(requirement: str, run_id: str, session_id: str | None) -> Any:
    """Run a mock agent pipeline with canned response messages."""
    emitter = StreamEmitter(run_id)
    messages = [
        f"收到需求：{requirement[:100]}",
        "正在分析需求...",
        "根据分析，这是一个标准的软件开发需求。",
        "建议采用模块化设计，优先实现核心功能。",
        "需求分析完成。",
    ]
    for msg in messages:
        await emitter._emit("Agent", msg)
        await asyncio.sleep(0.5)

    @dataclass
    class MockOutput:
        response: str = ""
        status: str = "converged"
        approved: bool = False

    return MockOutput(response="\n".join(messages), approved=True)
