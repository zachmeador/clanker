"""Unified tool system for Clanker apps."""

import os
import shlex
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic_ai.toolsets import FunctionToolset

from .logger import get_logger
from .daemon import DaemonManager, DaemonStatus
from .profile import Profile
from .storage.db import DB
from .tool_registry import get_registry, tool

logger = get_logger("tools")


def get_tool_display_info(tool_name: str) -> dict:
    """Get display metadata for any tool."""
    return get_registry().get_display_info(tool_name)


@tool(
    name="Launch Coding Tool",
    description="Start a coding session with any CLI coding tool",
    category="core"
)
def launch_coding_tool(tool: str, query: str = "") -> str:
    """Launch an interactive coding CLI session with Clanker context.

    This tool generates appropriate context for the given query and launches
    the specified coding tool. The session 
    will be interactive with full context about the Clanker system.

    Args:
        tool: The coding tool to launch (e.g., "claude", "cursor")
        query: Optional description of what you want to work on (e.g., "work on the recipe app", "add new features")

    Returns:
        Status message about the launch
    """
    try:
        logger.info(f"Launch tool called for {tool} with query: {query}")

        # Map tool names to their CLI commands
        tool_commands = {
            "claude": "claude",
            "cursor": "cursor-agent",
            "gemini": "gemini",
            "codex": "codex",
        }
        
        tool_lower = tool.lower()
        if tool_lower not in tool_commands:
            return f"❌ Unknown coding tool: {tool}. Supported tools: {', '.join(tool_commands.keys())}"
        
        cli_command = tool_commands[tool_lower]

        # Generate context for all tools using unified system
        try:
            from .context import build_all_contexts
            results = build_all_contexts(query)
            
            # Log which files were successfully generated
            successful_files = [name for name, success in results.items() if success]
            if successful_files:
                logger.info(f"Generated context files: {', '.join(successful_files)}")
            else:
                logger.warning("No context files were successfully generated")
            
            # For the CLI launch, we'll read the content from INSTRUCTIONS.md  
            # since that's our master file now
            try:
                with open("INSTRUCTIONS.md", "r") as f:
                    full_context = f.read()
            except FileNotFoundError:
                # Fallback to basic context if INSTRUCTIONS.md doesn't exist
                full_context = "# Clanker Development Session\n\nWorking with Clanker codebase."
            
            # Build the full query with context included
            context_query = f"{full_context}\n\n---\n\n**User Request**: {query}" if query else full_context

        except Exception as e:
            error_msg = f"❌ Failed to generate context: {e}"
            logger.error(f"Launch tool failed to generate context: {e}")
            return error_msg

        # Launch the coding tool with proper TTY allocation
        try:
            logger.info(f"Launching {tool} session with pseudo-terminal")

            # Clean environment for coding tools (remove API keys that might conflict)
            api_keys_to_remove = [
                'ANTHROPIC_API_KEY',
                'OPENAI_API_KEY',
                'GOOGLE_API_KEY',
                'CLANKER_PROFILE',  # Remove Clanker-specific env vars
                'CLANKER_REQUESTER_APP'
            ]

            for key in api_keys_to_remove:
                os.environ.pop(key, None)

            # Build command arguments with full context
            if tool_lower == "gemini":
                # Gemini uses -i flag for interactive mode with query
                cmd_args = [cli_command, "-i", context_query]
            else:
                # Claude, Cursor, and Codex accept query directly
                cmd_args = [cli_command, context_query]
            
            # Use os.execvp to replace the current process with the tool
            # This gives us a clean session with the modified environment
            os.execvp(cli_command, cmd_args)

            # This code never executes - process is replaced above

        except FileNotFoundError:
            error_msg = f"❌ {tool} not found. Please install {tool} first."
            if tool_lower == "claude":
                error_msg += "\n💡 Visit: https://docs.anthropic.com/claude/docs/desktop-setup"
            logger.error(f"{tool} command not found")
            return error_msg

        except Exception as e:
            error_msg = f"❌ Failed to launch {tool}: {e}"
            logger.error(f"Launch tool failed to start {tool}: {e}")
            return error_msg

    except Exception as e:
        error_msg = f"❌ Launch tool failed: {e}"
        logger.error(f"Launch tool error: {e}")
        return error_msg


