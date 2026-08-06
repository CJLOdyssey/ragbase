"""GenerationService — typed content generation orchestration.

SPEC §3.2 管线: 校验 → key 解析(vault) → 提示词组装(模板+素材+RAG) →
create_run → LLM 流式(SSE) → 结构化解析 → 存版本+草稿。
"""

from __future__ import annotations

import asyncio
from typing import Any

from broker import buffer_run_messages
from core.infra.logging_config import get_logger
from repository import (
    create_session,
    get_api_key_for_model,
    get_default_api_key,
    get_run,
    update_run_result,
    update_run_status,
)
from repository.assets import get_asset, increment_asset_usage, list_assets_by_user
from repository.compose_templates import get_template
from repository.run_repo import count_runs_by_parent, create_run

from services.structured import (
    CONTENT_TYPES,
    GENERATION_MODES,
    parse_generation_result,
)

logger = get_logger(__name__)

MAX_TOPIC_LENGTH = 500
MAX_EXTRA_LENGTH = 2000
MAX_VARIATIONS = 3

_PROMPT_TEMPLATE = """你是资深内容创作者。请基于以下要求创作{content_type_label}内容。

主题：{topic}
{extra_section}{asset_section}
输出要求（严格 JSON，不要输出其他内容）：
{{"title": "标题", "summary": "≤200字摘要", "body_markdown": "正文 Markdown", "keywords": ["关键词"]}}
"""

_CONTENT_TYPE_LABELS: dict[str, str] = {
    "xiaohongshu": "小红书笔记",
    "wechat_article": "公众号文章",
    "short_video_script": "短视频脚本",
    "marketing_copy": "营销文案",
    "generic": "通用内容",
}


async def _stream_llm(
    url: str, headers: dict[str, Any], body: dict[str, Any], run_id: str
) -> tuple[str, list[str]]:
    """Default LLM streaming — raw OpenAI-compatible SSE (mirrors tasks/prefix_completion)."""
    from tasks.prefix_completion import stream_prefix_completion

    return await stream_prefix_completion(url, headers, body, run_id)


