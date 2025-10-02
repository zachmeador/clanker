"""App discovery - find and run stuff in ./apps."""

import ast
import os
import shlex
import subprocess
import tomllib
from pathlib import Path
from typing import Dict, Optional, List, Any, Union


def _project_root() -> Path:
    """Resolve the project root directory regardless of CWD."""
    # apps.py is at src/clanker/apps.py → project root is three parents up
    return Path(__file__).resolve().parent.parent.parent


def discover() -> Dict[str, dict]:
    """Find runnable things in ./apps."""
    apps_dir = _project_root() / "apps"
    if not apps_dir.exists():
        return {}
    
    found = {}
    for item in apps_dir.iterdir():
        if not item.is_dir() or item.name.startswith(('_', '.')):
            continue
        
        info = _inspect_app(item)
        if info:
            found[item.name] = info
    
    return found


def _inspect_app(path: Path) -> Optional[dict]:
    """Figure out how to run this app."""
    # Python apps need pyproject.toml
    pyproject_path = path / "pyproject.toml"
    if not pyproject_path.exists():
        return None
    
    info = {
        "path": str(path),
        "entry": None,
        "description": None,
        "exports": [],  # CLI exports from pyproject.toml
    }
    
    # Parse pyproject.toml for metadata
    try:
        with open(pyproject_path, 'rb') as f:
            pyproject = tomllib.load(f)

        # Get description from project metadata
        project = pyproject.get("project", {})
        info["description"] = project.get("description", "")
        
        # Get CLI exports if defined
        tool_config = pyproject.get("tool", {})
        clanker_config = tool_config.get("clanker", {})
        exports = clanker_config.get("exports", {})
        if exports:
            info["exports"] = list(exports.keys())

        # Check for script entry points
        scripts = project.get("scripts", {})
        if scripts:
            # Use first script as entry
            script_name = next(iter(scripts.keys()))
            info["entry"] = {
                "cwd": str(path),
                "command": ["uv", "run", script_name]
            }
            return info
    except (FileNotFoundError, tomllib.TOMLKitError, KeyError):
        pass
    
    # Find entry file and try to extract typer commands
    entry_file = None
    
    # Check for __main__.py
    if (path / "__main__.py").exists():
        entry_file = path / "__main__.py"
        info["entry"] = {
            "cwd": str(path),
            "command": ["uv", "run", "python", "__main__.py"]
        }
    
    # Check for main.py or cli.py or app.py with main guard
    if not entry_file:
        for name in ["main.py", "cli.py", "app.py"]:
            candidate = path / name
            if candidate.exists() and _has_main_guard(candidate):
                entry_file = candidate
                info["entry"] = {
                    "cwd": str(path),
                    "command": ["uv", "run", "python", name]
                }
                break
    
    # Check any .py file with main guard
    if not entry_file:
        for py_file in path.glob("*.py"):
            if _has_main_guard(py_file):
                entry_file = py_file
                info["entry"] = {
                    "cwd": str(path),
                    "command": ["uv", "run", "python", py_file.name]
                }
                break
    
    if not entry_file:
        return None
    
    # Get description from file if not in pyproject
    if not info["description"]:
        info["description"] = _get_description(entry_file)
    
    return info


def _has_main_guard(py_file: Path) -> bool:
    """Check if file has if __name__ == '__main__'."""
    try:
        content = py_file.read_text()
        return "__name__" in content and "__main__" in content
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return False


def _get_description(py_file: Path) -> Optional[str]:
    """Extract docstring from Python file."""
    try:
        tree = ast.parse(py_file.read_text())
        docstring = ast.get_docstring(tree)
        if docstring:
            # First non-empty line
            for line in docstring.split('\n'):
                line = line.strip()
                if line:
                    return line
    except (FileNotFoundError, PermissionError, UnicodeDecodeError, SyntaxError):
        pass
    return None


def run(app_name: str, args: List[str] = None) -> int:
    """Run an app by name."""
    apps = discover()
    
    if app_name not in apps:
        print(f"App '{app_name}' not found")
        available = list(apps.keys())
        if available:
            print(f"Available: {', '.join(available)}")
        return 1
    
    app = apps[app_name]
    if not app.get("entry"):
        print(f"App '{app_name}' has no entry point")
        return 1
    
    # Parse entry command safely
    entry = app["entry"]
    if isinstance(entry, str):
        # Backward compatibility - parse old shell command format
        parts = entry.split(" && ")
        if len(parts) == 2 and parts[0].startswith("cd "):
            cwd = parts[0][3:].strip()
            command = shlex.split(parts[1])
        else:
            cwd = None
            command = shlex.split(entry)
    else:
        # New structured format
        cwd = entry.get("cwd")
        command = entry["command"][:]

    # Safely append user arguments as list elements
    if args:
        command.extend(args)

    # Clean environment to prevent VIRTUAL_ENV conflicts with uv
    env = os.environ.copy()
    env.pop('VIRTUAL_ENV', None)

    try:
        return subprocess.run(command, cwd=cwd, env=env).returncode
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        print(f"Failed to run '{app_name}': {e}")
        return 1


def list_apps() -> None:
    """Print discovered apps."""
    apps = discover()
    
    if not apps:
        print("No apps found in ./apps")
        return
    
    print("Available apps:")
    for name, info in apps.items():
        desc = info.get("description", "")
        exports = info.get("exports", [])
        
        # Build display string
        if desc:
            display = f"  {name} - {desc}"
        else:
            display = f"  {name}"
        
        # Add exports if available
        if exports:
            display += f" [exports: {', '.join(exports)}]"
        
        print(display)