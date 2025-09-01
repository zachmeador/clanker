"""Export-based toolsets for clanker using Pydantic AI toolsets."""

import subprocess
import shlex
import os
from pathlib import Path
from typing import List, Dict, Optional, Callable
from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset

from ..logger import get_logger
from ..exports import get_app_exports, list_exported_apps, discover_and_import_apps, ExportMetadata

logger = get_logger("toolsets")


def bash(
    ctx: RunContext,
    command: str,
    working_directory: str = "."
) -> str:
    """Execute a safe bash command (read-only operations only)."""
    try:
        # Parse and validate command
        parsed_command = shlex.split(command.strip())
        if not parsed_command:
            return "Empty command provided"

        base_command = parsed_command[0]

        # Check if command is allowed
        if not _is_allowed_command(base_command):
            return f"Command '{base_command}' not allowed. Only read-only operations permitted."

        # Additional security checks
        if _has_dangerous_patterns(command):
            return "Command contains potentially dangerous patterns"

        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=working_directory
        )

        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            if output:
                output += "\n--- STDERR ---\n"
            output += result.stderr

        if result.returncode != 0 and not output:
            output = f"Command failed with exit code {result.returncode}"

        return output.strip() or "Command completed successfully"

    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds"
    except Exception as e:
        return f"Command execution failed: {str(e)}"


