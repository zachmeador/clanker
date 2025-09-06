"""Pydantic models for recipe data validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class RecipeFrontmatter(BaseModel):
    """Strongly validated recipe frontmatter."""
    
    title: str = Field(..., description="Recipe title")
    servings: int = Field(..., description="Number of servings")
    prep_time: Optional[int] = Field(None, description="Prep time in minutes")
    cook_time: Optional[int] = Field(None, description="Cook time in minutes")
    tags: list[str] = Field(default_factory=list, description="Recipe tags")
    source: Optional[str] = Field(None, description="Where the recipe came from")
    created: str = Field(default_factory=lambda: datetime.now().isoformat())


class RecipeContent(BaseModel):
    """Full recipe with frontmatter and markdown content."""
    
    frontmatter: RecipeFrontmatter
    content: str = Field(..., description="Markdown recipe content")


class LogEntry(BaseModel):
    """Entry for logging when recipe was made and thoughts."""
    
    date: str = Field(default_factory=lambda: datetime.now().date().isoformat())
    note: str = Field(..., description="Thoughts on the recipe")