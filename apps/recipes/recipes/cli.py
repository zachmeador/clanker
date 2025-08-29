"""CLI for recipe management using typer."""

import os
import sys
from datetime import datetime
from typing import Optional

import typer
from dotenv import load_dotenv
from loguru import logger
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from rich.console import Console
from rich.markdown import Markdown

from .models import LogEntry, RecipeContent
from .storage import RecipeStorage

load_dotenv()

logger.remove()
logger.add(sys.stderr, level="INFO")

app = typer.Typer(help="Simple recipe manager")
console = Console()
storage = RecipeStorage()


def get_recipe_agent() -> Agent[None, RecipeContent]:
    """Create agent for parsing recipes."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    
    # Try to load from clanker config if not in env
    if not api_key:
        try:
            from pathlib import Path
            import sys
            # Add parent dir to path to import clanker
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from clanker.config import ClankerConfig
            config = ClankerConfig.load()
            api_key = config.api_keys.anthropic
        except ImportError:
            pass
    
    if not api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not found in environment or clanker config[/red]")
        raise typer.Exit(1)
    
    model = AnthropicModel("claude-3-5-sonnet-latest", api_key=api_key)
    
    return Agent(
        model,
        output_type=RecipeContent,
        system_prompt="""You are a recipe parser. Extract recipe information and format it properly.
        
        The frontmatter should contain:
        - title: Recipe name
        - servings: Number of servings
        - prep_time: Prep time in minutes (if mentioned)
        - cook_time: Cook time in minutes (if mentioned)
        - tags: List of relevant tags (cuisine type, meal type, dietary, etc)
        - source: Where the recipe came from (if mentioned)
        
        The content should be well-formatted markdown with:
        - Ingredients section
        - Instructions section
        - Any notes or tips
        
        Format ingredients as a bulleted list.
        Format instructions as numbered steps."""
    )


@app.command()
def add(
    recipe_text: str = typer.Argument(..., help="Recipe text to parse"),
    name: Optional[str] = typer.Option(None, "--name", help="Recipe name (defaults to title from recipe)")
):
    """Add a new recipe from text."""
    agent = get_recipe_agent()
    
    with console.status("[yellow]Parsing recipe...[/yellow]"):
        result = agent.run_sync(recipe_text)
        recipe = result.output
    
    recipe_name = name or recipe.frontmatter.title
    
    if storage.exists(recipe_name):
        console.print(f"[red]Recipe '{recipe_name}' already exists. Use 'replace' to update it.[/red]")
        raise typer.Exit(1)
    
    path = storage.save(recipe_name, recipe)
    console.print(f"[green]✓[/green] Added recipe: {recipe_name}")
    console.print(f"  Saved to: {path}")


@app.command()
def replace(
    name: str = typer.Argument(..., help="Recipe name to replace"),
    recipe_text: str = typer.Argument(..., help="New recipe text")
):
    """Replace an existing recipe."""
    if not storage.exists(name):
        console.print(f"[red]Recipe '{name}' not found. Use 'add' to create it.[/red]")
        raise typer.Exit(1)
    
    agent = get_recipe_agent()
    
    with console.status("[yellow]Parsing recipe...[/yellow]"):
        result = agent.run_sync(recipe_text)
        recipe = result.output
    
    path = storage.save(name, recipe)
    console.print(f"[green]✓[/green] Replaced recipe: {name}")
    console.print(f"  Saved to: {path}")


@app.command()
def delete(name: str = typer.Argument(..., help="Recipe name to delete")):
    """Delete a recipe."""
    if storage.delete(name):
        console.print(f"[green]✓[/green] Deleted recipe: {name}")
    else:
        console.print(f"[red]Recipe '{name}' not found.[/red]")
        raise typer.Exit(1)


@app.command()
def log(
    name: str = typer.Argument(..., help="Recipe name"),
    note: str = typer.Argument(..., help="Note about making the recipe"),
    date: Optional[str] = typer.Option(None, "--date", help="Date when you made it (YYYY-MM-DD). Defaults to today.")
):
    """Log when you made a recipe and thoughts."""
    if date:
        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
            log_entry = LogEntry(date=date, note=note)
        except ValueError:
            console.print("[red]Error: Date must be in YYYY-MM-DD format[/red]")
            raise typer.Exit(1)
    else:
        log_entry = LogEntry(note=note)
    
    if storage.add_log(name, log_entry):
        console.print(f"[green]✓[/green] Added log to recipe: {name}")
        console.print(f"  {log_entry.date}: {note}")
    else:
        console.print(f"[red]Recipe '{name}' not found.[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_recipes():
    """List all recipes."""
    recipes = storage.list_recipes()
    
    if not recipes:
        console.print("[yellow]No recipes found.[/yellow]")
        return
    
    console.print("[bold]Recipes:[/bold]")
    for recipe in recipes:
        console.print(f"  • {recipe}")


@app.command()
def grep(search_term: str = typer.Argument(..., help="Term to search for")):
    """Search recipes for a term."""
    matches = storage.grep(search_term)
    
    if not matches:
        console.print(f"[yellow]No recipes found matching '{search_term}'[/yellow]")
        return
    
    console.print(f"[bold]Recipes matching '{search_term}':[/bold]")
    for recipe in matches:
        console.print(f"  • {recipe}")


@app.command()
def show(name: str = typer.Argument(..., help="Recipe name to show")):
    """Show a recipe."""
    recipe = storage.load(name)
    
    if not recipe:
        console.print(f"[red]Recipe '{name}' not found.[/red]")
        raise typer.Exit(1)
    
    # Build markdown content
    content = f"# {recipe.frontmatter.title}\n\n"
    content += f"**Servings:** {recipe.frontmatter.servings}\n"
    
    if recipe.frontmatter.prep_time:
        content += f"**Prep:** {recipe.frontmatter.prep_time} min\n"
    if recipe.frontmatter.cook_time:
        content += f"**Cook:** {recipe.frontmatter.cook_time} min\n"
    
    if recipe.frontmatter.tags:
        content += f"**Tags:** {', '.join(recipe.frontmatter.tags)}\n"
    
    content += "\n" + recipe.content
    
    console.print(Markdown(content))


if __name__ == "__main__":
    app()