def launch_dev_tool(
    ctx: RunContext,
    tool_name: str,
    request: str,
    directory: str = "."
) -> str:
    """Launch a development tool with context."""
    try:
        # Validate tool name
        supported_tools = _get_supported_tools()
        if tool_name not in supported_tools:
            available = list(supported_tools.keys())
            return f"Unknown tool '{tool_name}'. Available: {', '.join(available)}"

        # Validate directory
        work_dir = Path(directory).resolve()
        if not work_dir.exists():
            return f"Directory '{directory}' does not exist"

        # Create context file
        context_file = work_dir / "CLAUDE.md"
        context_content = _generate_context(request, work_dir)
        context_file.write_text(context_content)

        # Launch the tool
        command = supported_tools[tool_name]
        full_command = f"cd {work_dir} && {command}"

        # Launch in background
        process = subprocess.Popen(
            full_command,
            shell=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        return f"Launched {tool_name} in {work_dir} with request: {request[:100]}..."

    except Exception as e:
        logger.error(f"Failed to launch {tool_name}: {e}", exc_info=True)
        return f"Failed to launch {tool_name}: {str(e)}"


def create_export_based_toolset():
    """
    Create toolset from exported functions.

    This replaces the old dynamic discovery approach with a cleaner
    export-based system where apps declare their functions explicitly.
    """
    tools = []  # Core tools - bash disabled for now

    # Discover and import all apps to trigger export registration
    discover_and_import_apps()

    # Get all exported apps
    exported_apps = list_exported_apps()

    for app_name in exported_apps:
        app_exports = get_app_exports(app_name)
        if not app_exports:
            continue

        # Get tool-exported functions
        tool_functions = app_exports.get_tool_functions()

        for func_name, metadata in tool_functions.items():
            # Create a tool wrapper for the exported function
            def create_tool_wrapper(original_func: Callable, meta: ExportMetadata):
                """Create a tool wrapper that handles parameter conversion."""
                def tool_wrapper(ctx: RunContext, **kwargs):
                    """Dynamically created tool from exported function."""
                    try:
                        # Convert string kwargs to appropriate types if needed
                        processed_args = {}
                        for param_name, param_value in kwargs.items():
                            # Basic type conversion - could be enhanced
                            if param_name in meta.parameters:
                                param_info = meta.parameters[param_name]
                                if param_info['type'] == 'Optional[str]' and param_value == '':
                                    processed_args[param_name] = None
                                else:
                                    processed_args[param_name] = param_value

                        # Call the original function
                        result = original_func(**processed_args)

                        # Format result for agent consumption
                        if isinstance(result, str):
                            return result
                        elif isinstance(result, dict):
                            return str(result)
                        else:
                            return str(result)

                    except Exception as e:
                        logger.error(f"Error calling {meta.name}: {e}", exc_info=True)
                        return f"Error executing {meta.name}: {str(e)}"

                # Set metadata for the tool
                tool_wrapper.__name__ = f"{app_name}_{meta.name}"
                tool_wrapper.__doc__ = meta.description

                return tool_wrapper

            # Create and add the tool
            tool_func = create_tool_wrapper(metadata.original_function, metadata)
            tools.append(tool_func)
            logger.debug(f"Added tool: {app_name}_{metadata.name}")

    return FunctionToolset(tools=tools)


def create_dynamic_app_toolset():
    """
    Legacy function for backwards compatibility.
    Now uses the export-based system instead of dynamic discovery.
    """
    logger.warning("create_dynamic_app_toolset is deprecated, use create_export_based_toolset instead")
    return create_export_based_toolset()


def create_clanker_toolset():
    """Create the main clanker toolset with all core tools."""
    return create_export_based_toolset()


def create_app_tools():
    """Create toolset for specific app tools (can be extended dynamically)."""
    return create_export_based_toolset()


def create_dev_tools():
    """Create toolset for development-specific tools."""
    return FunctionToolset(tools=[launch_dev_tool])


def create_cli_runner_from_exports(app_name: str, command_name: str, **kwargs):
    """
    Execute an exported function as a CLI command.

    This replaces the old app running mechanism with direct function calls.
    """
    try:
        app_exports = get_app_exports(app_name)
        if not app_exports:
            return f"App '{app_name}' not found or has no exports"

        cli_commands = app_exports.get_cli_commands()

        if command_name not in cli_commands:
            available = list(cli_commands.keys())
            return f"Command '{command_name}' not found. Available: {', '.join(available)}"

        metadata = cli_commands[command_name]
        func = metadata.original_function

        # Call the function with provided arguments
        result = func(**kwargs)

        return result

    except Exception as e:
        logger.error(f"Error running {app_name} {command_name}: {e}", exc_info=True)
        return f"Error: {str(e)}"


def list_available_exports():
    """Get information about all available exported functions."""
    # Ensure all apps are discovered and imported
    discover_and_import_apps()

    info = {}

    exported_apps = list_exported_apps()
    for app_name in exported_apps:
        app_exports = get_app_exports(app_name)
        if app_exports:
            info[app_name] = {
                'cli_commands': list(app_exports.get_cli_commands().keys()),
                'tool_functions': list(app_exports.get_tool_functions().keys())
            }

    return info


# Helper functions

def _is_allowed_command(command: str) -> bool:
    """Check if a command is in the allowed list."""
    ALLOWED_COMMANDS = {
        'ls', 'cat', 'head', 'tail', 'grep', 'find', 'pwd', 'echo',
        'wc', 'sort', 'uniq', 'cut', 'awk', 'sed', 'which', 'type',
        'file', 'stat', 'readlink', 'dirname', 'basename'
    }
    return command in ALLOWED_COMMANDS


def _has_dangerous_patterns(command: str) -> bool:
    """Check for dangerous patterns in command."""
    dangerous_patterns = [
        'rm ', 'mv ', 'cp ', 'mkdir ', 'touch ', 'chmod ', 'chown ',
        'sudo ', 'su ', 'passwd', 'kill ', 'pkill ', 'killall ',
        'shutdown', 'reboot', 'halt', 'poweroff',
        '> ', '>> ', '| ', '&& ', '|| ', '; ',
        'curl ', 'wget ', 'ssh ', 'scp ', 'ftp ',
        'python ', 'pip ', 'npm ', 'yarn ', 'git ',
        'docker ', 'kubectl ', 'terraform ', 'ansible '
    ]

    command_lower = command.lower()
    for pattern in dangerous_patterns:
        if pattern in command_lower:
            return True

    return False


def _get_supported_tools() -> Dict[str, str]:
    """Get supported development tools."""
    return {
        "claude": "claude",
        "cursor": "cursor",
        "gemini": "gemini-cli",
        "aider": "aider",
        "cline": "cline"
    }


def _generate_context(request: str, work_dir: Path) -> str:
    """Generate context content for the development tool."""
    context_parts = [
        "# Clanker Development Request",
        "",
        f"**Request**: {request}",
        "",
        "## Available Clanker Apps",
    ]

    # Add available apps
    try:
        from ..exports import list_exported_apps, get_app_exports
        exported_apps = list_exported_apps()
        if exported_apps:
            for name in exported_apps:
                app_exports = get_app_exports(name)
                if app_exports:
                    cli_cmds = list(app_exports.get_cli_commands().keys())
                    tool_funcs = list(app_exports.get_tool_functions().keys())
                    context_parts.append(f"- **{name}**:")
                    if cli_cmds:
                        context_parts.append(f"  - CLI: {', '.join(cli_cmds)}")
                    if tool_funcs:
                        context_parts.append(f"  - Tools: {', '.join(tool_funcs)}")
        else:
            context_parts.append("- No apps discovered")
    except:
        context_parts.append("- App discovery unavailable")

    context_parts.extend([
        "",
        "## Project Structure",
        f"**Working Directory**: {work_dir}",
        "",
        "## Available AI Providers"
    ])

    # Add available providers
    try:
        from ..models import list_available_providers
        providers = list_available_providers()
        if providers:
            context_parts.append(f"Configured: {', '.join(providers)}")
        else:
            context_parts.append("None configured")
    except:
        context_parts.append("Provider info unavailable")

    context_parts.extend([
        "",
        "## Instructions",
        "Use the available clanker apps and project context to fulfill the request.",
        "The CLAUDE.md file will be automatically updated with new context as needed."
    ])

    return "\n".join(context_parts)
