# clanker

It's like a little OS for your AI made applications.

Designed to be extended and used by LLMs.

## Project Structure

```
clanker/
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
│   └── resumes/            # AI-powered resume generator
│
├── data/                   # Persistent data storage
│   └── default/            # Default profile
│       ├── clanker.db      # Shared SQLite database
│       ├── logs/           # Application logs
│       └── vault/          # File storage per app
│           ├── recipes/    # Recipe app files
│           └── resumes/    # Resume app files
```
