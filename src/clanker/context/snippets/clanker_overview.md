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
