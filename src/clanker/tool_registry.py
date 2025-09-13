"""Simplified tool registry system for Clanker.

This module provides a clean abstraction for managing tool metadata,
registration, and execution for both core Clanker tools and app exports.
"""

import inspect
import json
import os
import shlex
import subprocess
import tomllib
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable

from .logger import get_logger

logger = get_logger("tool_registry")


@dataclass
class ToolParameter:
    """Metadata for a tool parameter."""
    name: str
    type: str = "str"
    required: bool = True
    default: Any = None
    description: Optional[str] = None


@dataclass
class ToolMetadata:
    """Complete metadata for a tool."""
    name: str
    description: str
    category: str = "general"
    parameters: Dict[str, ToolParameter] = field(default_factory=dict)
    needs_confirmation: bool = False
    hidden: bool = False

    @property
    def display_name(self) -> str:
        """Human-friendly display name."""
        return self.name.replace("_", " ").title()


@dataclass
class AppManifest:
    """Manifest for an app including all metadata."""
    name: str
    path: Path
    summary: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    exports: Dict[str, str] = field(default_factory=dict)  # name -> cli_template
    daemons: Dict[str, str] = field(default_factory=dict)  # id -> command
    tool_metadata: Dict[str, ToolMetadata] = field(default_factory=dict)

    @classmethod
    def from_pyproject(cls, app_path: Path) -> Optional["AppManifest"]:
        """Load app manifest from pyproject.toml."""
        pyproject_path = app_path / "pyproject.toml"
        if not pyproject_path.exists():
            return None

        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)

            clanker_config = data.get("tool", {}).get("clanker", {})
            if not clanker_config:
                return None

            app_config = clanker_config.get("app", {})
            exports_raw = clanker_config.get("exports", {})
            daemons = clanker_config.get("daemons", {})

            # Process exports - dict format only
            exports = {}
            tool_metadata = {}

            for export_name, export_config in exports_raw.items():
                if isinstance(export_config, str):
                    raise ValueError(f"Export '{export_name}' uses deprecated string format. Use dict format: {{cmd = \"...\", desc = \"...\"}}")

                # Dict format: {cmd = "...", desc = "...", confirm = true}
                cli_template = export_config.get("cmd", f"python main.py {export_name}")
                description = export_config.get("desc", f"Run {export_name}")
                needs_confirmation = export_config.get("confirm", False)

                exports[export_name] = cli_template

                # Create simple metadata
                metadata = ToolMetadata(
                    name=export_name,
                    description=description,
                    category="app",
                    needs_confirmation=needs_confirmation
                )
                tool_metadata[export_name] = metadata

            return cls(
                name=app_path.name,
                path=app_path,
                summary=app_config.get("summary"),
                capabilities=app_config.get("capabilities", []),
                examples=app_config.get("examples", []),
                exports=exports,
                daemons=daemons,
                tool_metadata=tool_metadata
            )

        except Exception as e:
            logger.warning(f"Failed to load manifest from {app_path}: {e}")
            return None


