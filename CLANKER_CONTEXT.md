# Clanker Gemini Session

This Gemini session was launched from Clanker. You have full context about the Clanker system 
and should help with development tasks within this environment.

---

---
## Current System State

# Clanker Environment Overview

Clanker is an LLM app environment where each app runs in its own `uv` environment with isolated storage.

## Core Components
- **Core system**: `src/clanker/` - Agent, CLI, storage, tools
- **User apps**: `apps/` - Standalone Python packages
- **Isolated storage**: `data/<profile>/vault/<app_name>/`
- **Shared database**: `data/<profile>/clanker.db`

## Key Features
- Apps are standalone with own dependencies
- CLI exports make app commands available as AI tools
- Storage is app-isolated by default with permission system
- Profile system for data isolation


## Available Apps

## example
- **Location**: `apps/example/`
- **Description**: Example app demonstrating CLI-based exports
- **CLI Exports**: hello, status
- **Commands**: `clanker example_hello`, `clanker example_status`

## Development
Create new apps in `apps/` directory with:
- `main.py` with typer CLI
- `pyproject.toml` with dependencies and exports
- Isolated storage via Clanker storage system

# CLI Development Patterns

## Basic App Structure
```python
import typer
from clanker.storage import AppVault

app = typer.Typer()

@app.command()
def my_command(param: str):
    """Command description."""
    vault = AppVault("myapp", vault_root="./data/default/vault", db_path="./data/default/clanker.db")
    # Do something with vault
    print(f"Processed: {param}")

if __name__ == "__main__":
    app()
```

## Export Pattern
Add to `pyproject.toml`:
```toml
[tool.clanker.exports]
my_command = "python main.py my_command {param}"
```

## Available in Clanker
- `clanker myapp_my_command param="value"`
- Becomes an AI tool for the agent


# CLI Export System

## How It Works
Apps can expose their CLI commands as AI tools by adding `[tool.clanker.exports]` to `pyproject.toml`:

```toml
[tool.clanker.exports]
hello = "python main.py hello {name}"
status = "python main.py status"
search = "python main.py search --query {query}"
```

## Available as AI Tools
- `appname_hello(name="Alice")` → `python apps/appname/main.py hello Alice`
- `appname_status()` → `python apps/appname/main.py status`
- `appname_search(query="pasta")` → `python apps/appname/main.py search --query pasta`

## In Clanker Console
```bash
clanker "use the hello command"
# Agent finds and calls appname_hello tool
```

## Parameter Types
- String parameters: `{param}`
- Optional parameters: `{param}` (agent decides if needed)
- All parameters passed as command line arguments


## Session Intent

**User Request**: general development work