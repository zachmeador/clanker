"""Export mechanism for Clanker apps to expose functions as CLI commands and agent tools."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from functools import wraps
import inspect


class ExportType(Enum):
    """Types of exports available for app functions."""
    CLI = "cli"         # Available as CLI command
    TOOL = "tool"       # Available as agent tool
    BOTH = "both"       # Available as both CLI and tool


@dataclass
class ExportMetadata:
    """Metadata for an exported function."""
    name: str
    description: str
    export_type: ExportType
    cli_path: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    original_function: Optional[Callable] = None


class AppExports:
    """Registry for app exports."""

    def __init__(self, app_name: str):
        self.app_name = app_name
        self.exports: Dict[str, ExportMetadata] = {}
        self._cli_commands: Dict[str, ExportMetadata] = {}
        self._tool_functions: Dict[str, ExportMetadata] = {}

    def register(self, metadata: ExportMetadata):
        """Register an exported function."""
        self.exports[metadata.name] = metadata

        if metadata.export_type in [ExportType.CLI, ExportType.BOTH]:
            cli_path = metadata.cli_path or metadata.name
            self._cli_commands[cli_path] = metadata

        if metadata.export_type in [ExportType.TOOL, ExportType.BOTH]:
            self._tool_functions[metadata.name] = metadata

    def get_cli_commands(self) -> Dict[str, ExportMetadata]:
        """Get all CLI-exported functions."""
        return self._cli_commands.copy()

    def get_tool_functions(self) -> Dict[str, ExportMetadata]:
        """Get all tool-exported functions."""
        return self._tool_functions.copy()

    def get_all_exports(self) -> Dict[str, ExportMetadata]:
        """Get all exported functions."""
        return self.exports.copy()


# Global registry of app exports
_app_exports_registry: Dict[str, AppExports] = {}


def export(
    name: Optional[str] = None,
    description: str = "",
    export_type: ExportType = ExportType.BOTH,
    cli_path: Optional[str] = None
):
    """
    Decorator to export a function for use by Clanker.

    Args:
        name: Name for the export (defaults to function name)
        description: Description of what the function does
        export_type: Whether to export as CLI, tool, or both
        cli_path: Custom CLI path (defaults to function name)
    """
    def decorator(func: Callable) -> Callable:
        export_name = name or func.__name__

        # Extract parameter information
        sig = inspect.signature(func)
        params = {}
        for param_name, param in sig.parameters.items():
            if param_name != 'self':  # Skip self for methods
                params[param_name] = {
                    'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                    'default': param.default if param.default != inspect.Parameter.empty else None,
                    'required': param.default == inspect.Parameter.empty
                }

        # Create metadata
        metadata = ExportMetadata(
            name=export_name,
            description=description or (func.__doc__ or f"Execute {export_name}"),
            export_type=export_type,
            cli_path=cli_path,
            parameters=params,
            original_function=func
        )

        # Store in function for later retrieval
        func._clanker_export = metadata

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


def register_app_exports(app_name: str, app_module: Any) -> AppExports:
    """
    Scan a module for exported functions and register them.

    Args:
        app_name: Name of the app
        app_module: The app's main module

    Returns:
        AppExports instance with registered functions
    """
    app_exports = AppExports(app_name)

    # Scan the module for exported functions
    for attr_name in dir(app_module):
        if not attr_name.startswith('_'):
            attr = getattr(app_module, attr_name)
            if hasattr(attr, '_clanker_export'):
                metadata = attr._clanker_export
                # Update the original function reference
                metadata.original_function = attr
                app_exports.register(metadata)

    # Register globally
    _app_exports_registry[app_name] = app_exports
    return app_exports


def get_app_exports(app_name: str) -> Optional[AppExports]:
    """Get exports for a specific app."""
    return _app_exports_registry.get(app_name)


def discover_and_import_apps():
    """
    Discover apps from the filesystem and import their modules to register exports.

    This is the key function that bridges the filesystem discovery with the export system.
    It finds apps in ./apps/ relative to the project root.
    """
    from pathlib import Path
    import importlib.util
    import sys
    import os

    # Find apps directory relative to the clanker package location
    # Go up from src/clanker/exports.py to the project root
    current_file = Path(__file__)
    clanker_dir = current_file.parent  # src/clanker/
    src_dir = clanker_dir.parent      # src/
    project_root = src_dir.parent     # project root/
    apps_dir = project_root / "apps"

    if not apps_dir.exists():
        return

    for item in apps_dir.iterdir():
        if not item.is_dir() or item.name.startswith(('_', '.')):
            continue

        # Check if it's a Python app
        pyproject_path = item / "pyproject.toml"
        if not pyproject_path.exists():
            continue

        app_name = item.name

        # Check if we already have exports for this app
        if app_name in _app_exports_registry:
            continue

        # Try to import the app module to trigger export registration
        try:
            # Look for the main app module (e.g., apps/example/example/__init__.py)
            app_module_path = item / app_name / "__init__.py"

            if app_module_path.exists():
                # Import the app module
                spec = importlib.util.spec_from_file_location(
                    f"apps.{app_name}.{app_name}",
                    app_module_path
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[f"apps.{app_name}.{app_name}"] = module
                    spec.loader.exec_module(module)

        except Exception as e:
            # If import fails, try to extract exports manually from the source
            _extract_exports_from_source(app_name, app_module_path)


def _extract_exports_from_source(app_name: str, init_file_path):
    """
    Extract exports from source files without full module import.

    This is a fallback for when the app module can't be imported due to missing dependencies.
    """
    from pathlib import Path

    try:
        exports_file = init_file_path.parent / "exports.py"
        if not exports_file.exists():
            return

        # Read the exports.py file
        with open(exports_file, 'r') as f:
            content = f.read()

        # Simple parsing to find @export decorators
        # This is a basic implementation - could be made more robust
        lines = content.split('\n')
        app_exports = AppExports(app_name)

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for @export decorator
            if line.startswith('@export('):
                # Parse the export decorator
                export_args = {}
                # Simple parsing - look for key arguments with single or double quotes
                if 'name=' in line:
                    for quote in ['"', "'"]:
                        name_start = line.find(f'name={quote}') + 6
                        if name_start > 5:  # Found it
                            name_end = line.find(quote, name_start)
                            if name_end > name_start:
                                export_args['name'] = line[name_start:name_end]
                                break

                if 'description=' in line:
                    for quote in ['"', "'"]:
                        desc_start = line.find(f'description={quote}') + 14
                        if desc_start > 13:  # Found it
                            desc_end = line.find(quote, desc_start)
                            if desc_end > desc_start:
                                export_args['description'] = line[desc_start:desc_end]
                                break

                # Parse cli_path for CLI commands
                if 'cli_path=' in line:
                    for quote in ['"', "'"]:
                        cli_start = line.find(f'cli_path={quote}') + 10
                        if cli_start > 9:  # Found it
                            cli_end = line.find(quote, cli_start)
                            if cli_end > cli_start:
                                export_args['cli_path'] = line[cli_start:cli_end]
                                break

                # Parse export_type to determine if it's CLI or BOTH
                if 'export_type=ExportType.BOTH' in line or 'export_type=ExportType.CLI' in line:
                    export_args['is_cli'] = True

                # Find the function definition
                function_found = False
                while i < len(lines) and not function_found:
                    i += 1
                    func_line = lines[i].strip()
                    if func_line.startswith('def '):
                        func_name = func_line[4:func_line.find('(')]
                        function_found = True

                        # Determine export type
                        if export_args.get('is_cli'):
                            export_type = ExportType.BOTH
                            cli_path = export_args.get('cli_path', func_name)
                        else:
                            export_type = ExportType.TOOL
                            cli_path = None

                        # Create a basic export metadata
                        metadata = ExportMetadata(
                            name=export_args.get('name', func_name),
                            description=export_args.get('description', f"Execute {func_name}"),
                            export_type=export_type,
                            cli_path=cli_path,
                            parameters={}  # Could parse function signature
                        )
                        app_exports.register(metadata)

            i += 1

        # Register the app exports
        if app_exports.exports:
            _app_exports_registry[app_name] = app_exports

    except Exception as e:
        # If manual extraction fails, that's okay - app just won't have exports
        pass


def list_exported_apps() -> List[str]:
    """List all apps that have registered exports."""
    # First ensure we've discovered all available apps
    discover_and_import_apps()
    return list(_app_exports_registry.keys())


def get_all_exports() -> Dict[str, AppExports]:
    """Get all registered app exports."""
    # First ensure we've discovered all available apps
    discover_and_import_apps()
    return _app_exports_registry.copy()
