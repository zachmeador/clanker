"""Unified tool system for Clanker apps."""

import os
import subprocess
import shlex
from pathlib import Path
from typing import Dict, List, Callable
import tomllib


from pydantic_ai.toolsets import FunctionToolset

from .logger import get_logger

logger = get_logger("tools")

# Tool display metadata for console
TOOL_DISPLAY = {
    "launch_coding_tool": {
        "name": "Launch Coding Tool",
        "description": "Start a coding session with any CLI coding tool"
    }
}

def get_tool_display_info(tool_name: str) -> dict:
    """Get display metadata for any tool."""
    
    # Check if it's a core tool with custom display
    if tool_name in TOOL_DISPLAY:
        return TOOL_DISPLAY[tool_name]
    
    # CLI export pattern: appname_command
    if "_" in tool_name:
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
            content = coding_session_context(tool, query)
            
            # Use tool-specific filename if needed
            context_file = "CLAUDE.md" if tool_lower == "claude" else "CLANKER_CONTEXT.md"
            
            with open(context_file, "w") as f:
                f.write(content)
            logger.info(f"Generated {context_file} with Clanker session context for {tool}")

        except Exception as e:
            error_msg = f"❌ Failed to write context file: {e}"
            logger.error(f"Launch tool failed to write context: {e}")
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

            # Use os.execvp to replace the current process with the tool
            # This gives us a clean session with the modified environment
            os.execvp(cli_command, [cli_command])

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
    logger.debug("Added core tool: launch_coding_tool")

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