def _discover_app_metadata() -> Dict[str, Dict[str, Any]]:
    """Discover apps and their metadata - legacy interface for app_context."""
    registry = get_registry()
    result = {}
    
    for app_name in registry.list_apps():
        manifest = registry.get_app_manifest(app_name)
        if manifest:
            result[app_name] = {
                "summary": manifest.summary,
                "capabilities": manifest.capabilities,
                "examples": manifest.examples,
                "tools": {}
            }
            
            # Convert tool metadata back to legacy format for app_context
            for export_name, metadata in manifest.tool_metadata.items():
                result[app_name]["tools"][export_name] = {
                    "cli": manifest.exports[export_name],
                    "description": metadata.description,
                    "params": {name: {
                        "type": param.type,
                        "required": param.required,
                        "default": param.default,
                        "description": param.description
                    } for name, param in metadata.parameters.items()},
                    "flags": {
                        "needs_confirmation": metadata.needs_confirmation
                    }
                }
    
    return result

@tool(
    name="List Daemons",
    description="Show all registered daemons and their status",
    category="daemon"
)
def daemon_list() -> str:
    """List all registered daemons with their current status.
    
    Returns:
        Formatted string showing daemon status information
    """
    try:
        manager = DaemonManager()
        daemons = manager.list_daemons()
        
        if not daemons:
            return "No daemons registered."
        
        output = ["Registered Daemons:"]
        output.append("-" * 60)
        
        for daemon in daemons:
            app_daemon = f"{daemon['app_name']}:{daemon['daemon_id']}"
            status = daemon['status']
            if status == DaemonStatus.RUNNING:
                uptime_str = f"{daemon['uptime']:.1f}s" if daemon['uptime'] else "unknown"
                memory_str = f"{daemon['memory_mb']:.1f}MB" if daemon['memory_mb'] else "unknown"
                output.append(f"✓ {app_daemon:30} RUNNING (PID: {daemon['pid']}, uptime: {uptime_str}, mem: {memory_str})")
            elif status == DaemonStatus.STOPPED:
                extra = []
                if daemon.get('ended_at'):
                    extra.append(f"ended: {daemon['ended_at']}")
                if daemon.get('exit_code') is not None:
                    extra.append(f"exit: {daemon['exit_code']}")
                suffix = f" ({', '.join(extra)})" if extra else ""
                output.append(f"○ {app_daemon:30} STOPPED{suffix}")
            elif status == DaemonStatus.CRASHED:
                extra = []
                if daemon.get('ended_at'):
                    extra.append(f"ended: {daemon['ended_at']}")
                if daemon.get('exit_code') is not None:
                    extra.append(f"exit: {daemon['exit_code']}")
                suffix = f" ({', '.join(extra)})" if extra else ""
                output.append(f"✗ {app_daemon:30} CRASHED{suffix}")
            else:
                output.append(f"? {app_daemon:30} {status.upper()}")
        
        return "\n".join(output)
        
    except Exception as e:
        logger.error(f"Failed to list daemons: {e}")
        return f"Error listing daemons: {e}"


@tool(
    name="Start Daemon", 
    description="Start a specific app daemon",
    category="daemon"
)
def daemon_start(app_name: str, daemon_id: str) -> str:
    """Start a specific daemon.
    
    Args:
        app_name: Name of the app
        daemon_id: ID of the daemon to start
        
    Returns:
        Status message about the start operation
    """
    try:
        # Get daemon configuration from app's pyproject.toml
        daemon_configs = discover_daemon_configs()
        
        if app_name not in daemon_configs:
            return f"❌ No daemon configurations found for app '{app_name}'"
            
        if daemon_id not in daemon_configs[app_name]:
            available = ", ".join(daemon_configs[app_name].keys())
            return f"❌ Daemon '{daemon_id}' not found in app '{app_name}'. Available: {available}"
        
        command_template = daemon_configs[app_name][daemon_id]
        
        # Parse command template and run in app's uv environment
        import shlex
        base_command = shlex.split(command_template)
        
        # Create daemon and start it
        manager = DaemonManager()
        daemon = manager.get_daemon(app_name, daemon_id)
        
        if daemon.is_running():
            return f"⚠️ Daemon {app_name}:{daemon_id} is already running"
        
        app_dir = Path("./apps") / app_name
        uv_command = ["uv", "run", "--project", f"apps/{app_name}"] + base_command
        success = daemon.start(uv_command, cwd=app_dir)
        
        if success:
            pid = daemon.get_pid()
            return f"✅ Started daemon {app_name}:{daemon_id} (PID: {pid})"
        else:
            return f"❌ Failed to start daemon {app_name}:{daemon_id}"
            
    except Exception as e:
        logger.error(f"Failed to start daemon {app_name}:{daemon_id}: {e}")
        return f"❌ Error starting daemon: {e}"


