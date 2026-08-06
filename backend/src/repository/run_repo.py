"""Project run repository — CRUD for run lifecycle management."""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.infra.database import ProjectRun, SessionDB, get_session_factory
from sqlalchemy import desc, select


async def get_session_runs(session_id: str) -> list[ProjectRun]:
    """Return all project runs belonging to a session, ordered by creation time."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(ProjectRun)
            .where(ProjectRun.session_id == session_id)
            .order_by(ProjectRun.created_at)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_runs_by_session_ids(session_ids: list[str]) -> dict[str, list[ProjectRun]]:
    """Batch-load runs for multiple session IDs, keyed by session_id."""
    if not session_ids:
        return {}
    factory = get_session_factory()
    async with factory() as session:
        stmt = (
            select(ProjectRun)
            .where(ProjectRun.session_id.in_(session_ids))
            .order_by(ProjectRun.created_at)
        )
        result = await session.execute(stmt)
        runs = list(result.scalars().all())
        grouped: dict[str, list[ProjectRun]] = {}
        for run in runs:
            grouped.setdefault(run.session_id or "", []).append(run)
        return grouped


async def create_run(
    requirement: str,
    session_id: str | None = None,
    parent_run_id: str | None = None,
    requirement_versions: list[str] | None = None,
    content_type: str = "generic",
    generation_mode: str = "generate",
    topic: str | None = None,
    template_id: str | None = None,
) -> str:
    """Create a new project run and return its ID.

    Also touches the parent session's updated_at timestamp.
    ``parent_run_id`` links an edit-regenerate to the run it replaces;
    ``requirement_versions`` carries the user-message edit history chain.
    """
    run_id = str(uuid4())
    run = ProjectRun(
        id=run_id,
        session_id=session_id,
        requirement=requirement,
        status="pending",
        parent_run_id=parent_run_id,
        requirement_versions=json.dumps(requirement_versions) if requirement_versions else None,
        content_type=content_type,
        generation_mode=generation_mode,
        topic=topic,
        template_id=template_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    factory = get_session_factory()
    async with factory() as session:
        session.add(run)
        await session.commit()
        if session_id:
            sess = await session.get(SessionDB, session_id)
            if sess:
                sess.updated_at = datetime.now(UTC)
                await session.commit()
    return run_id


async def update_run_status(run_id: str, status: str) -> Any:
    """Update the status field of a project run."""
    factory = get_session_factory()
    async with factory() as session:
        run = await session.get(ProjectRun, run_id)
        if run:
            run.status = status
            run.updated_at = datetime.now(UTC)
            await session.commit()


async def update_run_result(
    run_id: str,
    pm_document: str,
    code: str,
    review: str,
    approved: bool,
    status: str,
    result_json: dict[str, Any] | None = None,
) -> Any:
    """Persist the full result payload of a completed run."""
    factory = get_session_factory()
    async with factory() as session:
        run = await session.get(ProjectRun, run_id)
        if run:
            run.pm_document = pm_document
            run.code = code
            run.review = review
            run.approved = approved
            run.status = status
            run.result_json = result_json
            run.updated_at = datetime.now(UTC)
            await session.commit()


async def get_run(run_id: str) -> ProjectRun | None:
    """Fetch a single project run by its primary key ID."""
    factory = get_session_factory()
    async with factory() as session:
        run = await session.get(ProjectRun, run_id)
        return run


async def get_runs(limit: int = 20) -> list[ProjectRun]:
    """Return the most recent project runs, up to the given limit."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(ProjectRun).order_by(desc(ProjectRun.created_at)).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())
