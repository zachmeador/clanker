"""Core context manager for Clanker."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import tomlkit


class CoreContextManager:
    """Manages context snippets and templates for core Clanker functionality."""

    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.templates_dir = self.base_dir / "templates"
        self.snippets_dir = self.base_dir / "snippets"
        self._snippet_cache: Dict[str, str] = {}

    def get_session_context(self, tool_name: str, app_name: Optional[str] = None, user_request: Optional[str] = None) -> str:
        """Get context for coding tool session."""
        template_path = self.templates_dir / "sessions" / f"{tool_name}.md"

        if not template_path.exists():
            # Fallback to generic session template
            template_path = self.templates_dir / "sessions" / "generic.md"

        if not template_path.exists():
            raise FileNotFoundError(f"No template found for tool '{tool_name}' or generic session")

        template = template_path.read_text()

        # Get context components
        clanker_overview = self.get_snippet("clanker_overview")
        available_apps = self._get_available_apps_context()
        cli_patterns = self.get_snippet("cli_patterns")

        app_context = ""
        if app_name:
            app_context = self.get_snippet("app_context")

        # Simple variable substitution
        context = template.replace("{{clanker_overview}}", clanker_overview)
        context = context.replace("{{available_apps}}", available_apps)
        context = context.replace("{{cli_patterns}}", cli_patterns)
        context = context.replace("{{app_context}}", app_context)
        context = context.replace("{{app_name}}", app_name or "general")
        context = context.replace("{{user_request}}", user_request or "")

        return context

    def get_app_scaffold_context(self, app_name: str, description: str) -> str:
        """Get context for scaffolding a new app."""
        template_path = self.templates_dir / "apps" / "scaffold.md"

        if not template_path.exists():
            raise FileNotFoundError(f"No scaffold template found")

        template = template_path.read_text()

        # Get relevant snippets
        app_structure = self.get_snippet("app_structure")
        cli_patterns = self.get_snippet("cli_patterns")
        export_system = self.get_snippet("export_system")
        storage_guide = self.get_snippet("storage_guide")

        # Simple variable substitution
        context = template.replace("{{app_name}}", app_name)
        context = context.replace("{{description}}", description)
        context = context.replace("{{app_structure}}", app_structure)
        context = context.replace("{{cli_patterns}}", cli_patterns)
        context = context.replace("{{export_system}}", export_system)
        context = context.replace("{{storage_guide}}", storage_guide)

        return context

    def get_snippet(self, name: str) -> str:
        """Get a reusable context snippet."""
        if name in self._snippet_cache:
            return self._snippet_cache[name]

        snippet_path = self.snippets_dir / f"{name}.md"

        if snippet_path.exists():
            content = snippet_path.read_text()
            self._snippet_cache[name] = content
            return content

        return f"[Snippet '{name}' not found]"

    def _get_available_apps_context(self) -> str:
        """Dynamically discover and format available apps and their exports."""

        apps_dir = Path("apps")
        if not apps_dir.exists():
            return "# Available Apps\n\nNo apps directory found."

        apps = []
        for app_path in apps_dir.iterdir():
            if not app_path.is_dir():
                continue

            app_name = app_path.name
            pyproject_path = app_path / "pyproject.toml"

            if pyproject_path.exists():
                try:
                    with open(pyproject_path, 'r') as f:
                        data = tomlkit.parse(f.read())

                    exports = []
                    if 'tool' in data and 'clanker' in data['tool'] and 'exports' in data['tool']['clanker']:
                        exports = list(data['tool']['clanker']['exports'].keys())

                    description = data.get('project', {}).get('description', f'{app_name} app')

                    apps.append({
                        'name': app_name,
                        'description': description,
                        'exports': exports
                    })
                except Exception:
                    # Skip apps with malformed pyproject.toml
                    continue

        if not apps:
            return "# Available Apps\n\nNo apps found in apps/ directory."

        context = "# Available Apps\n\n"
        for app in apps:
            context += f"## {app['name']}\n"
            context += f"- **Location**: `apps/{app['name']}/`\n"
            context += f"- **Description**: {app['description']}\n"
            if app['exports']:
                context += f"- **CLI Exports**: {', '.join(app['exports'])}\n"
                commands = [f'`clanker {app["name"]}_{export}`' for export in app['exports']]
                context += f"- **Commands**: {', '.join(commands)}\n"
            context += "\n"

        context += "## Development\n"
        context += "Create new apps in `apps/` directory with:\n"
        context += "- `main.py` with typer CLI\n"
        context += "- `pyproject.toml` with dependencies and exports\n"
        context += "- Isolated storage via Clanker storage system\n"

        return context
