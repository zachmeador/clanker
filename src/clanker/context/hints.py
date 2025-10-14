"""Simple app-level hints for the Clanker agent.

Provides brief, non-redundant context about apps - not tools.
Pydantic-AI handles tool discovery automatically.
"""

from ..tool_registry import get_registry
from ..daemon import DaemonManager, DaemonStatus
from ..logger import get_logger

logger = get_logger("hints")


def get_app_hints() -> str:
    """Generate simple app-level hints for LLM context."""
    try:
        registry = get_registry()
        # Only discover apps if not already loaded
        if not registry.list_apps():
            registry.discover_apps()

        hints = []
        
        # App-specific hints (1-4 lines per app)
        for app_name in registry.list_apps():
            manifest = registry.get_app_manifest(app_name)
            if not manifest:
                continue

            # Generic hint for all apps based on manifest
            if manifest.summary and len(manifest.exports) > 0:
                tool_count = len(manifest.exports)
                hints.append(f"{app_name}: {manifest.summary} ({tool_count} tools available).")
        
        # System-level context
        has_daemon_tools = any('daemon' in t.lower() for t in registry.list_tools())
        if has_daemon_tools:
            try:
                from ..runtime import get_runtime_context
                daemon_manager = DaemonManager(runtime=get_runtime_context())
                daemons = daemon_manager.list_daemons()
                running_count = len([d for d in daemons if d['status'] == DaemonStatus.RUNNING])
                if running_count > 0:
                    hints.append(f"System: {running_count} daemons running. Use daemon_list to check status.")
                else:
                    hints.append("System: No daemons running. Use daemon_start to launch background services.")
            except Exception as e:
                logger.error(f"Failed to get daemon status: {e}", exc_info=True)
                hints.append("System: Daemon management tools available.")
        
        return "\n".join(hints) if hints else "No app-specific context available."

    except Exception as e:
        logger.error(f"Failed to generate app hints: {e}", exc_info=True)
        return "App context unavailable."


# Main entry point - keeping same name for compatibility
def get_smart_hints() -> str:
    """Get app hints for the agent context."""
    return get_app_hints()