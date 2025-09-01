"""App discovery - find and run stuff in ./apps."""

import ast
import importlib.util
import inspect
import os
import subprocess
import tomllib
from pathlib import Path
from typing import Dict, Optional, List, Any


def discover() -> Dict[str, dict]:
    """Find runnable things in ./apps."""
    apps_dir = Path("./apps")
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
        "commands": None,
    }
    
    # Parse pyproject.toml for metadata
    try:
        with open(pyproject_path, 'rb') as f:
            pyproject = tomllib.load(f)
            
        # Get description from project metadata
        project = pyproject.get("project", {})
        info["description"] = project.get("description", "")
        
        # Check for script entry points
        scripts = project.get("scripts", {})
        if scripts:
            # Use first script as entry
            script_name = next(iter(scripts.keys()))
            info["entry"] = f"cd {path} && uv run {script_name}"
            return info
    except:
        pass
    
    # Find entry file and try to extract typer commands
    entry_file = None
    
    # Check for __main__.py
    if (path / "__main__.py").exists():
        entry_file = path / "__main__.py"
        info["entry"] = f"cd {path} && uv run python -m ."
    
    # Check for main.py or cli.py or app.py with main guard
    if not entry_file:
        for name in ["main.py", "cli.py", "app.py"]:
            candidate = path / name
            if candidate.exists() and _has_main_guard(candidate):
                entry_file = candidate
                info["entry"] = f"cd {path} && uv run python {name}"
                break
    
    # Check any .py file with main guard
    if not entry_file:
        for py_file in path.glob("*.py"):
            if _has_main_guard(py_file):
                entry_file = py_file
                info["entry"] = f"cd {path} && uv run python {py_file.name}"
                break
    
    if not entry_file:
        return None
    
    # Get description and try to extract typer commands
    if not info["description"]:
        info["description"] = _get_description(entry_file)
    
    # Try to extract typer commands
    commands = _extract_typer_commands(entry_file)
    if commands:
        info["commands"] = commands
    
    return info


def _has_main_guard(py_file: Path) -> bool:
    """Check if file has if __name__ == '__main__'."""
    try:
        content = py_file.read_text()
        return "__name__" in content and "__main__" in content
    except:
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
    except:
        pass
    return None


def _extract_typer_commands(py_file: Path) -> Optional[List[str]]:
    """Try to extract typer command names from a Python file."""
    try:
        # Read the file and look for @app.command patterns using AST
        # This avoids actually importing the module which can have side effects
        content = py_file.read_text()
        tree = ast.parse(content)
        
        # Find typer app variable name
        typer_app_name = None
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Look for app = typer.Typer(...)
                if isinstance(node.value, ast.Call):
                    if (hasattr(node.value.func, 'attr') and 
                        node.value.func.attr == 'Typer'):
                        if node.targets and hasattr(node.targets[0], 'id'):
                            typer_app_name = node.targets[0].id
                            break
        
        if not typer_app_name:
            return None
        
        # Find @app.command() decorators
        commands = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for decorator in node.decorator_list:
                    # Check for @app.command()
                    if isinstance(decorator, ast.Call):
                        if (hasattr(decorator.func, 'attr') and 
                            decorator.func.attr == 'command' and
                            hasattr(decorator.func.value, 'id') and
                            decorator.func.value.id == typer_app_name):
                            # Use function name unless it's list (renamed)
                            cmd_name = node.name
                            if cmd_name == 'list_recipes':
                                cmd_name = 'list'
                            commands.append(cmd_name)
                    # Check for @app.command("name")
                    elif (hasattr(decorator, 'attr') and 
                          decorator.attr == 'command' and
                          hasattr(decorator.value, 'id') and
                          decorator.value.id == typer_app_name):
                        commands.append(node.name)
        
        return commands if commands else None
    except:
        # Silently fail - app might not use typer or might have parsing issues
        return None


def _get_description_from_dir(path: Path) -> Optional[str]:
    """Try to find description in README or similar."""
    for readme in ["README.md", "README.txt", "readme.md", "README"]:
        readme_path = path / readme
        if readme_path.exists():
            try:
                lines = readme_path.read_text().split('\n')
                for line in lines:
                    line = line.strip().lstrip('#').strip()
                    if line:
                        return line
            except:
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
    
    # Build command - entry already includes cd and uv run
    cmd = app["entry"]
    if args:
        cmd += " " + " ".join(args)
    
    # Clean environment to prevent VIRTUAL_ENV conflicts with uv
    env = os.environ.copy()
    env.pop('VIRTUAL_ENV', None)
    
    try:
        return subprocess.run(cmd, shell=True, env=env).returncode
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
        commands = info.get("commands")
        
        # Build display string
        if desc:
            display = f"  {name} - {desc}"
        else:
            display = f"  {name}"
        
        # Add commands if available
        if commands:
            display += f" [{', '.join(commands)}]"
        
        print(display)