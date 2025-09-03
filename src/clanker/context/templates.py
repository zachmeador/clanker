"""High-level context templates for common scenarios."""

from pathlib import Path
from typing import Optional

from .builder import ContextBuilder
from ..apps import discover as discover_apps


def cli_session_context(
    tool: str = "generic", 
    app_name: Optional[str] = None,
    user_request: Optional[str] = None
) -> str:
    """Build context for CLI tool sessions (claude code, cursor, etc).
    
    Args:
        tool: CLI tool name (e.g., "claude", "cursor")
        app_name: Optional app being worked on
        user_request: Optional user request to include
        
    Returns:
        Complete markdown context document
    """
    builder = ContextBuilder()
    
    # Add core overview
    builder.add_snippet("clanker_overview")
    
    # Add available apps listing
    apps_context = get_available_apps_context()
    builder.add(apps_context, "Available Apps")
    
    # Add development patterns
    builder.add_snippet("cli_patterns")
    
    # Add app-specific context if specified
    if app_name:
        app_context = _get_app_specific_context(app_name)
        if app_context:
            builder.add(app_context, f"Working with {app_name}")
    
    # Add user request if provided
    if user_request:
        builder.add(user_request, "User Request")
    
    return builder.build()


def app_scaffold_context(app_name: str, description: str) -> str:
    """Build context for scaffolding a new app.
    
    Args:
        app_name: Name of the app to scaffold
        description: Description of what the app should do
        
    Returns:
        Complete scaffold guide as markdown
    """
    builder = ContextBuilder()
    
    # Add header
    builder.add(f"## Overview\n{description}", f"{app_name.title()} App")
    
    # Add structure guide
    builder.add_snippet("app_structure")
    
    # Add implementation steps
    implementation = f"""## Implementation Steps

### 1. Set up basic structure
```bash
mkdir apps/{app_name}
cd apps/{app_name}
uv init
uv add clanker typer pydantic
```

### 2. Create main.py with typer commands
```python
import typer

app = typer.Typer()

@app.command()
def hello(name: str = "world"):
    \"\"\"Say hello.\"\"\"
    print(f"Hello {{name}}!")

if __name__ == "__main__":
    app()
```

### 3. Add CLI exports to pyproject.toml
```toml
[tool.clanker.exports]
hello = "python main.py hello {{name}}"
```

### 4. Test your app
- Test locally: `uv run python main.py hello`
- Test via Clanker: `clanker {app_name}_hello name="test"`
"""
    builder.add(implementation)
    
    # Add storage guide
    builder.add_snippet("storage_guide")
    
    # Add export system details
    builder.add_snippet("export_system")
    
    # Add CLI patterns for reference
    builder.add_snippet("cli_patterns")
    
    return builder.build()


def get_available_apps_context() -> str:
    """Discover apps via clanker.apps.discover and format a context section."""
    discovered = discover_apps()
    if not discovered:
        return "No apps found in apps/ directory."

    lines = []
    for app_name, info in discovered.items():
        description = info.get("description") or f"{app_name} app"
        exports = info.get("exports") or []

        lines.append(f"## {app_name}")
        lines.append(f"- **Location**: `apps/{app_name}/`")
        lines.append(f"- **Description**: {description}")
        if exports:
            lines.append(f"- **CLI Exports**: {', '.join(exports)}")
            commands = [f"`clanker {app_name}_{export}`" for export in exports]
            lines.append(f"- **Commands**: {', '.join(commands)}")
        lines.append("")

    lines.append("## Development")
    lines.append("Create new apps in `apps/` directory with:")
    lines.append("- `main.py` with typer CLI")
    lines.append("- `pyproject.toml` with dependencies and exports")
    lines.append("- Isolated storage via Clanker storage system")

    return "\n".join(lines)


def _get_app_specific_context(app_name: str) -> Optional[str]:
    """Get context specific to a particular app using unified discovery."""
    discovered = discover_apps()
    if app_name not in discovered:
        return None

    info = discovered[app_name]
    exports = info.get("exports") or []

    lines = [
        f"## Location",
        f"`apps/{app_name}/`",
        "",
        "## Structure",
        "- `main.py`: CLI entry point with typer commands",
        "- `pyproject.toml`: Dependencies and CLI export configuration",
        f"- `{app_name}/` package directory (if exists)",
        "",
    ]

    if exports:
        lines.append("## CLI Exports")
        lines.append("Available as AI tools in Clanker console:")
        for cmd_name in exports:
            lines.append(f"- `{app_name}_{cmd_name}(args)`")
        lines.append("")

    lines.extend([
        "## Storage",
        f"- File storage: `data/default/vault/{app_name}/`",
        "- Database: Scoped access to shared SQLite",
        "- Cross-app access requires explicit permission grants",
        "",
        "## Development",
        f"- Test locally: `cd apps/{app_name} && uv run python main.py`",
        f"- Test via Clanker: `clanker {app_name}_command_name args`",
        "- Storage access requires proper vault/db initialization",
    ])

    return "\n".join(lines)