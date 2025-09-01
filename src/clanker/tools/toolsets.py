"""Simplified toolsets for clanker using Pydantic AI toolsets."""

import subprocess
import shlex
import os
from pathlib import Path
from typing import List, Dict, Optional
from pydantic_ai import RunContext
from pydantic_ai.toolsets import FunctionToolset

from ..logger import get_logger
from ..apps import discover

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


def create_dynamic_app_toolset():
    """Dynamically create specific tools for each discovered app."""
    from ..apps import discover, run

    tools = []
    apps = discover()

    for app_name, app_info in apps.items():
        desc = app_info.get("description", f"Run the {app_name} app")
        commands = app_info.get("commands", [])

        # Create tool function with proper closure
        def app_tool(ctx: RunContext, args: str = "", app_name=app_name) -> str:
            """Dynamically created tool for running a specific app."""
            try:
                arg_list = args.split() if args.strip() else []
                returncode = run(app_name, arg_list)

                if returncode == 0:
                    return f"Successfully ran {app_name} app"
                else:
                    return f"{app_name} app completed with exit code {returncode}"

            except Exception as e:
                logger.error(f"Failed to run {app_name}: {e}", exc_info=True)
                return f"Failed to run {app_name} app: {str(e)}"

        # Set metadata for the tool
        app_tool.__name__ = f"run_{app_name}"
        tool_desc = app_info.get("description", f"Run the {app_name} app")
        cmd_str = f" Commands: {', '.join(commands)}" if commands else ""
        app_tool.__doc__ = f"{tool_desc}.{cmd_str}"

        tools.append(app_tool)

    return FunctionToolset(tools=tools)


def create_clanker_toolset():
    """Create the main clanker toolset with all core tools."""
    # Core tools (always available)
    # core_tools = [bash, launch_dev_tool]
    # TODO: User doesn't trust these tools yet.
    core_tools = []

    # Create dynamic app tools
    dynamic_app_toolset = create_dynamic_app_toolset()

    # Combine tools from both toolsets
    all_tools = core_tools + list(dynamic_app_toolset.tools.values())

    return FunctionToolset(tools=all_tools)


def create_app_tools():
    """Create toolset for specific app tools (can be extended dynamically)."""
    # For now, just return the core toolset
    # This can be extended to create specific tools for each app
    return create_clanker_toolset()


def create_dev_tools():
    """Create toolset for development-specific tools."""
    return FunctionToolset(tools=[launch_dev_tool])


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
    apps = discover()
    if apps:
        for name, info in apps.items():
            desc = info.get("description", "")
            commands = info.get("commands", [])
            context_parts.append(f"- **{name}**: {desc}")
            if commands:
                context_parts.append(f"  - Commands: {', '.join(commands)}")
    else:
        context_parts.append("- No apps discovered")

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
