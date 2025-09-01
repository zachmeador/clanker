# Clanker App Specification

## Philosophy
Apps are just directories in `./apps` that follow minimal conventions. If they use typer, clanker can introspect them for metadata. No config files needed.

## What is an App?

Any directory in `./apps/` with Python code that can be executed.

## Discovery

Clanker discovers apps by:
1. Looking for Python entry points (`__main__.py`, `main.py`, `cli.py`, etc.)
2. If the app uses typer, extracting command metadata directly from the code
3. Using the module docstring as the app description

```python
# apps/weather/main.py
"""Check weather and forecasts."""

import typer
from clanker.models import AppContext

app = typer.Typer()

@app.command()
def current(location: str):
    """Get current weather for a location."""
    print(f"Weather in {location}: Sunny, 72°F")

@app.command()
def forecast(
    location: str, 
    days: int = typer.Option(5, help="Number of days")
):
    """Get weather forecast."""
    print(f"{days}-day forecast for {location}")

if __name__ == "__main__":
    app()
```

## How Clanker Discovers This

```python
# src/clanker/apps.py

import importlib.util
import typer
from pathlib import Path

def discover_app(path: Path):
    """Discover app by introspecting its code."""
    
    # Find entry file
    for entry_name in ["__main__.py", "main.py", "cli.py", "app.py"]:
        entry = path / entry_name
        if entry.exists():
            break
    else:
        return None
    
    # Import and inspect
    spec = importlib.util.spec_from_file_location("app", entry)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Look for typer app
    typer_app = None
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if isinstance(attr, typer.Typer):
            typer_app = attr
            break
    
    info = {
        "name": path.name,
        "description": module.__doc__ or "",
        "entry": f"cd {path} && uv run python {entry.name}",
    }
    
    # Extract commands if typer app found
    if typer_app:
        info["commands"] = {}
        for cmd in typer_app.registered_commands:
            name = cmd.name or cmd.callback.__name__
            info["commands"][name] = {
                "help": cmd.help or cmd.callback.__doc__ or "",
                "params": _extract_params(cmd.callback)
            }
    
    return info
```

## Running Apps

```bash
# Clanker shows discovered commands
$ clanker apps
  weather - Check weather and forecasts
    current - Get current weather for a location  
    forecast - Get weather forecast

# Run the app
$ clanker run weather current "San Francisco"
```

## Requirements

- Apps need `pyproject.toml` for dependency management (using uv)
- Apps can import clanker as a local dependency:

```toml
# apps/weather/pyproject.toml
[project]
name = "weather"
dependencies = ["clanker", "typer"]

[tool.uv.sources]
clanker = { path = "../../", editable = true }
```

## Benefits

- **Zero config**: Code is the source of truth
- **Typer integration**: Rich CLI features automatically discovered
- **Simple fallback**: Non-typer apps still work, just without command discovery
- **Natural Python**: Apps are just normal Python packages