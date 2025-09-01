"""CLI-based export system for Clanker apps."""

import subprocess
import shlex
from pathlib import Path
from typing import Dict, List, Optional, Any
import tomllib

from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset
from .logger import get_logger

logger = get_logger("exports")


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


def create_cli_export_toolset() -> FunctionToolset:
    """
    Create toolset from CLI exports discovered from apps.

    This creates tools that execute subprocess calls to app CLIs.
    """
    exports = discover_cli_exports()
    tools = []

    for app_name, app_exports in exports.items():
        for export_name, cli_template in app_exports.items():

            def create_tool_wrapper(app_name: str, export_name: str, cli_template: str):
                """Create a tool that executes the CLI command."""
                def tool_wrapper(ctx: RunContext, **kwargs) -> str:
                    """Execute CLI command as tool."""
                    try:
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
                tool_wrapper.__name__ = f"{app_name}_{export_name}"
                tool_wrapper.__doc__ = f"Execute {app_name} {export_name} command"

                return tool_wrapper

            # Create and add the tool
            tool = create_tool_wrapper(app_name, export_name, cli_template)
            tools.append(tool)
            logger.debug(f"Created tool: {app_name}_{export_name}")

    return FunctionToolset(tools=tools)


def list_available_cli_exports() -> Dict[str, List[str]]:
    """List all available CLI exports by app."""
    exports = discover_cli_exports()
    return {app_name: list(app_exports.keys()) for app_name, app_exports in exports.items()}


def execute_cli_export(app_name: str, export_name: str, **kwargs) -> str:
    """
    Execute a specific CLI export directly.

    This is for testing and direct execution.
    """
    exports = discover_cli_exports()

    if app_name not in exports:
        return f"App '{app_name}' not found"

    app_exports = exports[app_name]
    if export_name not in app_exports:
        available = list(app_exports.keys())
        return f"Export '{export_name}' not found. Available: {available}"

    cli_template = app_exports[export_name]
    command = cli_template.format(**kwargs)

    try:
        result = subprocess.run(
            ["uv", "run", "--project", f"apps/{app_name}"] + shlex.split(command),
            capture_output=True,
            text=True,
            cwd=f"./apps/{app_name}",
            timeout=30
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            error_msg = result.stderr.strip() or f"Command failed with exit code {result.returncode}"
            return f"Error: {error_msg}"

    except subprocess.TimeoutExpired:
        return f"Command timed out: {command}"
    except Exception as e:
        return f"Execution failed: {str(e)}"