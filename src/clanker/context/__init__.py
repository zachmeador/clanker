"""Context management for core Clanker functionality."""

from .builder import ContextBuilder
from .store import ContextStore
from .templates import app_scaffold_context, coding_session_context, build_all_contexts
from .hints import get_smart_hints

__all__ = [
    "ContextBuilder",
    "ContextStore",
    "app_scaffold_context", 
    "coding_session_context",
    "build_all_contexts",
    "get_smart_hints",
]

