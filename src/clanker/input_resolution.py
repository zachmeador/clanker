"""Input resolution for smart command routing."""

from typing import List, Dict, Any
from .apps import discover


class InputResolver:
    """Resolves user input to appropriate handler type."""

    def __init__(self):
        self.apps = discover()
        # Only two reserved keywords now
        self.system_commands = {"system", "app"}

    def resolve(self, input_tokens: List[str]) -> Dict[str, Any]:
        """Resolve input tokens to handler type and parameters.

        Returns:
            Dict with keys:
            - type: "system_command", "app_command", "natural_language", "help"
            - Additional keys depending on type
        """
        if not input_tokens:
            return {"type": "help"}

        first_token = input_tokens[0]

        # Check for system or app commands (only two reserved keywords)
        if first_token in self.system_commands:
            return {
                "type": "system_command",
                "command": first_token,
                "args": input_tokens[1:]
            }

        # Everything else is natural language
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
