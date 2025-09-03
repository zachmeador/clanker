"""Context builder for composing markdown documentation."""

from typing import List, Optional


class ContextBuilder:
    """Builds context documentation by composing sections."""
    
    def __init__(self):
        self.sections: List[str] = []
    
    def add(self, content: str, title: Optional[str] = None) -> 'ContextBuilder':
        """Add a content section with optional title.
        
        Args:
            content: The content to add
            title: Optional section title (will be formatted as markdown header)
            
        Returns:
            Self for method chaining
        """
        if title:
            section = f"## {title}\n\n{content}"
        else:
            section = content
            
        self.sections.append(section)
        return self
    
    def add_snippet(self, name: str) -> 'ContextBuilder':
        """Add a predefined snippet from the store.
        
        Args:
            name: Snippet key (e.g., "clanker/overview")
            
        Returns:
            Self for method chaining
        """
        from .store import ContextStore
        store = ContextStore()
        snippet = store.get(name)
        if snippet:
            self.sections.append(snippet)
        return self
    
    def build(self) -> str:
        """Build the final context document.
        
        Returns:
            Complete markdown document with all sections
        """
        return "\n\n".join(self.sections).strip()