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
- **Context generation**: Dynamic instruction files built from snippets + live state

## Storage Patterns
- Apps own their vault/database by default
- Cross-app access requires explicit permissions
- YAML/Markdown auto-parsed, other files as binary
- SQLite tables with app-scoped access
