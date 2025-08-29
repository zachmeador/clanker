"""Storage operations for recipe vault."""

from typing import Optional

import frontmatter
from loguru import logger
from clanker.storage.vault import Vault

from .models import LogEntry, RecipeContent, RecipeFrontmatter


class RecipeStorage:
    """Handle recipe storage in vault."""
    
    def __init__(self):
        """Initialize storage with vault."""
        self.vault = Vault.for_app("recipes")
        logger.info("Recipe storage initialized")
    
    def _recipe_path(self, name: str) -> str:
        """Get path for a recipe file."""
        if not name.endswith('.md'):
            name = f"{name}.md"
        return name
    
    def _normalize_name(self, name: str) -> str:
        """Normalize recipe name for filesystem."""
        return name.lower().replace(' ', '-').replace('/', '-')
    
    def exists(self, name: str) -> bool:
        """Check if recipe exists."""
        name = self._normalize_name(name)
        path = self._recipe_path(name)
        return self.vault.exists(path)
    
    def save(self, name: str, recipe: RecipeContent) -> str:
        """Save recipe to vault."""
        name = self._normalize_name(name)
        path = self._recipe_path(name)
        
        post = frontmatter.Post(
            content=recipe.content,
            **recipe.frontmatter.model_dump()
        )
        
        content = frontmatter.dumps(post)
        self.vault.write(path, content)
        
        logger.info(f"Saved recipe: {path}")
        return path
    
    def load(self, name: str) -> Optional[RecipeContent]:
        """Load recipe from vault."""
        name = self._normalize_name(name)
        path = self._recipe_path(name)
        
        if not self.vault.exists(path):
            return None
        
        content = self.vault.read(path)
        post = frontmatter.loads(content)
        
        return RecipeContent(
            frontmatter=RecipeFrontmatter(**post.metadata),
            content=post.content
        )
    
    def delete(self, name: str) -> bool:
        """Delete recipe from vault."""
        name = self._normalize_name(name)
        path = self._recipe_path(name)
        
        if self.vault.exists(path):
            self.vault.delete(path)
            logger.info(f"Deleted recipe: {path}")
            return True
        return False
    
    def list_recipes(self) -> list[str]:
        """List all recipe names."""
        files = self.vault.list()
        recipes = []
        for file in files:
            if file.endswith('.md'):
                recipes.append(file[:-3])  # Remove .md extension
        return sorted(recipes)
    
    def add_log(self, name: str, log_entry: LogEntry) -> bool:
        """Add log entry to recipe."""
        name = self._normalize_name(name)
        recipe = self.load(name)
        
        if not recipe:
            return False
        
        if not recipe.content.strip().endswith("## Log"):
            recipe.content += "\n\n## Log\n"
        
        recipe.content += f"\n**{log_entry.date}**: {log_entry.note}"
        
        self.save(name, recipe)
        return True
    
    def grep(self, search_term: str) -> list[str]:
        """Search recipes for a term and return matching recipe names."""
        search_term = search_term.lower()
        matches = []
        
        for recipe_file in self.list_recipes():
            recipe = self.load(recipe_file)
            if recipe:
                # Search in title
                if search_term in recipe.frontmatter.title.lower():
                    matches.append(recipe_file)
                    continue
                
                # Search in tags
                if any(search_term in tag.lower() for tag in recipe.frontmatter.tags):
                    matches.append(recipe_file)
                    continue
                
                # Search in content
                if search_term in recipe.content.lower():
                    matches.append(recipe_file)
                    continue
        
        return sorted(matches)