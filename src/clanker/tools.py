"""Unified tool system for Clanker apps."""

import os
import subprocess
import shlex
from pathlib import Path
from typing import Dict, List, Callable, Optional
import tomllib
import pty

from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset

from .logger import get_logger
from .context import CoreContextManager

logger = get_logger("tools")


def launch_claude_code(ctx: Optional[RunContext], query: str) -> str:
    """Launch an interactive Claude Code session with Clanker context.

    This tool generates appropriate context for the given query and launches
    Claude Code with that context. The session will be interactive and allow
    you to work on your project with full context awareness.

    Args:
        query: Description of what you want to work on (e.g., "work on the recipe app", "add new features")

    Returns:
        Status message about the launch
    """
    try:
        logger.info(f"Launch tool called with query: {query}")

        # Extract potential app name from query
        app_name = None
        query_lower = query.lower()

        # Simple app detection - look for app names in the query
        if "recipe" in query_lower:
            app_name = "recipe"  # This could be more sophisticated
        elif "example" in query_lower:
            app_name = "example"

        # Generate context
        manager = CoreContextManager()
        context = manager.get_session_context("claude", app_name, query)

        # Write context file
        try:
            with open("CLAUDE.md", "w") as f:
                f.write(context)
            logger.info("Generated CLAUDE.md with context")

        except Exception as e:
            error_msg = f"❌ Failed to write CLAUDE.md: {e}"
            logger.error(f"Launch tool failed to write context: {e}")
            return error_msg

        # Launch Claude Code with proper TTY allocation
        try:
            logger.info("Launching Claude Code session with pseudo-terminal")

            # Create clean environment for Claude Code (remove API keys)
            env = os.environ.copy()

            # Remove API keys that might conflict with Claude Code
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
                env.pop(key, None)

            # Use pty.spawn to properly allocate a pseudo-terminal
            # This gives Claude Code a real terminal environment
            pty.spawn(["claude"], env)

            # This code never executes - process is replaced above

        except FileNotFoundError:
            error_msg = "❌ Claude Code not found. Please install Claude CLI first."
            error_msg += "\n💡 Visit: https://docs.anthropic.com/claude/docs/desktop-setup"
            logger.error("Claude command not found")
            return error_msg

        except Exception as e:
            error_msg = f"❌ Failed to launch Claude Code: {e}"
            logger.error(f"Launch tool failed to start claude: {e}")
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

    def tool_function(ctx: RunContext, **kwargs) -> str:
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
    plus core Clanker tools like launch_claude_code.
    """
    exports = discover_cli_exports()
    tools = []

    # Add core Clanker tools first
    tools.append(launch_claude_code)
    logger.debug("Added core tool: launch_claude_code")

    # Add CLI export tools from apps
    for app_name, app_exports in exports.items():
        for export_name, cli_template in app_exports.items():
            tool = create_tool_function(app_name, export_name, cli_template)
            tools.append(tool)
            logger.debug(f"Created tool: {app_name}_{export_name}")

    return FunctionToolset(tools=tools)


def list_available_exports() -> Dict[str, List[str]]:
    """List all available CLI exports by app."""
    exports = discover_cli_exports()
    return {app_name: list(app_exports.keys()) for app_name, app_exports in exports.items()}
