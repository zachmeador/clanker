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
