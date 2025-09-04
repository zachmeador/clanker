# clanker

It's like a little operating system for your AI made applications.

Designed to be extended and used by LLMs.

## The Console Experience

```bash
$ clanker
╭──────────────────────────────────────────╮
│ Clanker Interactive Console              │
│ Type 'help' for commands, 'exit' to quit │
╰──────────────────────────────────────────╯
Try: 'list my apps', 'what recipes do I have', 'help me with...'


You: tldr, what can you do?

Clanker: I can help with running Clanker apps and managing their functions, such as executing commands, checking statuses, and starting or stopping daemons. I can also assist with development tasks and provide contextual information about the Clanker system. 
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
src/clanker/                    # Core system
├── agent.py                    # Main conversational agent
├── apps.py                     # App discovery and execution
├── cli.py                      # Command-line interface
├── console.py                  # Interactive console UX
├── daemon.py                   # Daemon management
├── input_resolution.py         # Input processing and resolution
├── logger.py                   # Logging utilities
├── models.py                   # Data models
├── profile.py                  # User profiles and configuration
├── tools.py                    # CLI export → AI tool conversion
├── context/                    # Context management system
│   ├── builder.py              # Context builders
│   ├── store.py                # Context storage
│   ├── templates.py            # Context templates
│   └── snippets/               # Context snippet templates
└── storage/                    # Optional storage abstractions
    ├── db.py                   # Shared SQLite with permissions
    ├── schema.py               # Database schema definitions
    └── vault.py                # App-isolated file storage

data/default/                   # Core storage
├── clanker.db                  # Shared database
├── daemons/                    # Daemon state and configuration
├── logs/                       # Application logs
│   └── clanker.log             # Main log file
└── vault/                      # File storage
    └── clanker/                # Core system storage

docs/                           # Documentation
├── dependency_distillations/   # Dependency analysis docs
└── dev_notes/                  # Development notes

scratch/                        # Experimental/development code
```
