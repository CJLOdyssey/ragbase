"""Minimal type stubs for celery — covers only APIs used by AgentStudio."""

from __future__ import annotations

from typing import Any


class Celery:
    def __init__(
        self,
        main: str = "",
        broker: str | None = None,
        backend: str | None = None,
        **kwargs: Any,
    ) -> None: ...

    @property
    def conf(self) -> Any: ...
    def conf_update(self, **kwargs: Any) -> None: ...
    def autodiscover_tasks(self, packages: list[str] | None = None) -> None: ...
    def task(self, *args: Any, **kwargs: Any) -> Any: ...
