"""Context snippet storage with custom override support."""

import os
from pathlib import Path
from typing import Optional


class ContextStore:
    """Manages context snippets with custom override capability."""
    
    def __init__(self, profile: Optional[str] = None):
        """Initialize the context store.
        
        Args:
            profile: Profile name for custom snippets (defaults to CLANKER_PROFILE env var or "default")
        """
        self.profile = profile or os.getenv("CLANKER_PROFILE", "default")
        self.builtin_dir = Path(__file__).parent / "snippets"
        self.custom_base = Path("data") / self.profile / "context"
    
    def get(self, key: str) -> Optional[str]:
        """Get a context snippet by key.
        
        Checks custom snippets first, then falls back to builtin.
        
        Args:
            key: Snippet key (e.g., "clanker_overview" or "clanker/overview")
            
        Returns:
            Snippet content or None if not found
        """
        # Normalize key: convert slashes to underscores for backward compatibility
        normalized_key = key.replace("/", "_")
        
        # Check custom snippets first
        custom_path = self.custom_base / f"{normalized_key}.md"
        if custom_path.exists():
            return custom_path.read_text()
        
        # Fall back to builtin snippets
        builtin_path = self.builtin_dir / f"{normalized_key}.md"
        if builtin_path.exists():
            return builtin_path.read_text()
        
        return None
    
    def list_snippets(self) -> dict[str, str]:
        """List all available snippets.
        
        Returns:
            Dict mapping snippet keys to their sources ("custom" or "builtin")
        """
        snippets = {}
        
        # Add builtin snippets
        if self.builtin_dir.exists():
            for path in self.builtin_dir.glob("*.md"):
                key = path.stem
                snippets[key] = "builtin"
        
        # Override with custom snippets
        if self.custom_base.exists():
            for path in self.custom_base.glob("*.md"):
                key = path.stem
                snippets[key] = "custom"
        
        return snippets