class ToolRegistry:
    """Central registry for all Clanker tools."""

    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._app_manifests: Dict[str, AppManifest] = {}

    def register(self, func: Callable, metadata: ToolMetadata) -> None:
        """Register a tool with its metadata."""
        tool_name = func.__name__
        self._tools[tool_name] = func
        self._metadata[tool_name] = metadata
        logger.debug(f"Registered tool: {tool_name}")

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool function by name."""
        return self._tools.get(name)

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """Get metadata for a tool."""
        return self._metadata.get(name)

    def list_tools(self, category: Optional[str] = None, include_hidden: bool = False) -> List[str]:
        """List all registered tools, optionally filtered by category."""
        tools = []
        for name, metadata in self._metadata.items():
            if metadata.hidden and not include_hidden:
                continue
            if category and metadata.category != category:
                continue
            tools.append(name)
        return sorted(tools)

    def get_display_info(self, name: str) -> Dict[str, str]:
        """Get display information for a tool."""
        metadata = self._metadata.get(name)
        if metadata:
            return {
                "name": metadata.display_name,
                "description": metadata.description,
                "category": metadata.category
            }
        return {
            "name": name.replace("_", " ").title(),
            "description": f"Run {name}",
            "category": "unknown"
        }

    def discover_apps(self, apps_dir: Path = Path("./apps")) -> None:
        """Discover and register all app tools."""
        if not apps_dir.exists():
            return

        for app_path in apps_dir.iterdir():
            if not app_path.is_dir() or app_path.name.startswith(("_", ".")):
                continue

            manifest = AppManifest.from_pyproject(app_path)
            if manifest and manifest.exports:
                self._app_manifests[manifest.name] = manifest

                # Register each export as a tool
                for export_name, cli_template in manifest.exports.items():
                    tool_name = f"{manifest.name}_{export_name}"
                    metadata = manifest.tool_metadata.get(export_name)

                    if not metadata:
                        # Create default metadata
                        metadata = ToolMetadata(
                            name=tool_name,
                            description=f"Run {manifest.name} {export_name}",
                            category="app"
                        )
                    else:
                        # Update name to include app prefix
                        metadata.name = tool_name

                    # Create wrapper for app tool
                    wrapper = AppToolWrapper(
                        app_name=manifest.name,
                        export_name=export_name,
                        cli_template=cli_template,
                        metadata=metadata
                    )

                    self.register(wrapper, metadata)

    def get_app_manifest(self, app_name: str) -> Optional[AppManifest]:
        """Get manifest for an app."""
        return self._app_manifests.get(app_name)

    def list_apps(self) -> List[str]:
        """List all discovered apps."""
        return sorted(self._app_manifests.keys())


class AppToolWrapper:
    """Wrapper for app CLI tools to provide a consistent interface."""

    def __init__(self, app_name: str, export_name: str, cli_template: str, metadata: ToolMetadata):
        self.app_name = app_name
        self.export_name = export_name
        self.cli_template = cli_template
        self.metadata = metadata
        self.__name__ = f"{app_name}_{export_name}"
        self.__qualname__ = f"{app_name}_{export_name}"
        self.__doc__ = metadata.description
        self.__module__ = "clanker.app_tools"

    def __call__(self, **kwargs) -> str:
        """Execute the app tool with provided parameters."""
        try:
            # Parse placeholders from template
            import re
            placeholders = re.findall(r"\{(\w+)\}", self.cli_template)

            # Build format arguments - let pydantic-ai handle type conversion
            format_args = {}
            for placeholder in placeholders:
                value = kwargs.get(placeholder, "")
                if isinstance(value, (list, dict)):
                    value = json.dumps(value)
                else:
                    value = str(value)
                # Quote strings that might contain spaces or special characters
                if isinstance(value, str) and (' ' in value or '#' in value or any(c in value for c in '"\'()[]{}|;&$`<>')):
                    value = shlex.quote(value)
                format_args[placeholder] = value

            # Format command
            command = self.cli_template.format(**format_args)

            # Clean environment
            env = os.environ.copy()
            env.pop("VIRTUAL_ENV", None)

            # Execute via uv run
            result = subprocess.run(
                ["uv", "run", "--project", f"apps/{self.app_name}"] + shlex.split(command),
                capture_output=True,
                text=True,
                cwd=f"./apps/{self.app_name}",
                timeout=60,
                env=env
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                error_msg = result.stderr.strip() or f"Command failed with exit code {result.returncode}"
                return f"Error: {error_msg}"

        except subprocess.TimeoutExpired:
            return f"Command timed out: {self.cli_template}"
        except Exception as e:
            logger.error(f"Tool execution failed for {self.app_name}.{self.export_name}: {e}")
            return f"Tool execution failed: {str(e)}"


def tool(name: str, description: str, category: str = "general", **kwargs):
    """Decorator for registering core Clanker tools with metadata."""
    def decorator(func: Callable) -> Callable:
        # Extract parameters from function signature
        sig = inspect.signature(func)
        parameters = {}

        for param_name, param in sig.parameters.items():
            if param_name in ["self", "cls"]:
                continue

            # Determine type from annotation
            type_str = "str"
            if param.annotation != inspect.Parameter.empty:
                type_hint = param.annotation
                if type_hint == str:
                    type_str = "str"
                elif type_hint == int:
                    type_str = "int"
                elif type_hint == float:
                    type_str = "float"
                elif type_hint == bool:
                    type_str = "bool"

            parameters[param_name] = ToolParameter(
                name=param_name,
                type=type_str,
                required=param.default == inspect.Parameter.empty,
                default=param.default if param.default != inspect.Parameter.empty else None
            )

        # Create metadata
        metadata = ToolMetadata(
            name=name,
            description=description,
            category=category,
            parameters=parameters,
            **kwargs
        )

        # Store metadata on function for registration
        func.__tool_metadata__ = metadata

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
    return decorator


# Global registry instance
_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _registry