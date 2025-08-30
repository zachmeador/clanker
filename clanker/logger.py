"""Simple logging abstraction for clanker and its apps."""

import sys
import uuid
from contextvars import ContextVar
from typing import Optional
from loguru import logger as _logger

current_app_context: ContextVar[Optional[str]] = ContextVar('current_app_context', default=None)
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id_context', default=None)


def get_logger(app_name: Optional[str] = None):
    """Get a logger instance with optional app context."""
    if app_name:
        current_app_context.set(app_name)
    
    # Configure logger on first use
    if not _logger._core.handlers:
        _logger.remove()
        _logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[app]}</cyan> | <level>{message}</level>",
            colorize=True,
        )
        _logger.configure(patcher=_add_context)
    
    return _logger


def _add_context(record):
    """Add context variables to log record."""
    app = current_app_context.get()
    request_id = request_id_context.get()
    
    record["extra"]["app"] = app or "clanker"
    record["extra"]["request_id"] = request_id or ""


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set the request ID for the current context. Generates one if not provided."""
    if request_id is None:
        request_id = str(uuid.uuid4())[:8]
    request_id_context.set(request_id)
    return request_id


def clear_request_id() -> None:
    """Clear the request ID from the current context."""
    request_id_context.set(None)


logger = get_logger()

__all__ = [
    "logger",
    "get_logger",
    "set_request_id",
    "clear_request_id",
]