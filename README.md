# clanker

It's like a little operating system for your AI made applications.

Designed to be extended and used by LLMs.

## Project Status

Clanker is currently in active prototyping/alpha. 

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
add = {cmd = "python main.py add {recipe}", desc = "Add a new recipe"}
search = {cmd = "python main.py search {query}", desc = "Search recipes"}
list = {cmd = "python main.py list", desc = "List all recipes"}

[tool.clanker.daemons]
web_server = "python main.py serve --port 8000"
background_worker = "python main.py worker --threads 4"
```

The agent can:
- **Execute CLI commands** - Run app functions as tools with parameters
- **Manage daemons** - Start, stop, and monitor background processes
- **Access storage** - Use isolated file storage and shared databases

Each app runs in its own `uv` environment with automatic tool discovery and daemon management.

**Note**: Export commands like `"python main.py add {recipe}"` are executed as `uv run --project apps/recipes python main.py add {recipe}` to ensure proper isolation.

## Storage System

Clanker provides optional storage abstractions for app development:

```python
from clanker.storage import Vault, DB

# App-isolated file storage 
vault = Vault.for_app("my-app")
vault.write("config.yml", {"setting": "value"})  # Auto-parses YAML

# Cross-app permissions
main_vault = Vault()
main_vault.grant_permission("requester-app", "my-app", read=True)

# Isolated SQLite per app
db = DB.for_app("my-app")  # data/default/apps/my-app/db.sqlite
db.create_table("items", {"id": "INTEGER PRIMARY KEY", "name": "TEXT"})
```

**Features:**
- **Vault** - File storage (.yml/.yaml auto-parsed, .md as text, others binary)
- **DB** - Isolated SQLite database per app (complete isolation)
- **Isolation** - Apps own their data by default, vault sharing via explicit grants
- **Profiles** - Multiple environments (default, dev, prod) with separate storage

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

## Context Building System

Clanker dynamically generates context files (INSTRUCTIONS.md, CLAUDE.md, etc.) to keep coding tools informed about your current system state:

```python
# Context is rebuilt automatically when:
# 1. Launching coding tools (claude, cursor, etc.)
# 2. Running `clanker build` command

from clanker.context import build_all_contexts
results = build_all_contexts(query="user request")
```

**How it works:**
- **Modular snippets** - Base content from `src/clanker/context/snippets/`
- **Dynamic discovery** - Live app exports, daemon status, system hints
- **Tool-specific files** - CLAUDE.md, AGENTS.md (for Cursor), GEMINI.md
- **Always current** - Context reflects real-time system state

**Build triggers:**
- `launch_coding_tool()` - Rebuilds before launching any coding session
- `clanker build` - Manual rebuild command

This ensures coding assistants have up-to-date knowledge of your apps, exports, storage patterns, and system architecture.

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
