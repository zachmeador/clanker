# clanker

It's like a little OS for your AI made applications.

Designed to be extended and used by LLMs.

## Project Structure

```
clanker/
├── pyproject.toml          # Workspace root configuration
├── clanker/                # Core clanker package
│   ├── __init__.py         # Package exports
│   ├── models.py           # AI model abstractions (tiers, providers)
│   ├── logger.py           # Centralized logging with loguru
│   ├── config/             # Configuration management
│   │   ├── __init__.py
│   │   └── logging.py
│   └── storage/            # Shared storage abstractions
│       ├── __init__.py
│       ├── db.py           # SQLite database with permissions
│       └── vault.py        # File storage with cross-app permissions
├── apps/                   # Individual clanker applications
│   ├── recipes/            # Recipe management app
│   │   ├── pyproject.toml
│   │   └── recipes/
│   └── resumes/            # AI-powered resume generator
│       ├── pyproject.toml
│       └── resumes/
├── data/                   # Persistent data storage
│   └── default/            # Default profile
│       ├── clanker.db      # Shared SQLite database
│       ├── logs/           # Application logs
│       └── vault/          # File storage per app
│           ├── recipes/    # Recipe app files
│           └── resumes/    # Resume app files
```

### Key Components

- **clanker/**: Core package providing shared utilities, model abstractions, and storage
- **apps/**: Directory containing individual applications that use clanker's capabilities
- **Workspace**: Uses uv workspace management to link apps with the core clanker package