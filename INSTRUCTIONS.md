# # INSTRUCTIONS

This file provides guidance to CLI coding tools when working with code in this repository.

## Commands

```bash
clanker                          # Launch interactive console
clanker "your request"           # Natural language request (one-shot)
clanker app list                 # List available apps
clanker app run <name> [args]    # Run an app directly
clanker system models            # Show available AI models
```

## CLI Export System (Core Concept)

Apps expose CLI commands as AI tools via `pyproject.toml`:

```toml
[tool.clanker.exports]
hello = "python main.py hello {name}"
status = "python main.py status"
```

Becomes AI tools:
- `example_hello(name="Alice")` → `python apps/example/main.py hello Alice`
- `example_status()` → `python apps/example/main.py status`

## Quick Start
```bash
mkdir apps/myapp && cd apps/myapp
uv init && uv add clanker typer
# Create main.py with typer commands
# Add [tool.clanker.exports] to pyproject.toml
# Now: clanker "use myapp to do X"
```

## Architecture

### Core (`src/clanker/`)

#### Primary Modules
- **agent.py**: `ClankerAgent` with conversation persistence
- **models.py**: Tiered model selection, `create_agent()` factory
- **apps.py**: `discover()` apps, `run()` executes them
- **cli.py**: Typer entry point, routes to apps/agent/system
- **console.py**: Interactive console with streaming responses
- **tools.py**: `create_clanker_toolset()` - discovers CLI export tools

#### Storage
- **vault.py**: `AppVault` - app-isolated file storage
- **db.py**: `AppDB` - shared SQLite with app-scoped access

### Apps (`apps/`)
Standalone Python packages with:
- Own `pyproject.toml` with deps and `[tool.clanker.exports]`
- CLI commands in `main.py` with typer
- Isolated storage: `data/<profile>/vault/<app_name>/`
- Cross-app access via permission grants

### App Usage Pattern
```python
from clanker.models import create_agent, ModelTier
from clanker.storage import AppVault, AppDB

agent = create_agent(ModelTier.MEDIUM)
vault = AppVault("my-app", vault_root, db_path)
db = AppDB("my-app", db_path)
vault.grant_permission("other-app", "read")  # Cross-app access
```

### Key Design Principles

1. **Build CLI commands, not Python APIs**
2. **Apps communicate via exports, never direct imports**
3. **Users interact with Clanker, Clanker orchestrates apps**
4. **Each app runs in isolated `uv` environment**
5. **Apps opt-in to integration via `[tool.clanker.exports]`