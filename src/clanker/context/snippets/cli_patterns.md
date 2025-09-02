# CLI Development Patterns

## Basic App Structure
```python
import typer
from clanker.storage import AppVault

app = typer.Typer()

@app.command()
def my_command(param: str):
    """Command description."""
    vault = AppVault("myapp", vault_root="./data/default/vault", db_path="./data/default/clanker.db")
    # Do something with vault
    print(f"Processed: {param}")

if __name__ == "__main__":
    app()
```

## Export Pattern
Add to `pyproject.toml`:
```toml
[tool.clanker.exports]
my_command = "python main.py my_command {param}"
```

## Available in Clanker
- `clanker myapp_my_command param="value"`
- Becomes an AI tool for the agent