class GenerationService:
    """Business-logic facade for typed content generation."""

    async def create_generation(
        self,
        user_id: str,
        content_type: str,
        topic: str,
        additional_requirements: str = "",
        asset_ids: list[str] | None = None,
        key_id: str | None = None,
        model: str | None = None,
        generation_mode: str = "generate",
        template_id: str | None = None,
        parent_run_id: str | None = None,
    ) -> dict[str, Any]:
        topic = topic.strip()
        if content_type not in CONTENT_TYPES:
            raise ValueError(f"不支持的 content_type: {content_type}")
        if generation_mode not in GENERATION_MODES:
            raise ValueError(f"不支持的 generation_mode: {generation_mode}")
        if not topic or len(topic) > MAX_TOPIC_LENGTH:
            raise ValueError(f"主题必填且不超过 {MAX_TOPIC_LENGTH} 字")
        if len(additional_requirements) > MAX_EXTRA_LENGTH:
            raise ValueError(f"附加要求不超过 {MAX_EXTRA_LENGTH} 字")

        api_key, api_base, effective_model = await self._resolve_key(key_id, model, user_id)
        sess = await create_session(title=topic[:64], user_id=user_id, kind="normal")
        session_id = sess.id

        run_id = await create_run(
            topic,
            session_id=session_id,
            content_type=content_type,
            generation_mode=generation_mode,
            topic=topic,
            template_id=template_id,
            parent_run_id=parent_run_id,
        )

        await buffer_run_messages(run_id)

        asyncio.create_task(
            self._generate_pipeline(
                run_id=run_id,
                session_id=session_id,
                user_id=user_id,
                content_type=content_type,
                topic=topic,
                additional_requirements=additional_requirements,
                asset_ids=asset_ids or [],
                api_key=api_key,
                api_base=api_base,
                model=effective_model,
            )
        )
        logger.info(
            "Generation started | run=%s | type=%s | mode=%s",
            run_id, content_type, generation_mode,
        )
        return {"run_id": run_id, "session_id": session_id, "status": "pending"}

    async def get_generation(self, run_id: str) -> dict[str, Any] | None:
        run = await get_run(run_id)
        if run is None:
            return None
        return {
            "id": run.id,
            "session_id": run.session_id,
            "topic": run.topic or run.requirement,
            "content_type": run.content_type,
            "generation_mode": run.generation_mode,
            "status": run.status,
            "result": run.result_json or {},
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }

    async def continue_generation(
        self, run_id: str, content: str, user_id: str
    ) -> dict[str, Any]:
        run = await get_run(run_id)
        if run is None:
            raise ValueError("run 不存在")
        return await self.create_generation(
            user_id=user_id,
            content_type=run.content_type,
            topic=run.topic or run.requirement,
            additional_requirements=content,
            generation_mode="rewrite",
            template_id=run.template_id,
        )

    async def create_variations(self, run_id: str, user_id: str) -> dict[str, Any]:
        run = await get_run(run_id)
        if run is None:
            raise ValueError("run 不存在")
        count = await count_runs_by_parent(run_id)
        if count >= MAX_VARIATIONS:
            raise ValueError(f"同一输入最多生成 {MAX_VARIATIONS} 版")
        return await self.create_generation(
            user_id=user_id,
            content_type=run.content_type,
            topic=run.topic or run.requirement,
            generation_mode="variations",
            parent_run_id=run_id,
        )

    async def compose_card(
        self,
        run_id: str,
        template_id: str,
        title: str,
        summary: str,
    ) -> dict[str, Any]:
        run = await get_run(run_id)
        if run is None:
            raise ValueError("run 不存在")
        template = await get_template(template_id)
        if template is None:
            raise ValueError("模板不存在")
        from repository.attachments import list_attachments_by_run

        images = [a.id for a in await list_attachments_by_run(run_id) if a.content_type.startswith("image/")]
        return {
            "template": {
                "id": template.id,
                "name": template.name,
                "layout": template.layout_json,
            },
            "fields": {"title": title, "summary": summary, "image_attachment_ids": images},
        }

    async def _generate_pipeline(
        self,
        run_id: str,
        session_id: str,
        user_id: str,
        content_type: str,
        topic: str,
        additional_requirements: str,
        asset_ids: list[str],
        api_key: str,
        api_base: str | None,
        model: str | None,
    ) -> None:
        try:
            await update_run_status(run_id, "running")
            asset_context = await self._build_asset_context(user_id, asset_ids, topic)
            prompt = _PROMPT_TEMPLATE.format(
                content_type_label=_CONTENT_TYPE_LABELS.get(content_type, content_type),
                topic=topic,
                extra_section=f"附加要求：{additional_requirements}\n" if additional_requirements else "",
                asset_section=asset_context,
            )
            base_url = (api_base or "https://api.deepseek.com").rstrip("/")
            url = f"{base_url}/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            body = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
                "max_tokens": 16384,
            }
            full_content, _thinking = await _stream_llm(url, headers, body, run_id)

            result = parse_generation_result(full_content)
            snapshot = result.model_dump()
            await update_run_result(
                run_id,
                pm_document="",
                code=result.body_markdown,
                review="",
                approved=False,
                status="completed",
                result_json=snapshot,
            )
            await self._save_version(session_id, run_id, snapshot)
            from broker import publish_run_message

            await publish_run_message(run_id, {"type": "result", "status": "completed", **snapshot})
        except Exception as e:  # noqa: BLE001
            logger.exception("Generation pipeline failed for run=%s", run_id)
            await update_run_status(run_id, "error")
            from broker import publish_run_message

            await publish_run_message(run_id, {"type": "error", "detail": str(e)})

    async def _build_asset_context(self, user_id: str, asset_ids: list[str], query: str) -> str:
        parts: list[str] = []
        for asset_id in asset_ids:
            asset = await get_asset(asset_id)
            if asset is None:
                continue
            await increment_asset_usage(asset_id)
            parts.append(f"[素材 {asset.name}]: {asset.storage_path}")
        rag_context = await self._retrieve_rag_context(user_id, query)
        if rag_context:
            parts.append(f"[品牌风格参考]:\n{rag_context}")
        return ("\n".join(parts) and "素材参考：\n" + "\n".join(parts)) or ""

    async def _retrieve_rag_context(self, user_id: str, query: str) -> str:
        try:
            from rag.rag_pipeline import ensure_embedding_provider, retrieve_context
            from repository.keys import get_embedding_api_key

            api_key = await get_embedding_api_key()
            ensure_embedding_provider(api_key)
            assets = await list_assets_by_user(user_id)
            chunks: list[str] = []
            for asset in assets:
                if not asset.indexed:
                    continue
                context = await retrieve_context(
                    query=query, session_id=f"asset:{asset.id}", top_k=3
                )
                if context:
                    chunks.append(context)
            return "\n\n".join(chunks[:3])
        except Exception:  # noqa: BLE001
            logger.warning("RAG retrieval failed for user=%s", user_id, exc_info=True)
            return ""

    async def _save_version(self, session_id: str, run_id: str, snapshot: dict[str, Any]) -> None:
        try:
            from core.infra.database import get_session_factory
            from repository.versions import create_version

            factory = get_session_factory()
            async with factory() as session:
                await create_version(
                    session,
                    resource_type="generation",
                    resource_id=run_id,
                    snapshot={"session_id": session_id, **snapshot},
                )
                await session.commit()
        except Exception:  # noqa: BLE001
            logger.exception("Failed to save version for run=%s", run_id)

    async def _resolve_key(
        self, key_id: str | None, model: str | None, user_id: str
    ) -> tuple[str, str | None, str | None]:
        config = await self._load_config()
        api_key: str | None = None
        api_base: str | None = None
        effective_model = model or config.model
        if key_id:
            from repository import get_api_key_for_use

            entry = await get_api_key_for_use(key_id, user_id)
            if entry:
                api_key = entry.get("api_key")
                api_base = entry.get("base_url") or api_base
        if not api_key and effective_model:
            entry = await get_api_key_for_model(effective_model, user_id)
            if entry:
                api_key = entry.get("api_key")
                api_base = entry.get("base_url") or api_base
        if not api_key:
            entry = await get_default_api_key(user_id)
            if entry:
                api_key = entry["api_key"]
                api_base = entry.get("base_url") or api_base
        if not api_key:
            raise ValueError("请先在设置中配置 API Key")
        return api_key, api_base, effective_model

    async def _load_config(self) -> Any:
        from core.config import load_config

        return load_config()


generation_service = GenerationService()

__all__ = ["GenerationService", "generation_service"]
