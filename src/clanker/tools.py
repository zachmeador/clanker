"""Unified tool system for Clanker apps."""

import os
import subprocess
import shlex
from pathlib import Path
from typing import Dict, List, Callable
import tomllib


from pydantic_ai.toolsets import FunctionToolset

from .logger import get_logger
from .daemon import DaemonManager, DaemonStatus

logger = get_logger("tools")

# Tool display metadata for console
TOOL_DISPLAY = {
    "launch_coding_tool": {
        "name": "Launch Coding Tool",
        "description": "Start a coding session with any CLI coding tool"
    },
    "daemon_list": {
        "name": "List Daemons",
        "description": "Show all registered daemons and their status"
    },
    "daemon_start": {
        "name": "Start Daemon",
        "description": "Start a specific app daemon"
    },
    "daemon_stop": {
        "name": "Stop Daemon", 
        "description": "Stop a specific app daemon"
    },
    "daemon_logs": {
        "name": "View Daemon Logs",
        "description": "View recent log output from a daemon"
    },
    "daemon_kill_all": {
        "name": "Kill All Daemons",
        "description": "Emergency stop all running daemons"
    }
}

def get_tool_display_info(tool_name: str) -> dict:
    """Get display metadata for any tool."""
    
    # Check if it's a core tool with custom display
    if tool_name in TOOL_DISPLAY:
        return TOOL_DISPLAY[tool_name]
    
    # CLI export pattern: appname_command
    # Need to find the correct split point by checking discovered exports
    if "_" in tool_name:
        exports = discover_cli_exports()
        for app_name, app_exports in exports.items():
            for export_name in app_exports.keys():
                expected_tool_name = f"{app_name}_{export_name}"
                if tool_name == expected_tool_name:
                    return {
                        "name": f"{app_name} {export_name}",
                        "description": f"Run {export_name} from {app_name} app"
                    }
        
        # Fallback to simple split if not found in exports
        parts = tool_name.split("_", 1)
        if len(parts) == 2:
            app, command = parts
            return {
                "name": f"{app} {command}",
                "description": f"Run {command} from {app} app"
            }
    
    # Fallback
    return {
        "name": tool_name,
        "description": ""
    }


