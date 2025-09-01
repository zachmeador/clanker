"""Tool registry system for clanker."""

from typing import Dict, List, Protocol
from pydantic_ai import Tool


class ToolProtocol(Protocol):
    """Protocol for clanker tools."""

    name: str
    description: str

    def get_tool_definition(self) -> Tool:
        """Return pydantic-ai tool definition."""
        ...


class ToolRegistry:
    """Registry for managing available tools."""

    def __init__(self):
        self.tools: Dict[str, ToolProtocol] = {}

    def register(self, tool: ToolProtocol) -> None:
        """Register a tool with the registry."""
        self.tools[tool.name] = tool

    def unregister(self, tool_name: str) -> None:
        """Unregister a tool from the registry."""
        self.tools.pop(tool_name, None)

    def get_available_tools(self) -> List[Tool]:
        """Get all registered tools as pydantic-ai Tool objects."""
        return [tool.get_tool_definition() for tool in self.tools.values()]

    def get_tool(self, name: str) -> ToolProtocol | None:
        """Get a specific tool by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[str]:
        """List names of all registered tools."""
        return list(self.tools.keys())

    def get_tool_info(self) -> Dict[str, str]:
        """Get info about all registered tools."""
        return {name: tool.description for name, tool in self.tools.items()}
