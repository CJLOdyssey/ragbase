"""SQLAlchemy declarative base for all ORM models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared base for ORM models — all models register on one metadata registry.

    Required so ``create_all``/Alembic see the full schema through a single ``Base.metadata``.
    """
