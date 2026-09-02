"""Tests for SingleAgentGraph image node path in backend/graph/graph.py.

Mocks the LLM and streaming layer to exercise _image_node dispatch without
real HTTP calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from graph.graph import SingleAgentGraph
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver


@pytest.fixture
def graph() -> SingleAgentGraph:
    """Create a SingleAgentGraph with MemorySaver and mocked ChatOpenAI."""
    with patch("graph.graph.ChatOpenAI") as MockLLM:
        MockLLM.return_value = MagicMock()
        g = SingleAgentGraph(
            model="test-model",
            api_key="test-key",
            base_url="http://localhost:9999",
            checkpointer=MemorySaver(),
        )
    return g


class TestImageNode:
    @pytest.mark.asyncio
    async def test_image_model_uses_image_node(self, graph: SingleAgentGraph):
        graph.image_model = True
        with patch("streaming.image_generation.generate_image", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "https://img.example/cat.png"
            state = {"messages": [HumanMessage(content="一只橘猫")], "system_prompt": "", "session_context": ""}
            result = await graph._agent_node(state)

        mock_gen.assert_awaited_once()
        _, kwargs = mock_gen.call_args
        assert kwargs["model"] == "test-model"
        ai_msg = result["messages"][0]
        assert isinstance(ai_msg, AIMessage)
        assert ai_msg.content == "![生成的图片](https://img.example/cat.png)"

    @pytest.mark.asyncio
    async def test_image_node_emits_token_and_node_end(self, graph: SingleAgentGraph):
        graph.image_model = True
        events: list[dict] = []

        async def fake_cb(event: dict) -> None:
            events.append(event)

        graph.set_stream_callback(fake_cb)
        with patch("streaming.image_generation.generate_image", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "https://img.example/cat.png"
            await graph._agent_node({"messages": [HumanMessage(content="一只橘猫")], "system_prompt": "", "session_context": ""})

        token_events = [e for e in events if e.get("event") == "on_custom_token"]
        assert token_events
        assert "https://img.example/cat.png" in token_events[0]["data"]["content"]
        assert any(e.get("event") == "on_node_end" for e in events)

    @pytest.mark.asyncio
    async def test_image_node_uses_last_human_message(self, graph: SingleAgentGraph):
        graph.image_model = True
        with patch("streaming.image_generation.generate_image", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "https://img.example/x.png"
            await graph._agent_node(
                {"messages": [HumanMessage(content="先聊两句"), HumanMessage(content="画一朵云")], "system_prompt": "", "session_context": ""}
            )

        args, _ = mock_gen.call_args
        assert args[1] == "画一朵云"


class TestNoRagHitsRefusal:
    """R1: zero retrieval hits injects deterministic refusal guidance."""

    @pytest.mark.asyncio
    async def test_injects_refusal_guidance_when_no_rag_hits(self, graph: SingleAgentGraph):
        from graph.helpers import NO_RAG_HITS_PROMPT

        with patch.object(graph, "_raw_llm_stream", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("回答", "", [])
            await graph._agent_node(
                {
                    "messages": [HumanMessage(content="知识库问题")],
                    "system_prompt": "",
                    "session_context": "",
                    "no_rag_hits": True,
                }
            )

        sent = mock_llm.call_args[0][0]
        assert any(isinstance(m, SystemMessage) and m.content == NO_RAG_HITS_PROMPT for m in sent)

    @pytest.mark.asyncio
    async def test_no_refusal_guidance_when_hits_exist(self, graph: SingleAgentGraph):
        """反例：有检索结果绝不注入拒答指引（防 answer_relevancy 0.253 回归）。"""
        from graph.helpers import NO_RAG_HITS_PROMPT

        with patch.object(graph, "_raw_llm_stream", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = ("回答", "", [])
            await graph._agent_node(
                {
                    "messages": [HumanMessage(content="知识库问题")],
                    "system_prompt": "",
                    "session_context": "",
                    "no_rag_hits": False,
                }
            )

        sent = mock_llm.call_args[0][0]
        assert not any(isinstance(m, SystemMessage) and m.content == NO_RAG_HITS_PROMPT for m in sent)
