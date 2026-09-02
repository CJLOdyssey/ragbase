"""Tests for completion_request — provider-routed continuation builder."""

import pytest
from tasks.completion_request import (
    ContinuationContext,
    build_completion_request,
)

API_KEY = "sk-test"


def ctx(**kw):
    return ContinuationContext(**kw)


class TestDeepseekOfficial:
    """DeepSeek official API → /beta Chat Prefix Completion."""

    def test_thinking_routes_to_beta_prefix(self):
        req = build_completion_request(
            ctx=ctx(question="原问题", draft="半截文本", thinking="原思考链"),
            model="deepseek-chat",
            api_base="https://api.deepseek.com",
            api_key=API_KEY,
        )
        assert req.url == "https://api.deepseek.com/beta/chat/completions"
        assert req.body["messages"][0] == {"role": "user", "content": "原问题"}
        assistant = req.body["messages"][1]
        assert assistant["prefix"] is True
        assert assistant["content"] == "半截文本"
        assert assistant["reasoning_content"] == "原思考链"
        assert req.body["thinking"] == {"type": "enabled"}

    def test_beta_suffix_is_not_duplicated(self):
        req = build_completion_request(
            ctx=ctx(draft="x", thinking="t"),
            model="deepseek-chat",
            api_base="https://api.deepseek.com/beta",
            api_key=API_KEY,
        )
        assert req.url == "https://api.deepseek.com/beta/chat/completions"

    def test_without_thinking_falls_back_to_plain(self):
        req = build_completion_request(
            ctx=ctx(question="q", draft="半截文本"),
            model="deepseek-chat",
            api_base="https://api.deepseek.com",
            api_key=API_KEY,
        )
        assert req.url == "https://api.deepseek.com/chat/completions"
        assert "半截文本" in req.body["messages"][0]["content"]


class TestKimi:
    """Kimi (Moonshot) kimi-k2 → Partial Mode with preserved thinking."""

    def test_thinking_uses_partial_mode(self):
        req = build_completion_request(
            ctx=ctx(question="q", draft="半截文本", thinking="原思考链"),
            model="kimi-k2.6",
            api_base="https://api.moonshot.cn/v1",
            api_key=API_KEY,
        )
        assert req.url == "https://api.moonshot.cn/v1/chat/completions"
        assert "/beta/" not in req.url
        assistant = req.body["messages"][-1]
        assert assistant["role"] == "assistant"
        assert assistant["partial"] is True
        assert assistant["reasoning_content"] == "原思考链"
        assert req.body["thinking"] == {"type": "enabled", "keep": "all"}

    def test_non_k2_model_falls_back_to_plain(self):
        req = build_completion_request(
            ctx=ctx(draft="半截文本", thinking="t"),
            model="moonshot-v1-32k",
            api_base="https://api.moonshot.cn/v1",
            api_key=API_KEY,
        )
        assert "partial" not in str(req.body)
        assert "半截文本" in req.body["messages"][0]["content"]


