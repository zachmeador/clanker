"""Simple context builder for composing markdown sections."""

from pathlib import Path
from typing import List, Optional


class ContextBuilder:
    """Simple builder for composing markdown context documents."""
    
    def __init__(self):
        self.sections: List[str] = []
        self.snippets_dir = Path(__file__).parent / "snippets"
    
    def add(self, content: str, title: Optional[str] = None) -> 'ContextBuilder':
        """Add content with optional title."""
        if title:
            self.sections.append(f"# {title}\n\n{content}")
        else:
            self.sections.append(content)
        return self
    
    def add_snippet(self, name: str) -> 'ContextBuilder':
        """Add content from a snippet file."""
        snippet_path = self.snippets_dir / f"{name}.md"
        try:
            content = snippet_path.read_text().strip()
            self.sections.append(content)
        except FileNotFoundError:
            pass  # Skip missing snippets silently
        return self
    
    def build(self) -> str:
        """Build the final markdown document."""
        return "\n\n".join(self.sections).strip()
    
    def clear(self) -> 'ContextBuilder':
        """Clear all sections."""
        self.sections.clear()
        return self