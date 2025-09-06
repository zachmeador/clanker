# Clanker Environment Overview

Clanker is a lightweight LLM application framework where each app runs in its own `uv` environment with isolated storage.

## Core Components
- **Core system**: `src/clanker/` - Agent, CLI, storage, tools
- **User apps**: `apps/` - Standalone Python packages with dependencies
- **Isolated storage**: `data/<profile>/vault/<app_name>/` - File storage per app
- **Shared database**: `data/<profile>/clanker.db` - SQLite with app isolation

## Key Features
- **App isolation**: Each app has own dependencies and storage
- **Tool exports**: App commands become AI tools via `pyproject.toml` exports
- **Storage conventions**: Vault for files, DB for tables, with permission system
- **Daemon management**: Background services defined in app config
- **Profile system**: Multiple isolated environments (default, dev, etc.)

## Storage Patterns
- Apps own their vault/database by default
- Cross-app access requires explicit permissions
- YAML/Markdown auto-parsed, other files as binary
- SQLite tables with app-scoped access

# App Structure

Every Clanker app should follow this structure:

```
apps/your_app/
├── main.py              # CLI commands with typer
├── pyproject.toml       # Dependencies + CLI exports
├── README.md           # Documentation
└── your_app/           # Package directory
    ├── __init__.py
    ├── models.py       # Data models
    ├── storage.py      # Storage operations
    └── cli.py          # Command implementations
```

## Key Files

### main.py - Entry Point
```python
import typer
from your_app.cli import your_command

app = typer.Typer()

@app.command()
def your_command(name: str):
    """Your command description."""
    result = your_command(name)
    print(result)

if __name__ == "__main__":
    app()
```

### pyproject.toml - Configuration
```toml
[project]
name = "your_app"
version = "0.1.0"
dependencies = ["clanker", "typer"]

[tool.clanker.exports]
your_command = "python main.py your_command {name}"
```

### Storage Integration
```python
from clanker.storage import Vault, DB

vault = Vault.for_app("your_app")
db = DB.for_app("your_app")

# Write config
vault.write("config.yml", {"setting": "value"})

# Create tables
db.create_table("users", {
    "id": "INTEGER PRIMARY KEY",
    "name": "TEXT NOT NULL"
})
```

## Tool Exports
Make app commands available as AI tools by adding exports to `pyproject.toml`:

```toml
[tool.clanker.exports]
hello = "python main.py hello {name}"
search = "python main.py search --query {query}"
```

The agent will see these as `your_app_hello(name="Alice")` and `your_app_search(query="pasta")` tools.

# Storage Guide

## Vault - File Storage
```python
from clanker.storage import Vault

vault = Vault.for_app("myapp")

# Write files
vault.write("config.yml", {"setting": "value"})
vault.write("data.json", my_data)

# Read files
config = vault.read("config.yml")  # Auto-parses YAML
data = vault.read("data.json")     # Auto-parses JSON

# List files
files = vault.list()  # All files in app vault
files = vault.list("subfolder")  # Files in subfolder
```

## DB - Database Storage
```python
from clanker.storage import DB

db = DB.for_app("myapp")

# Create table
db.create_table("items", {
    "id": "INTEGER PRIMARY KEY",
    "name": "TEXT NOT NULL",
    "value": "TEXT"
})

# Insert data
db.insert("items", {"name": "test", "value": "data"})

# Query data
results = db.query("items", {"name": "test"})
```

## Cross-App Access
Apps can access each other's storage with explicit permissions:

```python
# Grant permission
vault = Vault()
vault.grant_permission("requester-app", "target-app", read=True, write=False)

# Access another app's vault
vault = Vault.for_app("target-app", requester_app="requester-app")
data = vault.read("shared-config.yml")
```

## Storage Types
- **Vault**: Files (.yml/.yaml auto-parsed, .md as text, others as binary)
- **DB**: SQLite tables with app isolation and permissions

# Current Apps

## example
- **Location**: `apps/example/`
- **Description**: Example app demonstrating CLI-based exports
- **CLI Exports**: hello, status, weather
- **Commands**: `clanker example_hello`, `clanker example_status`, `clanker example_weather`

## weather_daemon
- **Location**: `apps/weather_daemon/`
- **Description**: Example weather monitoring daemon for Clanker
- **CLI Exports**: weather, status
- **Commands**: `clanker weather_daemon_weather`, `clanker weather_daemon_status`

## Development
Create new apps in `apps/` directory with:
- `main.py` with typer CLI
- `pyproject.toml` with dependencies and exports
- Isolated storage via Clanker storage system

# Daemon Management

Available daemon management commands:
- `daemon_list()` - Show all daemons with status
- `daemon_start(app, daemon_id)` - Start specific daemon  
- `daemon_stop(app, daemon_id)` - Stop specific daemon
- `daemon_logs(app, daemon_id)` - View recent logs
- `daemon_status(app, daemon_id)` - Check daemon status
- `daemon_restart(app, daemon_id)` - Restart daemon
- `daemon_kill_all()` - Emergency stop all daemons
- `daemon_enable_autostart(app, daemon_id)` - Enable autostart
- `daemon_start_enabled()` - Start all autostart-enabled daemons

Daemons are defined in app's `pyproject.toml`:
```toml
[tool.clanker.daemons]  
background = "python daemon.py --interval 300"
```

# System Status

example app: Test with 'hello NAME' or 'check status' or 'weather NYC'. Returns formatted greetings, status tables, or mock weather data.
weather_daemon: Ask 'what's the weather in CITY'. Returns JSON weather data, may cache results.
System: No daemons running. Use daemon_start to launch background services.