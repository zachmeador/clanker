"""Input resolution for smart command routing."""

from typing import List, Dict, Any
from .apps import discover


class InputResolver:
    """Resolves user input to appropriate handler type."""

    def __init__(self):
        self.apps = discover()
        self.system_commands = {
            "launch", "app", "apps", "profile", "config",
            "models", "help", "version", "--help", "--version"
        }

    def resolve(self, input_tokens: List[str]) -> Dict[str, Any]:
        """Resolve input tokens to handler type and parameters.

        Returns:
            Dict with keys:
            - type: "app_command", "system_command", "flag_command", "natural_language", "help"
            - Additional keys depending on type
        """
        if not input_tokens:
            return {"type": "help"}

        first_token = input_tokens[0]

        # Check if it's a known app
        if first_token in self.apps:
            return {
                "type": "app_command",
                "app_name": first_token,
                "args": input_tokens[1:]
            }

        # Check for system commands
        if first_token in self.system_commands:
            return {
                "type": "system_command",
                "command": first_token,
                "args": input_tokens[1:]
            }

        # Check for flags
        if first_token.startswith("--"):
            return {
                "type": "flag_command",
                "flag": first_token,
                "args": input_tokens[1:]
            }

        # Default to natural language
        return {
            "type": "natural_language",
            "request": " ".join(input_tokens)
        }

    def get_available_apps(self) -> List[str]:
        """Get list of available app names."""
        return list(self.apps.keys())

    def get_app_info(self, app_name: str) -> Dict[str, Any] | None:
        """Get information about a specific app."""
        return self.apps.get(app_name)

    def is_app_command(self, tokens: List[str]) -> bool:
        """Check if tokens represent an app command."""
        if not tokens:
            return False
        return tokens[0] in self.apps

    def is_system_command(self, tokens: List[str]) -> bool:
        """Check if tokens represent a system command."""
        if not tokens:
            return False
        return tokens[0] in self.system_commands

    def is_flag_command(self, tokens: List[str]) -> bool:
        """Check if tokens represent a flag command."""
        if not tokens:
            return False
        return tokens[0].startswith("--")

    def suggest_commands(self, partial: str) -> List[str]:
        """Suggest possible commands based on partial input."""
        suggestions = []

        # Suggest apps
        for app_name in self.apps:
            if app_name.startswith(partial):
                suggestions.append(app_name)

        # Suggest system commands
        for cmd in self.system_commands:
            if cmd.startswith(partial):
                suggestions.append(cmd)

        return suggestions
