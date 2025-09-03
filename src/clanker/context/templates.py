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
    
    # Add development patterns and export system details
    builder.add_snippet("cli_patterns")
    builder.add_snippet("export_system")
    
    # Add app-specific context if specified
    if app_name:
        app_context = _get_app_specific_context(app_name)
        if app_context:
            builder.add(app_context, f"Working with {app_name}")
    
    # Add user request if provided
    if user_request:
        builder.add(user_request, "User Request")
    
    return builder.build()


def coding_session_context(tool_name: str, user_request: str) -> str:
    """Build context for coding CLI sessions launched from Clanker.
    
    Combines agent-like context with INSTRUCTIONS.md and session info.
    Supports various tools like Claude Code, Cursor, Windsurf, etc.
    
    Args:
        tool_name: Name of the coding tool (e.g., "claude", "cursor", "windsurf")
        user_request: The user's request/intent for the session
        
    Returns:
        Complete context document for the coding session
    """
    builder = ContextBuilder()
    
    # Add session header
    tool_display = tool_name.title() if tool_name else "Coding"
    session_header = f"""# Clanker {tool_display} Session

This {tool_display} session was launched from Clanker. You have full context about the Clanker system 
and should help with development tasks within this environment.

---
"""
    builder.add(session_header.strip())
    
    # Load and add INSTRUCTIONS.md content
    try:
        project_root = Path(__file__).resolve().parent.parent.parent
        instructions_path = project_root / "INSTRUCTIONS.md"
        if instructions_path.exists():
            instructions = instructions_path.read_text()
            # Remove the first # header since we have our own
            if instructions.startswith("# "):
                instructions = instructions[instructions.find("\n") + 1:]
            builder.add(instructions.strip())
    except Exception:
        pass  # Gracefully continue without INSTRUCTIONS.md
    
    # Add a separator before dynamic content
    builder.add("---\n## Current System State")
    
    # Add the same base context as the agent
    builder.add_snippet("clanker_overview")
    
    # Add dynamically discovered apps
    apps_context = get_available_apps_context()
    builder.add(apps_context, "Available Apps")
    
    # Add CLI patterns and export system
    builder.add_snippet("cli_patterns") 
    builder.add_snippet("export_system")
    
    # Add user request
    if user_request:
        builder.add(f"**User Request**: {user_request}", "Session Intent")
    
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