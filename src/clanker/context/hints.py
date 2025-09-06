"""Simple app-level hints for the Clanker agent.

Provides brief, non-redundant context about apps - not tools.
Pydantic-AI handles tool discovery automatically.
"""

from typing import List
from ..tool_registry import get_registry
from ..daemon import DaemonManager, DaemonStatus
from ..logger import get_logger

logger = get_logger("hints")


def get_app_hints() -> str:
    """Generate simple app-level hints for LLM context."""
    try:
        registry = get_registry()
        registry.discover_apps()
        
        hints = []
        
        # App-specific hints (1-4 lines per app)
        for app_name in registry.list_apps():
            manifest = registry.get_app_manifest(app_name)
            if not manifest:
                continue
                
            if app_name == "example":
                hints.append("example app: Test with 'hello NAME' or 'check status' or 'weather NYC'. Returns formatted greetings, status tables, or mock weather data.")
            
            elif "weather" in app_name.lower() or "weather" in (manifest.capabilities or []):
                hints.append(f"{app_name}: Ask 'what's the weather in CITY'. Returns JSON weather data, may cache results.")
            
            elif "recipe" in app_name.lower() or "cooking" in (manifest.capabilities or []):
                hints.append(f"{app_name}: Try 'find recipe for pasta' or 'get recipe details'. Returns structured recipe data from nutritional databases.")
            
            elif manifest.summary and len(manifest.exports) > 0:
                # Generic hint for other apps
                tool_count = len(manifest.exports)
                hints.append(f"{app_name}: {manifest.summary} ({tool_count} tools available).")
        
        # System-level context
        daemon_tools = [t for t in registry.list_tools() if 'daemon' in t]
        if daemon_tools:
            try:
                daemon_manager = DaemonManager()
                daemons = daemon_manager.list_daemons()
                running_count = len([d for d in daemons if d['status'] == DaemonStatus.RUNNING])
                if running_count > 0:
                    hints.append(f"System: {running_count} daemons running. Use daemon_list to check status.")
                else:
                    hints.append("System: No daemons running. Use daemon_start to launch background services.")
            except Exception:
                hints.append(f"System: {len(daemon_tools)} daemon management tools available.")
        
        return "\n".join(hints) if hints else "No app-specific context available."
        
    except Exception as e:
        logger.warning(f"Failed to generate app hints: {e}")
        return "App context unavailable."


# Main entry point - keeping same name for compatibility
def get_smart_hints() -> str:
    """Get app hints for the agent context."""
    return get_app_hints()