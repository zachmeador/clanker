"""Simple logging abstraction for clanker and its apps."""

import sys
import uuid
from contextvars import ContextVar
from typing import Optional
from loguru import logger as _logger

from .profile import Profile

current_app_context: ContextVar[Optional[str]] = ContextVar('current_app_context', default=None)
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id_context', default=None)
_logger_configured: bool = False


def get_logger(app_name: Optional[str] = None):
    """Get a logger instance with optional app context."""
    global _logger_configured
    
    if app_name:
        current_app_context.set(app_name)
    
    # Configure logger on first use
    if not _logger_configured:
        _logger.remove()
        
        # Get current profile for log paths
        profile = Profile.current()
        
        # Stderr handler - only ERROR and above
        _logger.add(
            sys.stderr,
            level="ERROR",
            format="<red>{time:HH:mm:ss}</red> | <level>{level: <8}</level> | <cyan>{extra[app]}</cyan> | <level>{message}</level>",
            colorize=True,
        )
        
        # File handler - all logs (DEBUG and above)
        log_file = profile.log_file
        _logger.add(
            log_file,
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[app]} | {message}",
            rotation="100 MB",  # Rotate when file reaches 100MB
            retention="30 days",  # Keep logs for 30 days
            compression="zip",    # Compress rotated logs
            enqueue=True,        # Thread-safe logging
        )
        
        # Configure context patcher
        _logger.configure(patcher=_add_context)
        _logger_configured = True
    
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