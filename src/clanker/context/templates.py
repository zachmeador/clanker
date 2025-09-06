"""High-level context templates for common scenarios."""

from pathlib import Path
from typing import Optional

from .hints import get_smart_hints




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




