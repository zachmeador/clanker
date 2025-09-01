"""Tool for executing safe bash commands."""

import subprocess
import shlex
from typing import List
from pydantic_ai import RunContext, Tool
from .registry import ToolProtocol


class BashTool(ToolProtocol):
    """Tool for executing safe bash commands with read-only restrictions."""

    name = "bash"
    description = "Execute safe read-only bash commands"

    # Allowed commands for security
    ALLOWED_COMMANDS = {
        'ls', 'cat', 'head', 'tail', 'grep', 'find', 'pwd', 'echo',
        'wc', 'sort', 'uniq', 'cut', 'awk', 'sed', 'which', 'type',
        'file', 'stat', 'readlink', 'dirname', 'basename'
    }

    def get_tool_definition(self) -> Tool:
        """Return pydantic-ai tool definition."""

        def bash(
            ctx: RunContext,
            command: str,
            working_directory: str = "."
        ) -> str:
            """Execute a safe bash command.

            Only read-only operations are allowed for security.

            Args:
                command: The bash command to execute
                working_directory: Directory to run the command in
            """
            try:
                # Parse and validate command
                parsed_command = shlex.split(command.strip())
                if not parsed_command:
                    return "Empty command provided"

                base_command = parsed_command[0]

                # Check if command is allowed
                if base_command not in self.ALLOWED_COMMANDS:
                    return f"Command '{base_command}' not allowed. Only read-only operations permitted."

                # Additional security checks
                if self._has_dangerous_patterns(command):
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

        return Tool(bash)

    def _has_dangerous_patterns(self, command: str) -> bool:
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
