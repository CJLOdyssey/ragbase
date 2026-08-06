"""Generic CRUD base for simple entity repositories."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar, Generic, TypeVar, cast

from core.infra.database import get_session_factory
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase

ModelT = TypeVar("ModelT", bound=DeclarativeBase)


class BaseRepository(Generic[ModelT]):

    model: ClassVar[type[DeclarativeBase]]
    default_order: ClassVar[Any] = None
    session_factory = staticmethod(get_session_factory)

    @classmethod
    def _session_cm(cls) -> Any:
        return cls.session_factory()()

    @classmethod
    async def get_one(cls, entity_id: str) -> ModelT | None:
        """Fetch a single entity by its primary key."""
        async with cls._session_cm() as session:
            return cast(ModelT | None, await session.get(cls.model, entity_id))

    @classmethod
    async def get_all(cls) -> list[ModelT]:
        """Fetch all entities, ordered by ``default_order`` if set."""
        async with cls._session_cm() as session:
            stmt = select(cls.model)
            if cls.default_order is not None:
                stmt = stmt.order_by(cls.default_order)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    @classmethod
    async def get_all_as_dicts(cls) -> list[dict[str, Any]]:
        """Fetch all entities and return them as dictionaries."""
        async with cls._session_cm() as session:
            stmt = select(cls.model)
            if cls.default_order is not None:
                stmt = stmt.order_by(cls.default_order)
            result = await session.execute(stmt)
            return [cls.to_dict(obj) for obj in result.scalars().all()]

    @classmethod
    async def create_one(cls, data: dict[str, Any]) -> ModelT:
        """Insert a new entity from the given data dictionary."""
        async with cls._session_cm() as session:
            obj = cast(ModelT, cls.model(**data))
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return obj

    @classmethod
    async def update_one(cls, entity_id: str, data: dict[str, Any]) -> ModelT | None:
        """Update an existing entity's fields from *data* (None values skipped)."""
        async with cls._session_cm() as session:
            obj = await session.get(cls.model, entity_id)
            if not obj:
                return None
            for k, v in data.items():
                if v is not None and hasattr(obj, k):
                    setattr(obj, k, v)
            obj.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(obj)
            return cast(ModelT | None, obj)

    @classmethod
    async def delete_one(cls, entity_id: str) -> bool:
        """Delete an entity by ID. Returns True if deleted, False if not found."""
        async with cls._session_cm() as session:
            obj = await session.get(cls.model, entity_id)
            if not obj:
                return False
            await session.delete(obj)
            await session.commit()
            return True

    @staticmethod
    def to_dict(obj: ModelT) -> dict[str, Any]:
        """Serialize a model instance to a dictionary. Must be overridden."""
        raise NotImplementedError
