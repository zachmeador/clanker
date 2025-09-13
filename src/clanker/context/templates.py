"""High-level context templates for common scenarios."""

from pathlib import Path
from typing import Optional, Dict

from .builder import ContextBuilder
from .store import ContextStore
from .hints import get_smart_hints
from ..apps import discover as discover_apps




def coding_session_context(tool_name: str, user_request: str) -> str:
    """Build context for coding CLI sessions launched from Clanker.
    
    Combines agent-like context with INSTRUCTIONS.md and session info.
    Supports various tools like Claude Code, Cursor, Gemini, etc.
    
    Args:
        tool_name: Name of the coding tool (e.g., "claude", "cursor", "gemini")
        user_request: The user's request/intent for the session
        
    Returns:
        Complete context document for the coding session
    """
    sections = []
    snippets_dir = Path(__file__).parent / "snippets"
    
    # Add session header
    tool_display = tool_name.title() if tool_name else "Coding"
    session_header = f"""# Clanker {tool_display} Session

This {tool_display} session was launched from Clanker. You have full context about the Clanker system 
and should help with development tasks within this environment.

---"""
    sections.append(session_header)
    
    # Load and add INSTRUCTIONS.md content
    try:
        project_root = Path(__file__).resolve().parent.parent.parent
        instructions_path = project_root / "INSTRUCTIONS.md"
        if instructions_path.exists():
            instructions = instructions_path.read_text()
            # Remove the first # header since we have our own
            if instructions.startswith("# "):
                instructions = instructions[instructions.find("\n") + 1:]
            sections.append(instructions.strip())
    except Exception:
        pass  # Gracefully continue without INSTRUCTIONS.md
    
    # Add a separator before dynamic content
    sections.append("---\n## Current System State")
    
    # Add the same base context as the agent
    try:
        sections.append((snippets_dir / "clanker_overview.md").read_text())
    except FileNotFoundError:
        pass
    
    # Add smart contextual hints
    hints = get_smart_hints()
    if hints:
        sections.append(f"## Contextual Hints\n\n{hints}")
    
    # Add CLI patterns and export system
    for snippet in ["cli_patterns", "export_system"]:
        try:
            sections.append((snippets_dir / f"{snippet}.md").read_text())
        except FileNotFoundError:
            pass
    
    # Add user request
    if user_request:
        sections.append(f"## Session Intent\n\n**User Request**: {user_request}")
    
    return "\n\n".join(sections).strip()


def app_scaffold_context(app_name: str, description: str) -> str:
    """Build context for scaffolding a new app.
    
    Args:
        app_name: Name of the app to scaffold
        description: Description of what the app should do
        
    Returns:
        Complete scaffold guide as markdown
    """
    sections = []
    snippets_dir = Path(__file__).parent / "snippets"
    
    # Add header
    sections.append(f"# {app_name.title()} App\n\n## Overview\n{description}")
    
    # Add structure guide
    try:
        sections.append((snippets_dir / "app_structure.md").read_text())
    except FileNotFoundError:
        pass
    
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
- Test via Clanker: `clanker {app_name}_hello name="test"`"""
    sections.append(implementation)
    
    # Add storage guide, export system details, and CLI patterns
    for snippet in ["storage_guide", "export_system", "cli_patterns"]:
        try:
            sections.append((snippets_dir / f"{snippet}.md").read_text())
        except FileNotFoundError:
            pass
    
    return "\n\n".join(sections).strip()


def build_all_contexts(query: Optional[str] = None) -> Dict[str, bool]:
    """Generate all instruction files from snippets.
    
    Creates INSTRUCTIONS.md and all tool-specific context files from snippets
    plus dynamic system state.
    
    Args:
        query: Optional user query to include in context
        
    Returns:
        Dict mapping filename -> success status
    """
    builder = ContextBuilder()
    
    # Build core content from snippets in logical order
    builder.add_snippet("clanker_overview")
    builder.add_snippet("export_system") 
    builder.add_snippet("cli_patterns")
    builder.add_snippet("app_structure")
    builder.add_snippet("storage_guide")
    
    # Add dynamic content - current apps and state
    apps_context = get_available_apps_context()
    if apps_context and apps_context != "No apps found in apps/ directory.":
        builder.add(apps_context, "Current Apps")
    
    # Add daemon management section
    builder.add_snippet("daemon_management")
    
    # Add smart hints about current system state
    hints = get_smart_hints()
    if hints and hints != "No app-specific context available.":
        builder.add(hints, "System Status")
    
    # Add user query if provided
    if query:
        builder.add(f"**Current Request**: {query}", "User Query")
    
    # Build final content and write to all files
    content = builder.build()
    store = ContextStore()
    return store.write_all(content)


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


