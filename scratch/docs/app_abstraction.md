# Clanker App Abstraction Design

## Philosophy
Clanker assumes high user capability and stays out of the way. Apps are just directories in `./apps` that follow minimal conventions. No registration, no complex manifests, no framework lock-in.

## What is an App?

An app is any directory in `./apps/` that has something executable. That's it.

## Minimal Convention

```
./apps/
├── weather/
│   └── whatever.py       # Has if __name__ == "__main__" probably
├── todo/
│   ├── __main__.py      # Can be run as python -m apps.todo
│   └── other_stuff.py
└── scanner/
    └── cli.py           # Maybe uses typer, maybe not
```

## Discovery

When clanker needs to know what apps exist:

```python
# src/clanker/apps.py

from pathlib import Path
import ast

def discover_apps():
    """Find apps by looking for Python entry points in ./apps."""
    apps_dir = Path("./apps")
    if not apps_dir.exists():
        return {}
    
    apps = {}
    for app_path in apps_dir.iterdir():
        if not app_path.is_dir():
            continue
            
        # Look for executable patterns
        entry = None
        
        # Check for __main__.py
        if (app_path / "__main__.py").exists():
            entry = f"python -m apps.{app_path.name}"
        
        # Check for any .py with if __name__ == "__main__"
        else:
            for py_file in app_path.glob("*.py"):
                if _has_main_block(py_file):
                    entry = f"python {py_file}"
                    break
        
        if entry:
            apps[app_path.name] = {
                "path": app_path,
                "entry": entry,
                # Maybe extract docstring or first comment for description
                "description": _extract_description(app_path)
            }
    
    return apps

def _has_main_block(py_file: Path) -> bool:
    """Check if Python file has if __name__ == '__main__'."""
    try:
        with open(py_file) as f:
            tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    # Check for __name__ == "__main__" pattern
                    if (isinstance(node.test, ast.Compare) and
                        isinstance(node.test.left, ast.Name) and
                        node.test.left.id == "__name__"):
                        return True
    except:
        pass
    return False

def _extract_description(app_path: Path) -> str:
    """Try to grab a description from docstring, comment, or README."""
    # Check for README
    for readme in ["README.md", "README.txt", "readme.md"]:
        readme_path = app_path / readme
        if readme_path.exists():
            with open(readme_path) as f:
                first_line = f.readline().strip()
                return first_line.lstrip("#").strip()
    
    # Check main file's docstring
    for pattern in ["__main__.py", "main.py", "cli.py", "app.py"]:
        main_file = app_path / pattern
        if main_file.exists():
            try:
                with open(main_file) as f:
                    tree = ast.parse(f.read())
                    docstring = ast.get_docstring(tree)
                    if docstring:
                        return docstring.split('\n')[0]
            except:
                pass
    
    return ""
```

## CLI Interface Detection (Optional Enhancement)

If an app wants to be more discoverable, it can follow a loose pattern that clanker can detect:

```python
# apps/weather/cli.py

"""Check weather and forecasts."""  # This gets picked up

import typer

app = typer.Typer()

@app.command()
def current(location: str):
    """Get current weather."""
    pass

# Clanker could detect typer usage and extract commands
# But it's not required - app still works without this detection
```

## Running Apps

```python
# In clanker's main routing

def run_app(app_name: str, args: str = ""):
    """Just run the app with subprocess."""
    apps = discover_apps()
    
    if app_name not in apps:
        print(f"No app named '{app_name}'")
        return
    
    import subprocess
    cmd = f"{apps[app_name]['entry']} {args}"
    subprocess.run(cmd, shell=True)
```

## Clanker's Role

1. **Discovery**: `clanker app list` shows what's in ./apps
2. **Routing**: When user says something, clanker might run an app or suggest running it
3. **Context Provider**: When launching AI tools, clanker can mention available apps
4. **That's it**: No framework, no enforcement, no opinions

## App Development

When user wants to create an app:

1. Make a directory in ./apps
2. Put Python files in it
3. Maybe add an INSTRUCTIONS.md if using AI tools
4. That's it

The app can:
- Import from clanker if it wants (models, storage)
- Use any libraries it wants
- Structure itself however it wants
- Not even be Python if there's a run script

## Benefits

- **Zero friction**: Just put code in ./apps
- **No lock-in**: Apps don't need to know about clanker
- **AI-friendly**: Simple structure that AI tools understand
- **User control**: Everything is transparent and modifiable

## Non-goals

- Not trying to be a framework
- Not enforcing any structure
- Not managing dependencies
- Not doing automatic intent matching