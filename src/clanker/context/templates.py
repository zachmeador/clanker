"""High-level context templates for common scenarios."""

from pathlib import Path
from typing import Optional
import tomlkit

from .builder import ContextBuilder
from .store import ContextStore


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
    apps_context = _get_available_apps_context()
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
    print(f"Hello {name}!")

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


def _get_available_apps_context() -> str:
    """Dynamically discover and format available apps."""
    apps_dir = Path("apps")
    if not apps_dir.exists():
        return "No apps directory found."
    
    apps = []
    for app_path in apps_dir.iterdir():
        if not app_path.is_dir():
            continue
        
        app_name = app_path.name
        pyproject_path = app_path / "pyproject.toml"
        
        if pyproject_path.exists():
            try:
                with open(pyproject_path, 'r') as f:
                    data = tomlkit.parse(f.read())
                
                exports = []
                if 'tool' in data and 'clanker' in data['tool'] and 'exports' in data['tool']['clanker']:
                    exports = list(data['tool']['clanker']['exports'].keys())
                
                description = data.get('project', {}).get('description', f'{app_name} app')
                
                apps.append({
                    'name': app_name,
                    'description': description,
                    'exports': exports
                })
            except Exception:
                continue
    
    if not apps:
        return "No apps found in apps/ directory."
    
    lines = []
    for app in apps:
        lines.append(f"## {app['name']}")
        lines.append(f"- **Location**: `apps/{app['name']}/`")
        lines.append(f"- **Description**: {app['description']}")
        if app['exports']:
            lines.append(f"- **CLI Exports**: {', '.join(app['exports'])}")
            commands = [f"`clanker {app['name']}_{export}`" for export in app['exports']]
            lines.append(f"- **Commands**: {', '.join(commands)}")
        lines.append("")
    
    lines.append("## Development")
    lines.append("Create new apps in `apps/` directory with:")
    lines.append("- `main.py` with typer CLI")
    lines.append("- `pyproject.toml` with dependencies and exports")
    lines.append("- Isolated storage via Clanker storage system")
    
    return "\n".join(lines)


def _get_app_specific_context(app_name: str) -> Optional[str]:
    """Get context specific to a particular app."""
    app_path = Path("apps") / app_name
    if not app_path.exists():
        return None
    
    lines = [
        f"## Location",
        f"`apps/{app_name}/`",
        "",
        "## Structure",
        "- `main.py`: CLI entry point with typer commands",
        "- `pyproject.toml`: Dependencies and CLI export configuration",
        f"- `{app_name}/` package directory (if exists)",
        ""
    ]
    
    # Check for exports
    pyproject_path = app_path / "pyproject.toml"
    if pyproject_path.exists():
        try:
            with open(pyproject_path, 'r') as f:
                data = tomlkit.parse(f.read())
            
            if 'tool' in data and 'clanker' in data['tool'] and 'exports' in data['tool']['clanker']:
                exports = data['tool']['clanker']['exports']
                lines.append("## CLI Exports")
                lines.append("Available as AI tools in Clanker console:")
                for cmd_name in exports.keys():
                    lines.append(f"- `{app_name}_{cmd_name}(args)`")
                lines.append("")
        except Exception:
            pass
    
    lines.extend([
        "## Storage",
        f"- File storage: `data/default/vault/{app_name}/`",
        "- Database: Scoped access to shared SQLite",
        "- Cross-app access requires explicit permission grants",
        "",
        "## Development",
        f"- Test locally: `cd apps/{app_name} && uv run python main.py`",
        f"- Test via Clanker: `clanker {app_name}_command_name args`",
        "- Storage access requires proper vault/db initialization"
    ])
    
    return "\n".join(lines)