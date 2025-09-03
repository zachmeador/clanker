# clanker

It's like a little operating system for your AI made applications.

Designed to be extended and used by LLMs.

## The Console Experience

```bash
$ clanker
# [console interaction examples here]
```

## How Apps Work

Apps are CLI tools that export commands as AI functions:

```toml
# apps/recipes/pyproject.toml
[tool.clanker.exports]
add = "python main.py add {recipe}"
search = "python main.py search {query}"
list = "python main.py list"
```

The agent can now call these as tools. Each app runs in its own `uv` environment.

## Optional Storage System

Clanker provides optional storage abstractions in `src/clanker/storage/`:

```python
from clanker.storage import AppVault, AppDB

# App-isolated file storage with permissions
vault = AppVault("my-app", vault_root, db_path)
vault.save_yaml("config.yaml", {"setting": "value"})
vault.grant_permission("other-app", "read")

# Shared SQLite with app-scoped access
db = AppDB("my-app", db_path)
```

Apps can use any storage they want - this is just provided for convenience.

## Structure

```
src/clanker/           # Core system
├── agent.py           # Main conversational agent
├── console.py         # Interactive console UX
├── apps.py            # App discovery and execution
├── tools.py           # CLI export → AI tool conversion
└── storage/           # Optional storage abstractions
    ├── vault.py       # App-isolated file storage
    └── db.py          # Shared SQLite with permissions

apps/                  # Your apps (isolated uv environments)
└── example/           # Demo app

data/default/          # Storage (when using provided abstractions)
├── vault/[app]/       # Per-app file storage  
└── clanker.db         # Shared database
```
