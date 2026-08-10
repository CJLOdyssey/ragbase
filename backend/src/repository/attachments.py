"""Attachment repository — CRUD for AttachmentDB."""

from core.infra.database import AttachmentDB, get_session_factory
from sqlalchemy import and_, or_, select, update


async def create_attachment(
    attachment_id: str,
    session_id: str | None,
    filename: str,
    content_type: str,
    size_bytes: int,
    storage_path: str,
    user_id: str | None = None,
    run_id: str | None = None,
    extracted_text: str | None = None,
) -> AttachmentDB:
    """Create a new attachment record and return it."""
    attachment = AttachmentDB(
        id=attachment_id,
        session_id=session_id,
        user_id=user_id,
        run_id=run_id,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        storage_path=storage_path,
        extracted_text=extracted_text,
    )
    factory = get_session_factory()
    async with factory() as session:
        session.add(attachment)
        await session.commit()
    return attachment


async def get_attachment_by_id(attachment_id: str) -> AttachmentDB | None:
    """Get an attachment by its ID."""
    factory = get_session_factory()
    async with factory() as session:
        return await session.get(AttachmentDB, attachment_id)


async def list_attachments_by_session(session_id: str) -> list[AttachmentDB]:
    """List all attachments for a session, ordered by creation time descending."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(AttachmentDB)
            .where(AttachmentDB.session_id == session_id)
            .order_by(AttachmentDB.created_at.desc())
        )
        return list(result.scalars().all())


async def list_attachments_by_run(run_id: str) -> list[AttachmentDB]:
    """List all attachments for a run, ordered by creation time ascending."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(AttachmentDB)
            .where(AttachmentDB.run_id == run_id)
            .order_by(AttachmentDB.created_at.asc())
        )
        return list(result.scalars().all())


async def delete_attachment(attachment_id: str) -> str | None:
    """Delete an attachment by ID. Returns the storage_path if found, None otherwise."""
    factory = get_session_factory()
    async with factory() as session:
        attachment = await session.get(AttachmentDB, attachment_id)
        if attachment is None:
            return None
        storage_path = attachment.storage_path
        await session.delete(attachment)
        await session.commit()
        return storage_path


async def bind_attachments_to_run(
    attachment_ids: list[str], run_id: str, session_id: str, user_id: str
) -> None:
    """Bind pre-uploaded attachments to a run.

    Qualified: attachment already belongs to the run's session, OR is still
    unbound (pre-session upload) AND owned by the same user. Silently skips
    ids that don't qualify — a stranger's pending file can never be attached.
    """
    if not attachment_ids:
        return
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(
            update(AttachmentDB)
            .where(
                AttachmentDB.id.in_(attachment_ids),
                or_(
                    AttachmentDB.session_id == session_id,
                    and_(AttachmentDB.session_id.is_(None), AttachmentDB.user_id == user_id),
                ),
            )
            .values(run_id=run_id, session_id=session_id)
        )
        await session.commit()
