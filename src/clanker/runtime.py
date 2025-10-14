"""Runtime context management for Clanker.

Provides a lightweight dependency injection container so modules can share
profile, registry, and schema configuration without relying on module-level
singletons. When running under the CLI we build a default context, but tests or
embedding environments can construct their own and inject it explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import RLock
from typing import Optional

from .profile import Profile
from .storage.schema import DatabaseSchema, ensure_database_initialized
from .tool_registry import ToolRegistry, get_registry


@dataclass
class RuntimeContext:
    """Aggregates shared runtime services for Clanker components."""

    profile: Profile = field(default_factory=Profile.current)
    registry: ToolRegistry = field(default_factory=get_registry)
    _schema: DatabaseSchema | None = field(default=None, init=False, repr=False)
    _registry_discovered: bool = field(default=False, init=False, repr=False)
    _core_tools_registered: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        # Lazily construct schema helper so we respect custom profiles.
        if self._schema is None:
            self._schema = DatabaseSchema(self.profile)

    @property
    def schema(self) -> DatabaseSchema:
        if self._schema is None:
            self._schema = DatabaseSchema(self.profile)
        return self._schema

    def ensure_database_initialized(self, *, force: bool = False) -> None:
        """Ensure the core schema exists for this context's profile."""

        ensure_database_initialized(self.profile, force=force)

    def ensure_registry_discovered(self) -> None:
        """Populate registry with app exports exactly once per context."""

        if not self._registry_discovered:
            self.registry.discover_apps()
            self._registry_discovered = True

    def mark_core_tools_registered(self) -> None:
        self._core_tools_registered = True

    def core_tools_already_registered(self) -> bool:
        return self._core_tools_registered


_runtime_lock = RLock()
_runtime_context: Optional[RuntimeContext] = None


def set_runtime_context(context: RuntimeContext) -> None:
    """Replace the process-wide runtime context."""

    global _runtime_context
    with _runtime_lock:
        _runtime_context = context


def get_runtime_context() -> RuntimeContext:
    """Return the active runtime context, creating a default if missing."""

    global _runtime_context
    with _runtime_lock:
        if _runtime_context is None:
            _runtime_context = RuntimeContext()
        return _runtime_context


def bootstrap_runtime_context(force: bool = False) -> RuntimeContext:
    """Ensure a runtime context exists and is fully initialized."""

    ctx = get_runtime_context()
    ctx.ensure_database_initialized(force=force)
    ctx.ensure_registry_discovered()
    return ctx


__all__ = [
    "RuntimeContext",
    "bootstrap_runtime_context",
    "get_runtime_context",
    "set_runtime_context",
]

