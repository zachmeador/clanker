"""Context storage and file management."""

from pathlib import Path
from typing import Dict, Optional


class ContextStore:
    """Manages context files for different CLI tools."""
    
    # Mapping of tools to their expected instruction files
    TOOL_FILES = {
        "claude": "CLAUDE.md",
        "cursor": "AGENTS.md", 
        "gemini": "GEMINI.md",
    }
    
    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            # Find project root by looking for pyproject.toml
            current = Path(__file__).resolve()
            while current.parent != current:
                if (current / "pyproject.toml").exists():
                    project_root = current
                    break
                current = current.parent
            else:
                project_root = Path.cwd()
        
        self.project_root = Path(project_root)
    
    def write_all(self, content: str) -> Dict[str, bool]:
        """Write context to all tool files."""
        results = {}
        
        # Always write INSTRUCTIONS.md as master file
        instructions_path = self.project_root / "INSTRUCTIONS.md"
        results["INSTRUCTIONS.md"] = self._write_file(instructions_path, content)
        
        # Write tool-specific files
        for tool_name, filename in self.TOOL_FILES.items():
            file_path = self.project_root / filename
            results[filename] = self._write_file(file_path, content)
        
        return results
    
    def write_for_tool(self, tool: str, content: str) -> bool:
        """Write context for a specific tool."""
        filename = self.TOOL_FILES.get(tool, self.TOOL_FILES["generic"])
        file_path = self.project_root / filename
        return self._write_file(file_path, content)
    
    def _write_file(self, path: Path, content: str) -> bool:
        """Write content to file, return success status."""
        try:
            path.write_text(content)
            return True
        except Exception:
            return False