@tool(
    name="Stop Daemon",
    description="Stop a specific app daemon", 
    category="daemon"
)
def daemon_stop(app_name: str, daemon_id: str) -> str:
    """Stop a specific daemon.
    
    Args:
        app_name: Name of the app
        daemon_id: ID of the daemon to stop
        
    Returns:
        Status message about the stop operation
    """
    try:
        manager = DaemonManager()
        daemon = manager.get_daemon(app_name, daemon_id)
        
        if not daemon.is_running():
            return f"⚠️ Daemon {app_name}:{daemon_id} is not running"
        
        success = daemon.stop()
        
        if success:
            return f"✅ Stopped daemon {app_name}:{daemon_id}"
        else:
            return f"❌ Failed to stop daemon {app_name}:{daemon_id}"
            
    except Exception as e:
        logger.error(f"Failed to stop daemon {app_name}:{daemon_id}: {e}")
        return f"❌ Error stopping daemon: {e}"


@tool(
    name="View Daemon Logs",
    description="View recent log output from a daemon",
    category="daemon"
)
def daemon_logs(app_name: str, daemon_id: str, lines: int = 50) -> str:
    """View recent log output from a daemon.
    
    Args:
        app_name: Name of the app
        daemon_id: ID of the daemon
        lines: Number of lines to show (default 50)
        
    Returns:
        Recent log output
    """
    try:
        manager = DaemonManager()
        daemon = manager.get_daemon(app_name, daemon_id)
        
        log_lines = daemon.get_logs(lines)
        
        if not log_lines:
            return f"No logs available for daemon {app_name}:{daemon_id}"
        
        output = [f"Recent logs for {app_name}:{daemon_id} (last {len(log_lines)} lines):"]
        output.append("-" * 60)
        output.extend(log_lines)
        
        return "\n".join(output)
        
    except Exception as e:
        logger.error(f"Failed to get logs for daemon {app_name}:{daemon_id}: {e}")
        return f"❌ Error getting logs: {e}"


@tool(
    name="Daemon Status",
    description="Show status for one daemon",
    category="daemon"
)
def daemon_status(app_name: str, daemon_id: str) -> str:
    """Show status for a specific daemon."""
    try:
        manager = DaemonManager()
        daemon = manager.get_daemon(app_name, daemon_id)
        st = daemon.get_status()
        app_daemon = f"{st['app_name']}:{st['daemon_id']}"
        status = st['status']
        if status == DaemonStatus.RUNNING:
            uptime_str = f"{st['uptime']:.1f}s" if st['uptime'] else "unknown"
            mem = f"{st['memory_mb']:.1f}MB" if st['memory_mb'] else "unknown"
            return f"{app_daemon} RUNNING (PID {st['pid']}, uptime {uptime_str}, mem {mem})"
        return f"{app_daemon} {status.upper()}"
    except Exception as e:
        logger.error(f"Failed to fetch daemon status {app_name}:{daemon_id}: {e}")
        return f"❌ Error getting status: {e}"


@tool(
    name="Restart Daemon",
    description="Restart a specific app daemon",
    category="daemon"
)
def daemon_restart(app_name: str, daemon_id: str) -> str:
    """Restart a specific daemon."""
    try:
        stop_msg = daemon_stop(app_name, daemon_id)
        # Ignore not running
        start_msg = daemon_start(app_name, daemon_id)
        return f"{stop_msg}\n{start_msg}"
    except Exception as e:
        logger.error(f"Failed to restart daemon {app_name}:{daemon_id}: {e}")
        return f"❌ Error restarting daemon: {e}"


@tool(
    name="Enable Autostart",
    description="Enable autostart for a daemon",
    category="daemon"
)
def daemon_enable_autostart(app_name: str, daemon_id: str) -> str:
    """Enable autostart for a daemon."""
    try:
        manager = DaemonManager()
        manager.set_autostart(app_name, daemon_id, True)
        return f"✅ Enabled autostart for {app_name}:{daemon_id}"
    except Exception as e:
        logger.error(f"Failed to enable autostart for {app_name}:{daemon_id}: {e}")
        return f"❌ Error enabling autostart: {e}"


@tool(
    name="Disable Autostart",
    description="Disable autostart for a daemon",
    category="daemon"
)
def daemon_disable_autostart(app_name: str, daemon_id: str) -> str:
    """Disable autostart for a daemon."""
    try:
        manager = DaemonManager()
        manager.set_autostart(app_name, daemon_id, False)
        return f"✅ Disabled autostart for {app_name}:{daemon_id}"
    except Exception as e:
        logger.error(f"Failed to disable autostart for {app_name}:{daemon_id}: {e}")
        return f"❌ Error disabling autostart: {e}"


