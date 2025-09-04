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

The console provides:
- **Streaming responses** - Real-time output as the AI processes your request
- **Tool visibility** - See exactly which tools are being called and their parameters
- **Context awareness** - Maintains conversation history for better responses
- **Interactive commands** - Use `context`, `tools`, and `help` for console management
- **Natural language queries** - Ask questions conversationally instead of using complex commands

## How Apps Work

Apps are CLI tools that export both commands and daemons as AI functions:

```toml
# apps/recipes/pyproject.toml
[tool.clanker.exports]
add = "python main.py add {recipe}"
search = "python main.py search {query}"
list = "python main.py list"

[tool.clanker.daemons]
web_server = "python main.py serve --port 8000"
background_worker = "python main.py worker --threads 4"
```

The agent can:
- **Execute CLI commands** - Run app functions as tools with parameters
- **Manage daemons** - Start, stop, and monitor background processes
- **Access storage** - Use isolated file storage and shared databases

Each app runs in its own `uv` environment with automatic tool discovery and daemon management.

## Optional Storage System

Clanker provides optional storage abstractions in `src/clanker/storage/`:

```python
from clanker.storage import AppVault, AppDB

# App-isolated file storage with permissions
vault = AppVault.for_app("my-app")
vault.write("config.yaml", {"setting": "value"})
vault.grant_permission("my-app", "other-app", read=True)

# Shared SQLite with app-scoped access
db = AppDB("my-app", db_path)
```

The storage system provides:
- **AppVault** - Isolated file storage with cross-app permission controls
- **AppDB** - Shared SQLite database with app-scoped table access
- **Automatic isolation** - Apps can only access their own data by default
- **Permission grants** - Explicit permissions required for cross-app access

Apps can use any storage they want - this is just provided for convenience.

## Coding CLI Integration

Launch coding tools directly from Clanker with full system context:

```bash
clanker "open claude code to work on my recipe app"
clanker "use cursor to fix the weather daemon"
```

**In the Interactive Console:**
```bash
You: I want to work on the weather daemon using Claude Code
Clanker: I'll launch Claude Code with full context...

[Launches Claude Code with complete Clanker environment context]
```

**Supported Tools:**
- **Claude Code** - Natural language like "claude" or "claude code"
- **Cursor** - Reference as "cursor" or "cursor editor"
- **Gemini** - Google's coding assistant

The tool opens with comprehensive context about your apps, architecture, and development patterns for seamless coding sessions.

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
