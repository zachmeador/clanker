"""Clanker - An LLM app environment with shared storage."""

from .agent import ClankerAgent
from .models import ModelTier, create_agent, list_available_providers
from .runtime import (
    RuntimeContext,
    bootstrap_runtime_context,
    get_runtime_context,
    set_runtime_context,
)
from .tools import create_clanker_toolset, discover_cli_exports, list_available_exports

__version__ = "0.1.0"

__all__ = [
    # Main classes
    "ClankerAgent",

    # Models and configuration
    "ModelTier",
    "create_agent",
    "list_available_providers",

    # Runtime context
    "RuntimeContext",
    "bootstrap_runtime_context",
    "get_runtime_context",
    "set_runtime_context",

    # Tool system
    "create_clanker_toolset",
    "discover_cli_exports",
    "list_available_exports",
]