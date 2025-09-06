"""Context management for core Clanker functionality."""

from .templates import app_scaffold_context, coding_session_context
from .hints import get_smart_hints

__all__ = [
    "app_scaffold_context",
    "coding_session_context",
    "get_smart_hints",
]