class TestFallback:
    """SiliconFlow & other OpenAI-compatible providers → standardized prompt."""

    @pytest.mark.parametrize(
        "base",
        [
            "https://api.siliconflow.cn/v1",
            "https://api.openai.com/v1",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ],
    )
    def test_thinking_never_reaches_beta_or_partial(self, base):
        req = build_completion_request(
            ctx=ctx(question="q", draft="半截文本", thinking="原思考链"),
            model="deepseek-ai/DeepSeek-V4-Flash",
            api_base=base,
            api_key=API_KEY,
        )
        assert req.url == f"{base.rstrip('/')}/chat/completions"
        assert "/beta/" not in req.url
        assert "partial" not in str(req.body)
        assert "reasoning_content" not in str(req.body)

    def test_prompt_contains_all_three_sections(self):
        """标准化：fallback 模型看到 原问题 + 草稿 + 思考 三段。"""
        req = build_completion_request(
            ctx=ctx(question="什么是相对论？", draft="半截回答", thinking="半截思考"),
            model="deepseek-ai/DeepSeek-V4-Flash",
            api_base="https://api.siliconflow.cn/v1",
            api_key=API_KEY,
        )
        prompt = req.body["messages"][0]["content"]
        assert "什么是相对论？" in prompt
        assert "半截回答" in prompt
        assert "半截思考" in prompt
        assert "<已生成的回答草稿>" in prompt
        assert "<已生成的思考草稿>" in prompt
        assert "<任务>" in prompt
        # draft 有 → 关思考（避免续写 run 的新思考覆盖消息 thinking）
        assert req.body["enable_thinking"] is False

    def test_thinking_only_interruption_enables_thinking_and_omits_draft_section(self):
        req = build_completion_request(
            ctx=ctx(question="什么是相对论？", draft="", thinking="半截思考"),
            model="deepseek-ai/DeepSeek-V4-Flash",
            api_base="https://api.siliconflow.cn/v1",
            api_key=API_KEY,
        )
        prompt = req.body["messages"][0]["content"]
        assert "半截思考" in prompt
        assert "什么是相对论？" in prompt
        assert "<已生成的回答草稿>" not in prompt
        assert "<已生成的思考草稿>" in prompt
        # draft 空 → 开思考：思考链从断点继续滚动（丝滑）
        assert req.body["enable_thinking"] is True

    def test_other_fallback_uses_thinking_param(self):
        req = build_completion_request(
            ctx=ctx(draft="半截文本"),
            model="some-model",
            api_base="https://api.openai.com/v1",
            api_key=API_KEY,
        )
        assert req.body["thinking"] == {"type": "disabled"}

    def test_default_base_is_deepseek_official(self):
        req = build_completion_request(
            ctx=ctx(draft="x", thinking="t"),
            model="m",
            api_base=None,
            api_key=API_KEY,
        )
        assert "api.deepseek.com" in req.url

    def test_trailing_slash_base_stripped(self):
        """base_url 尾斜杠 rstrip——不应影响路由判定与 URL 拼接。"""
        req = build_completion_request(
            ctx=ctx(draft="x", thinking="t"),
            model="deepseek-chat",
            api_base="https://api.deepseek.com/",
            api_key=API_KEY,
        )
        assert req.url == "https://api.deepseek.com/beta/chat/completions"

    def test_question_none_uses_deepseek_default_prompt(self):
        """question 缺失 → DeepSeek 官方前缀接口使用默认续写指令。"""
        req = build_completion_request(
            ctx=ctx(draft="半截文本", thinking="t"),
            model="deepseek-chat",
            api_base="https://api.deepseek.com",
            api_key=API_KEY,
        )
        assert req.body["messages"][0] == {"role": "user", "content": "请继续完成下面的回答"}

    def test_max_tokens_cap_applied(self):
        """超长草稿/思考：请求体仍受 _MAX_TOKENS 上限约束（防无限生成）。"""
        req = build_completion_request(
            ctx=ctx(question="q", draft="x" * 20000, thinking="t" * 20000),
            model="deepseek-chat",
            api_base="https://api.deepseek.com",
            api_key=API_KEY,
        )
        assert req.body["max_tokens"] == 16384


class TestThinkingOnlyInterruption:
    """正文未生成（仅思考被中断）时，续写原料 = 半截思考链。"""

    def test_fallback_uses_thinking_as_material_when_content_empty(self):
        req = build_completion_request(
            ctx=ctx(draft="", thinking="半截思考链"),
            model="deepseek-ai/DeepSeek-V4-Flash",
            api_base="https://api.siliconflow.cn/v1",
            api_key=API_KEY,
        )
        prompt = req.body["messages"][0]["content"]
        assert "半截思考链" in prompt
        assert "<已生成的思考草稿>" in prompt
        # 思考中断续写：开启思考让思考链从断点继续滚动（丝滑）
        assert req.body["enable_thinking"] is True

    def test_siliconflow_continuation_disables_thinking_for_text_draft(self):
        """正文中断续写：关思考，避免新 reasoning 覆盖消息 thinking。"""
        req = build_completion_request(
            ctx=ctx(draft="半截文本", thinking="原思考链"),
            model="deepseek-ai/DeepSeek-V4-Flash",
            api_base="https://api.siliconflow.cn/v1",
            api_key=API_KEY,
        )
        assert req.body["enable_thinking"] is False

    def test_kimi_skips_partial_when_content_empty(self):
        req = build_completion_request(
            ctx=ctx(draft="", thinking="半截思考链"),
            model="kimi-k2.6",
            api_base="https://api.moonshot.cn/v1",
            api_key=API_KEY,
        )
        assistant = req.body["messages"][-1]
        assert assistant["partial"] is False
        assert assistant["reasoning_content"] == "半截思考链"
        assert "基于以下思考过程" in req.body["messages"][0]["content"]

    def test_deepseek_official_keeps_prefix_with_empty_content(self):
        req = build_completion_request(
            ctx=ctx(draft="", thinking="半截思考链"),
            model="deepseek-chat",
            api_base="https://api.deepseek.com",
            api_key=API_KEY,
        )
        assert req.body["messages"][1]["prefix"] is True
        assert req.body["messages"][1]["reasoning_content"] == "半截思考链"
        assert req.body["messages"][1]["content"] == ""