@tool(
    name="Start Enabled Daemons",
    description="Start all daemons marked autostart",
    category="daemon"
)
def daemon_start_enabled() -> str:
    """Start all daemons marked for autostart."""
    try:
        manager = DaemonManager()
        results = manager.start_enabled_daemons()
        if not results:
            return "No enabled daemons to start."
        ok = [k for k, v in results.items() if v]
        bad = [k for k, v in results.items() if not v]
        lines = []
        if ok:
            lines.append("Started:")
            lines.extend([f"✅ {k}" for k in ok])
        if bad:
            if lines:
                lines.append("")
            lines.append("Failed:")
            lines.extend([f"❌ {k}" for k in bad])
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to start enabled daemons: {e}")
        return f"❌ Error starting enabled daemons: {e}"


@tool(
    name="List Autostart Daemons",
    description="List daemons with autostart enabled",
    category="daemon"
)
def daemon_autostart_list() -> str:
    """List daemons with autostart enabled, and whether running."""
    try:
        import sqlite3
        manager = DaemonManager()
        # Gather enabled rows from DB
        enabled = []
        with sqlite3.connect(manager.profile.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT app_name, daemon_id FROM _daemon_startup WHERE enabled = 1 ORDER BY app_name, daemon_id")
            enabled = [(r['app_name'], r['daemon_id']) for r in cur.fetchall()]

        if not enabled:
            return "No daemons enabled for autostart."

        # Check configs and running status
        configs = discover_daemon_configs()
        lines = ["Autostart-enabled daemons:", "-" * 60]
        for app_name, daemon_id in enabled:
            has_config = daemon_id in (configs.get(app_name, {}) or {})
            daemon = manager.get_daemon(app_name, daemon_id)
            running = daemon.is_running()
            flags = []
            flags.append("running" if running else "stopped")
            if not has_config:
                flags.append("missing config")
            line = f"• {app_name}:{daemon_id} ({', '.join(flags)})"
            lines.append(line)

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to list autostart daemons: {e}")
        return f"❌ Error listing autostart daemons: {e}"


@tool(
    name="Kill All Daemons",
    description="Emergency stop all running daemons",
    category="daemon"
)
def daemon_kill_all() -> str:
    """Emergency stop all running daemons.
    
    Returns:
        Status message about the kill operation
    """
    try:
        manager = DaemonManager()
        results = manager.stop_all_daemons()
        
        if not results:
            return "No running daemons to stop."
        
        output = ["Daemon shutdown results:"]
        success_count = 0
        
        for daemon_name, success in results.items():
            if success:
                output.append(f"✅ {daemon_name}")
                success_count += 1
            else:
                output.append(f"❌ {daemon_name}")
        
        total = len(results)
        output.append(f"\nStopped {success_count}/{total} daemons successfully")
        
        return "\n".join(output)
        
    except Exception as e:
        logger.error(f"Failed to kill all daemons: {e}")
        return f"❌ Error killing daemons: {e}"


def discover_daemon_configs() -> Dict[str, Dict[str, str]]:
    """Discover daemon configurations from all apps.
    
    Returns:
        Dict mapping app_name -> {daemon_id: command_template}
    """
    registry = get_registry()
    configs = {}
    
    for app_name in registry.list_apps():
        manifest = registry.get_app_manifest(app_name)
        if manifest and manifest.daemons:
            configs[app_name] = manifest.daemons
            
    return configs


def discover_cli_exports() -> Dict[str, Dict[str, str]]:
    """
    Discover CLI exports from all apps.

    Returns:
        Dict mapping app_name -> {export_name: cli_command_template}
    """
    registry = get_registry()
    exports = {}
    
    for app_name in registry.list_apps():
        manifest = registry.get_app_manifest(app_name)
        if manifest and manifest.exports:
            exports[app_name] = manifest.exports
            
    return exports




def create_clanker_toolset() -> FunctionToolset:
    """
    Create the main clanker toolset with all CLI export tools and core tools.

    This creates tools from all apps that have [tool.clanker.exports] in their pyproject.toml,
    plus core Clanker tools like launch_coding_tool.
    """
    registry = get_registry()
    
    # Discover and register all apps
    registry.discover_apps()
    
    # Register core tools
    core_tools = [
        launch_coding_tool,
        daemon_list,
        daemon_start,
        daemon_stop,
        daemon_logs,
        daemon_kill_all,
        daemon_status,
        daemon_restart,
        daemon_enable_autostart,
        daemon_disable_autostart,
        daemon_start_enabled,
        daemon_autostart_list,
        app_context
    ]
    
    for tool_func in core_tools:
        if hasattr(tool_func, '__tool_metadata__'):
            registry.register(tool_func, tool_func.__tool_metadata__)
        else:
            # Fallback for tools without metadata
            logger.warning(f"Core tool {tool_func.__name__} missing metadata decorator")
    
    # Create pydantic toolset from registry
    toolset = FunctionToolset()
    for tool_name in registry.list_tools():
        tool_func = registry.get_tool(tool_name)
        if tool_func:
            toolset.add_function(tool_func)
            logger.debug(f"Added tool: {tool_name}")
    
    return toolset


def list_available_exports() -> Dict[str, List[str]]:
    """List all available CLI exports by app."""
    registry = get_registry()
    result = {}
    
    for app_name in registry.list_apps():
        manifest = registry.get_app_manifest(app_name)
        if manifest and manifest.exports:
            result[app_name] = list(manifest.exports.keys())
    
    return result


# --------------------------
# App context tool
# --------------------------

@tool(
    name="App Context",
    description="Return structured metadata for an app",
    category="app"
)
def app_context(app: str, detail: str = "summary", tool: Optional[str] = None) -> Dict[str, Any]:
    """Return compact, structured context for an app for LLM use."""
    detail = (detail or "summary").lower()
    meta_all = _discover_app_metadata()
    app_meta = meta_all.get(app, {})

    # Tools
    tools: List[Dict[str, Any]] = []
    for name, tmeta in (app_meta.get("tools", {}) or {}).items():
        if tool and name != tool:
            continue
        params_list = []
        for pname, pspec in (tmeta.get("params", {}) or {}).items():
            params_list.append({
                "name": pname,
                "type": pspec.get("type", "str"),
                "required": bool(pspec.get("required", True)),
                "default": pspec.get("default"),
                "description": pspec.get("description"),
            })
        tools.append({
            "name": name,
            "description": tmeta.get("description"),
            "params": params_list,
            "flags": tmeta.get("flags", {}),
        })

    # Daemons
    daemons_info: List[Dict[str, Any]] = []
    try:
        cfgs = discover_daemon_configs()
        if app in cfgs:
            manager = DaemonManager()
            listed = { (d['app_name'], d['daemon_id']): d for d in manager.list_daemons() }
            for did, cmd in cfgs[app].items():
                status = manager.get_daemon(app, did).get_status()
                merged = listed.get((app, did), {})
                daemons_info.append({
                    "id": did,
                    "command": cmd,
                    "status": status.get("status"),
                    "pid": status.get("pid"),
                    "uptime": status.get("uptime"),
                    "last_heartbeat": merged.get("last_heartbeat"),
                    "ended_at": merged.get("ended_at"),
                    "exit_code": merged.get("exit_code"),
                })
    except Exception as e:
        logger.error(f"Failed to gather daemon info for app '{app}': {e}", exc_info=True)

    # Data (db tables and vault roots)
    data_info: Dict[str, Any] = {}
    try:
        profile = Profile.current()
        # Get app's isolated database and list its tables
        app_db = DB.for_app(app, profile)
        data_info["db_tables"] = app_db.tables()[:5]

        vault_root = profile.vault_root / app
        if vault_root.exists():
            entries = [p.name for p in vault_root.iterdir() if p.is_dir()][:5]
        else:
            entries = []
        data_info["vault_roots"] = entries
    except Exception as e:
        logger.error(f"Failed to gather storage info for app '{app}': {e}", exc_info=True)
        data_info = {"db_tables": [], "vault_roots": []}

    # Build response
    base = {
        "app": app,
        "summary": app_meta.get("summary"),
        "capabilities": app_meta.get("capabilities", []),
    }

    if detail == "summary":
        top_tools = [t.get("name") for t in tools][:3]
        base.update({"tools": top_tools})
        return base
    if detail == "tools":
        base.update({"tools": tools})
        return base
    if detail == "daemons":
        base.update({"daemons": daemons_info})
        return base
    if detail == "data":
        base.update({"data": data_info})
        return base
    if detail == "examples":
        base.update({"examples": app_meta.get("examples", [])})
        return base

    # full
    base.update({
        "tools": tools,
        "daemons": daemons_info,
        "data": data_info,
        "examples": app_meta.get("examples", []),
    })
    return base
