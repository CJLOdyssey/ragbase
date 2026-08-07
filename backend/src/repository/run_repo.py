"""Project run repository — CRUD for run lifecycle management."""

import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from core.infra.database import ProjectRun, SessionDB, get_session_factory
from sqlalchemy import desc, func, select

from repository.session_repo import get_sessions


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
            run.updated_at = datetime.now(UTC)
            await session.commit()


async def get_run(run_id: str) -> ProjectRun | None:
    """Fetch a single project run by its primary key ID."""
    factory = get_session_factory()
    async with factory() as session:
        run = await session.get(ProjectRun, run_id)
        return run


async def get_run_for_user(run_id: str, user_id: str) -> ProjectRun | None:
    """Fetch a run only if its session belongs to user_id. None otherwise."""
    factory = get_session_factory()
    async with factory() as session:
        run = await session.get(ProjectRun, run_id)
        if run is None or run.session_id is None:
            return None
        sess = await session.get(SessionDB, run.session_id)
        if sess is None or sess.user_id != user_id:
            return None
        return run


async def get_runs(limit: int = 20) -> list[ProjectRun]:
    """Return the most recent project runs, up to the given limit."""
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(ProjectRun).order_by(desc(ProjectRun.created_at)).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_runs_for_user(user_id: str, limit: int = 20) -> list[ProjectRun]:
    """List a user's runs via session ownership (project_runs has no user_id column)."""
    sessions = await get_sessions(user_id=user_id, limit=limit * 2)
    if not sessions:
        return []
    run_map = await get_runs_by_session_ids([s.id for s in sessions])
    runs = [run for rs in run_map.values() for run in rs]
    runs.sort(key=lambda r: r.created_at or datetime.min, reverse=True)
    return runs[:limit]


async def count_runs_by_parent(parent_run_id: str) -> int:
    """Count child runs linked to the given parent run."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(func.count(ProjectRun.id)).where(ProjectRun.parent_run_id == parent_run_id)
        )
        return int(result.scalar_one() or 0)


async def get_run_ancestors(run_id: str) -> list[ProjectRun]:
    """Return the run and all its ancestors via parent_run_id, root-first.

    Guards against cycles (corrupt data) by capping the walk at the run count.
    """
    factory = get_session_factory()
    async with factory() as session:
        rows: list[ProjectRun] = []
        seen: set[str] = set()
        current_id: str | None = run_id
        while current_id and current_id not in seen:
            seen.add(current_id)
            run = await session.get(ProjectRun, current_id)
            if run is None:
                break
            rows.append(run)
            current_id = run.parent_run_id or None
        rows.reverse()
        return rows
