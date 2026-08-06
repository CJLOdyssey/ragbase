"""Compose template repository — card layout templates."""

from core.infra.database import ComposeTemplateDB, get_session_factory
from sqlalchemy import select


async def get_template(template_id: str) -> ComposeTemplateDB | None:
    factory = get_session_factory()
    async with factory() as session:
        return await session.get(ComposeTemplateDB, template_id)


async def list_templates() -> list[ComposeTemplateDB]:
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(ComposeTemplateDB).order_by(ComposeTemplateDB.created_at.asc())
        )
        return list(result.scalars().all())
