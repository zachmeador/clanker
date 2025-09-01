"""Tool for delegating to LLM development tools."""

import subprocess
import os
from pathlib import Path
from typing import Dict
from pydantic_ai import RunContext, Tool
from .registry import ToolProtocol
from ..apps import discover


class LLMDevTool(ToolProtocol):
    """Tool for launching LLM development tools with context."""

    name = "launch_dev_tool"
    description = "Launch LLM development tools like Claude Code, Cursor, etc."

    # Supported development tools
    SUPPORTED_TOOLS: Dict[str, str] = {
        "claude": "claude",
        "cursor": "cursor",
        "gemini": "gemini-cli",
        "aider": "aider",
        "cline": "cline"
    }

    def get_tool_definition(self) -> Tool:
        """Return pydantic-ai tool definition."""

        def launch_dev_tool(
            ctx: RunContext,
            tool_name: str,
            request: str,
            directory: str = "."
        ) -> str:
            """Launch a development tool with context.

            Args:
                tool_name: Name of the tool (claude, cursor, gemini, aider, cline)
                request: The development request or prompt
                directory: Working directory for the tool
            """
            try:
                # Validate tool name
                if tool_name not in self.SUPPORTED_TOOLS:
                    available = list(self.SUPPORTED_TOOLS.keys())
                    return f"Unknown tool '{tool_name}'. Available: {', '.join(available)}"

                # Validate directory
                work_dir = Path(directory).resolve()
                if not work_dir.exists():
                    return f"Directory '{directory}' does not exist"

                # Create context file
                context_file = work_dir / "CLAUDE.md"
                context_content = self._generate_context(request, work_dir)
                context_file.write_text(context_content)

                # Launch the tool
                command = self.SUPPORTED_TOOLS[tool_name]
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
                return f"Failed to launch {tool_name}: {str(e)}"

        return Tool(launch_dev_tool)

    def _generate_context(self, request: str, work_dir: Path) -> str:
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
