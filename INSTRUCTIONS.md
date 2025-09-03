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

[tool.clanker.daemons]
background_task = "python daemon.py --interval 300"
```

Becomes AI tools:
- `example_hello(name="Alice")` → `python apps/example/main.py hello Alice`
- `example_status()` → `python apps/example/main.py status`
- Daemon tools: `daemon_start("example", "background_task")`

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
- **daemon.py**: `ClankerDaemon`, `DaemonManager` for background processes

#### Storage
- **vault.py**: `AppVault` - app-isolated file storage
- **db.py**: `AppDB` - shared SQLite with app-scoped access

### Apps (`apps/`)
Standalone Python packages with:
- Own `pyproject.toml` with deps and `[tool.clanker.exports]`
- CLI commands in `main.py` with typer
- Optional background daemons via `[tool.clanker.daemons]`
- Isolated storage: `data/<profile>/vault/<app_name>/`
- Cross-app access via permission grants

### App Usage Pattern
```python
from clanker.models import create_agent, ModelTier
from clanker.storage import AppVault, AppDB
from clanker.daemon import ClankerDaemon

agent = create_agent(ModelTier.MEDIUM)
vault = AppVault("my-app", vault_root, db_path)
db = AppDB("my-app", db_path)
daemon = ClankerDaemon("my-app", "background_task")
vault.grant_permission("other-app", "read")  # Cross-app access
```

### Key Design Principles

1. **Build CLI commands, not Python APIs**
2. **Apps communicate via exports, never direct imports**
3. **Users interact with Clanker, Clanker orchestrates apps**
4. **Each app runs in isolated `uv` environment**
5. **Apps opt-in to integration via `[tool.clanker.exports]`**
6. **Background tasks use decentralized app-owned daemons**

## Daemon System

### Daemon Development
Apps can define background processes that run continuously:

```toml
[tool.clanker.daemons]
monitor = "python daemon.py --interval 300"
sync = "python sync_daemon.py"
```

### Daemon Management Tools
- `daemon_list()` - Show all daemons with status
- `daemon_start(app, daemon_id)` - Start specific daemon
- `daemon_stop(app, daemon_id)` - Stop specific daemon
- `daemon_logs(app, daemon_id)` - View recent logs
- `daemon_kill_all()` - Emergency stop all daemons

### Daemon Implementation
```python
from clanker.daemon import ClankerDaemon
import signal

class MyDaemon:
    def __init__(self):
        self.running = True
        signal.signal(signal.SIGTERM, self._shutdown)
        
    def _shutdown(self, signum, frame):
        self.running = False
        
    async def run(self):
        while self.running:
            # Do work
            await asyncio.sleep(interval)
```

Storage: PIDs in `data/<profile>/daemons/`, logs in `data/<profile>/logs/`