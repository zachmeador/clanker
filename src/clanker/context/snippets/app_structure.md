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
from clanker.storage import AppVault, AppDB

vault = AppVault("your_app", vault_root="./data/default/vault", db_path="./data/default/clanker.db")
db = AppDB("your_app", db_path="./data/default/clanker.db")
```
