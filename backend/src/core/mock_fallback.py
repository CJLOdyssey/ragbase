"""Mock fallback for agent runs — canned responses when the LLM is unavailable.

Enabled via ``ENABLE_MOCK_FALLBACK=1`` (see tasks/registry.py).
"""

import asyncio
import os
from dataclasses import dataclass

from streaming.emitter import StreamEmitter

ENABLE = os.environ.get("ENABLE_MOCK_FALLBACK", "0") == "1"

_MESSAGES = [
    "正在分析需求...",
    "根据分析，这是一个标准的软件开发需求。",
    "建议采用模块化设计，优先实现核心功能。",
    "需求分析完成。",
]


@dataclass
class MockOutput:
    """Canned pipeline output — mirrors the shape of a real graph result."""

    response: str = ""
    status: str = "converged"
    approved: bool = False


async def run_mock(requirement: str, run_id: str, session_id: str | None) -> MockOutput:
    """Run a mock agent pipeline with canned response messages.

    ``session_id`` is part of the shared runner contract (kept for drop-in
    compatibility with tasks/pipeline_utils.py) but not needed by the mock.
    """
    emitter = StreamEmitter(run_id)
    messages = [f"收到需求：{requirement[:100]}", *_MESSAGES]
    for msg in messages:
        await emitter.emit_message("Agent", msg)
        await asyncio.sleep(0.5)

    return MockOutput(response="\n".join(messages), approved=True)