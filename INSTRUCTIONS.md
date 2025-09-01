# # INSTRUCTIONS

This file provides guidance to CLI coding tools when working with code in this repository.

## Commands

```bash
# CLI
clanker                          # Launch interactive console
clanker "your request"           # Natural language request (one-shot)
clanker app list                 # List available apps
clanker app run <name> [args]    # Run an app directly
clanker system models            # Show available AI models
clanker system help              # Show help

# App Development
cd apps/<app_name>
uv run python main.py <command>  # Run app CLI commands

# Dependencies (uv)
uv sync                    # Install deps in current environment
uv add <package>          # Add package to current project
uv run <command>          # Run command in current venv
```

## Architecture

### Core (`src/clanker/`)

#### Primary Modules
- **agent.py**: `ClankerAgent` - pydantic-ai agent wrapper with conversation persistence via message_history, handles natural language requests and tool orchestration
- **models.py**: Tiered model selection (LOW/MEDIUM/HIGH) with provider fallback, `create_agent()` factory for pydantic-ai agents
- **apps.py**: `discover()` finds apps in `./apps/`, `run()` executes via pyproject.toml scripts or `__main__` guards
- **cli.py**: Typer CLI entry point with natural language support, routes to apps/agent/system commands
- **console.py**: Interactive console with streaming responses, tool visibility, and conversation context

#### Tools System
- **tools.py**: Unified tool system with `create_clanker_toolset()` - discovers and creates CLI export tools from apps

#### Storage (`storage/`)
- **vault.py**: `AppVault` - app-isolated file storage with SQLite permission grants, YAML/Markdown specialization
- **db.py**: `AppDB` - shared SQLite with app-scoped table access control

#### Support
- **profile.py**: Profile management via `CLANKER_PROFILE` env var
- **logger.py**: Centralized logging to `data/<profile>/logs/clanker.log`, stderr for errors
- **__init__.py**: Package initialization and public API exports

### Apps (`apps/`)
Standalone Python packages with:
- Own `pyproject.toml` declaring deps (including `clanker` as editable)
- CLI commands defined in `main.py` with typer
- **CLI Exports**: Optional `[tool.clanker.exports]` section in `pyproject.toml` to expose CLI commands as AI tools
- Isolated storage: `data/<profile>/vault/<app_name>/` (profile defaults to "default")
- Logs written to `data/<profile>/logs/clanker.log`
- Cross-app access via permission grants in shared DB

### CLI Export System
Apps can expose their CLI commands as AI tools by adding to `pyproject.toml`:

```toml
[tool.clanker.exports]
hello = "python main.py hello {name}"
status = "python main.py status"
```

These become available as AI tools:
- `example_hello(name="Alice")` → `python apps/example/main.py hello Alice`
- `example_status()` → `python apps/example/main.py status`

### App Development Workflow
```bash
# Create new app
mkdir apps/myapp
cd apps/myapp

# Initialize with typer CLI
# Add [tool.clanker.exports] to pyproject.toml to expose commands
# Commands automatically become AI tools in Clanker console
```

### App Usage Pattern
```python
from clanker.models import create_agent, ModelTier
from clanker.storage import AppVault, AppDB

# Get AI agent with tier-based model selection
agent = create_agent(ModelTier.MEDIUM)

# Access app storage
vault = AppVault("my-app", vault_root, db_path)
db = AppDB("my-app", db_path)

# Cross-app access requires permission grant
vault.grant_permission("other-app", "read")
```

### Configuration
API keys in `.env`: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`

Model tiers auto-select from available providers:
- **LOW**: Fast, cheap models (gpt-4o-mini, claude-3-5-haiku)
- **MEDIUM**: Balanced performance (gpt-4o, claude-3-5-sonnet)
- **HIGH**: Maximum quality (gpt-4o, claude-3-5-sonnet, claude-3-7-sonnet)

### Key Design Principles

1. **Environment Isolation**: Each app runs in its own `uv` environment
2. **Explicit Integration**: Apps opt-in via `[tool.clanker.exports]`
3. **CLI-First**: Apps designed as CLI tools, not direct API calls
4. **AI Tool Focus**: Apps built for AI agent consumption
5. **Natural Interaction**: Users talk to Clanker, not individual apps

### Recent Improvements

- **Conversation Persistence**: Agent now uses pydantic-ai's `message_history` for reliable conversation context across interactions
- **Unified Tool System**: Simplified tool discovery and creation through consolidated `tools.py` (removed unnecessary subdirectory)
- **Streamlined Architecture**: Removed complex input resolution and manual memory management while preserving UX