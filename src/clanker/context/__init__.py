"""Context management for core Clanker functionality."""

from .builder import ContextBuilder
from .store import ContextStore
from .templates import cli_session_context, app_scaffold_context, get_available_apps_context, coding_session_context

__all__ = [
    "ContextBuilder",
    "ContextStore", 
    "cli_session_context",
    "app_scaffold_context",
    "get_available_apps_context",
    "coding_session_context",
]