def launch_coding_tool(tool: str, query: str) -> str:
    """Launch an interactive coding CLI session with Clanker context.

    This tool generates appropriate context for the given query and launches
    the specified coding tool (Claude, Cursor, Windsurf, etc.). The session 
    will be interactive with full context about the Clanker system.

    Args:
        tool: The coding tool to launch (e.g., "claude", "cursor")
        query: Description of what you want to work on (e.g., "work on the recipe app", "add new features")

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
        }
        
        tool_lower = tool.lower()
        if tool_lower not in tool_commands:
            return f"❌ Unknown coding tool: {tool}. Supported tools: {', '.join(tool_commands.keys())}"
        
        cli_command = tool_commands[tool_lower]

        # Generate context using coding_session_context
        try:
            from .context import coding_session_context
            full_context = coding_session_context(tool, query)
            
            # Use tool-specific filename for each tool
            context_files = {
                "claude": "CLAUDE.md",
                "gemini": "GEMINI.md",
                "cursor": "CLANKER_CONTEXT.md",
            }
            context_file = context_files.get(tool_lower, "CLANKER_CONTEXT.md")
            
            # Write context file for reference
            with open(context_file, "w") as f:
                f.write(full_context)
            logger.info(f"Generated {context_file} with Clanker session context for {tool}")
            
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
                'GROQ_API_KEY',
                'MISTRAL_API_KEY',
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
                # Claude and Cursor accept query directly
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
                output.append(f"○ {app_daemon:30} STOPPED")
            elif status == DaemonStatus.CRASHED:
                output.append(f"✗ {app_daemon:30} CRASHED")
            else:
                output.append(f"? {app_daemon:30} {status.upper()}")
        
        return "\n".join(output)
        
    except Exception as e:
        logger.error(f"Failed to list daemons: {e}")
        return f"Error listing daemons: {e}"


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
        
        # Parse command template
        import shlex
        command = shlex.split(command_template)
        
        # Create daemon and start it
        manager = DaemonManager()
        daemon = manager.get_daemon(app_name, daemon_id)
        
        if daemon.is_running():
            return f"⚠️ Daemon {app_name}:{daemon_id} is already running"
        
        app_dir = Path("./apps") / app_name
        success = daemon.start(command, cwd=app_dir)
        
        if success:
            pid = daemon.get_pid()
            return f"✅ Started daemon {app_name}:{daemon_id} (PID: {pid})"
        else:
            return f"❌ Failed to start daemon {app_name}:{daemon_id}"
            
    except Exception as e:
        logger.error(f"Failed to start daemon {app_name}:{daemon_id}: {e}")
        return f"❌ Error starting daemon: {e}"


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
    apps_dir = Path("./apps")
    if not apps_dir.exists():
        return {}
    
    configs = {}
    
    for item in apps_dir.iterdir():
        if not item.is_dir() or item.name.startswith(('_', '.')):
            continue
            
        pyproject_path = item / "pyproject.toml"
        if not pyproject_path.exists():
            continue
        
        try:
            with open(pyproject_path, 'rb') as f:
                pyproject = tomllib.load(f)
            
            # Look for daemon configurations
            daemon_configs = pyproject.get("tool", {}).get("clanker", {}).get("daemons", {})
            if daemon_configs:
                configs[item.name] = dict(daemon_configs)
                logger.debug(f"Found {len(daemon_configs)} daemon configs for {item.name}")
                
        except Exception as e:
            logger.warning(f"Failed to read daemon configs from {item.name}: {e}")
    
    return configs


def discover_cli_exports() -> Dict[str, Dict[str, str]]:
    """
    Discover CLI exports from all apps in ./apps/.

    Returns:
        Dict mapping app_name -> {export_name: cli_command_template}
    """
    apps_dir = Path("./apps")
    if not apps_dir.exists():
        return {}

    exports = {}

    for item in apps_dir.iterdir():
        if not item.is_dir() or item.name.startswith(('_', '.')):
            continue

        pyproject_path = item / "pyproject.toml"
        if not pyproject_path.exists():
            continue

        # Read pyproject.toml
        try:
            with open(pyproject_path, 'rb') as f:
                pyproject = tomllib.load(f)

            # Look for clanker exports
            clanker_exports = pyproject.get("tool", {}).get("clanker", {}).get("exports", {})
            if clanker_exports:
                exports[item.name] = dict(clanker_exports)
                logger.debug(f"Found {len(clanker_exports)} exports for {item.name}")

        except Exception as e:
            logger.warning(f"Failed to read exports from {item.name}: {e}")

    return exports


def create_tool_function(app_name: str, export_name: str, cli_template: str) -> Callable:
    """Create a tool function that executes a CLI command."""

    # Extract parameter names from the CLI template
    import re
    param_names = re.findall(r'\{(\w+)\}', cli_template)

    def tool_function(**kwargs) -> str:
        """Execute CLI command as tool."""
        try:
            # Provide default values for missing parameters
            for param in param_names:
                if param not in kwargs:
                    if param == 'name':
                        kwargs[param] = 'World'  # Default name
                    else:
                        kwargs[param] = ''  # Empty string for other params

            # Format the CLI command with arguments
            command = cli_template.format(**kwargs)

            # Execute in app's environment
            result = subprocess.run(
                ["uv", "run", "--project", f"apps/{app_name}"] + shlex.split(command),
                capture_output=True,
                text=True,
                cwd=f"./apps/{app_name}",  # Run from app directory
                timeout=30
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                error_msg = result.stderr.strip() or f"Command failed with exit code {result.returncode}"
                return f"Error: {error_msg}"

        except subprocess.TimeoutExpired:
            return f"Command timed out: {cli_template.format(**kwargs)}"
        except Exception as e:
            logger.error(f"Tool execution failed for {app_name}.{export_name}: {e}")
            return f"Tool execution failed: {str(e)}"

    # Set metadata
    tool_function.__name__ = f"{app_name}_{export_name}"
    tool_function.__doc__ = f"Execute {app_name} {export_name} command"

    return tool_function


def create_clanker_toolset() -> FunctionToolset:
    """
    Create the main clanker toolset with all CLI export tools and core tools.

    This creates tools from all apps that have [tool.clanker.exports] in their pyproject.toml,
    plus core Clanker tools like launch_coding_tool.
    """
    exports = discover_cli_exports()
    toolset = FunctionToolset()

    # Add core Clanker tools first
    toolset.add_function(launch_coding_tool)
    toolset.add_function(daemon_list)
    toolset.add_function(daemon_start)
    toolset.add_function(daemon_stop)
    toolset.add_function(daemon_logs)
    toolset.add_function(daemon_kill_all)
    logger.debug("Added core tools: launch_coding_tool, daemon management")

    # Add CLI export tools from apps
    for app_name, app_exports in exports.items():
        for export_name, cli_template in app_exports.items():
            tool_func = create_tool_function(app_name, export_name, cli_template)
            toolset.add_function(tool_func)
            logger.debug(f"Created tool: {app_name}_{export_name}")

    return toolset


def list_available_exports() -> Dict[str, List[str]]:
    """List all available CLI exports by app."""
    exports = discover_cli_exports()
    return {app_name: list(app_exports.keys()) for app_name, app_exports in exports.items()}
