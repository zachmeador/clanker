# {{app_name.title()}} App

## Overview
{{description}}

## Clanker App Structure
{{app_structure}}

## Implementation Steps

### 1. Set up basic structure
```bash
mkdir apps/{{app_name}}
cd apps/{{app_name}}
uv init
uv add clanker typer pydantic
```

### 2. Create main.py with typer commands
```python
import typer

app = typer.Typer()

@app.command()
def hello(name: str = "world"):
    """Say hello."""
    print(f"Hello {{name}}!")

if __name__ == "__main__":
    app()
```

### 3. Add CLI exports to pyproject.toml
```toml
[tool.clanker.exports]
hello = "python main.py hello {name}"
```

### 4. Implement storage
{{storage_guide}}

## Testing
- Test locally: `uv run python main.py hello`
- Test via Clanker: `clanker {{app_name}}_hello name="test"`

## Next Steps
{{cli_patterns}}
{{export_system}}
