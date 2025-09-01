"""Exported functions for the recipes app."""

from datetime import datetime
from typing import List, Optional
from rich.console import Console
from rich.markdown import Markdown

from clanker.exports import export, ExportType
from clanker.logger import get_logger
from clanker.models import create_agent
from pydantic_ai import Agent

from .models import LogEntry, RecipeContent
from .storage import RecipeStorage

logger = get_logger("recipes")
console = Console()
storage = RecipeStorage()


def get_recipe_agent() -> Agent[None, RecipeContent]:
    """Create agent for parsing recipes using clanker model conventions."""
    try:
        return create_agent(
            "anthropic:claude-3-5-sonnet-latest",
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
    except Exception as e:
        console.print(f"[red]Error creating model agent: {e}[/red]")
        raise


@export(
    name="add_recipe",
    description="Add a new recipe from text",
    export_type=ExportType.BOTH,
    cli_path="add"
)
def add_recipe(
    recipe_text: str,
    name: Optional[str] = None
) -> str:
    """
    Add a new recipe from text.

    Args:
        recipe_text: The recipe text to parse
        name: Optional custom name for the recipe

    Returns:
        Success message with recipe details
    """
    agent = get_recipe_agent()

    with console.status("[yellow]Parsing recipe...[/yellow]"):
        result = agent.run_sync(recipe_text)
        recipe = result.output

    recipe_name = name or recipe.frontmatter.title

    if storage.exists(recipe_name):
        error_msg = f"Recipe '{recipe_name}' already exists. Use 'replace_recipe' to update it."
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    path = storage.save(recipe_name, recipe)
    success_msg = f"✓ Added recipe: {recipe_name} (saved to: {path})"
    console.print(f"[green]{success_msg}[/green]")
    return success_msg


@export(
    name="replace_recipe",
    description="Replace an existing recipe with new content",
    export_type=ExportType.BOTH,
    cli_path="replace"
)
def replace_recipe(
    name: str,
    recipe_text: str
) -> str:
    """
    Replace an existing recipe.

    Args:
        name: Name of the recipe to replace
        recipe_text: New recipe text

    Returns:
        Success message
    """
    if not storage.exists(name):
        error_msg = f"Recipe '{name}' not found. Use 'add_recipe' to create it."
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

    agent = get_recipe_agent()

    with console.status("[yellow]Parsing recipe...[/yellow]"):
        result = agent.run_sync(recipe_text)
        recipe = result.output

    path = storage.save(name, recipe)
    success_msg = f"✓ Replaced recipe: {name} (saved to: {path})"
    console.print(f"[green]{success_msg}[/green]")
    return success_msg


@export(
    name="delete_recipe",
    description="Delete a recipe",
    export_type=ExportType.BOTH,
    cli_path="delete"
)
def delete_recipe(name: str) -> str:
    """
    Delete a recipe.

    Args:
        name: Name of the recipe to delete

    Returns:
        Success message
    """
    if storage.delete(name):
        success_msg = f"✓ Deleted recipe: {name}"
        console.print(f"[green]{success_msg}[/green]")
        return success_msg
    else:
        error_msg = f"Recipe '{name}' not found."
        console.print(f"[red]{error_msg}[/red]")
        return error_msg


@export(
    name="log_recipe",
    description="Log when you made a recipe and add notes",
    export_type=ExportType.BOTH,
    cli_path="log"
)
def log_recipe(
    name: str,
    note: str,
    date: Optional[str] = None
) -> str:
    """
    Log when you made a recipe and thoughts.

    Args:
        name: Recipe name
        note: Note about making the recipe
        date: Optional date in YYYY-MM-DD format (defaults to today)

    Returns:
        Success message
    """
    if date:
        # Validate date format
        try:
            datetime.strptime(date, '%Y-%m-%d')
            log_entry = LogEntry(date=date, note=note)
        except ValueError:
            error_msg = "Date must be in YYYY-MM-DD format"
            console.print(f"[red]{error_msg}[/red]")
            return error_msg
    else:
        log_entry = LogEntry(note=note)

    if storage.add_log(name, log_entry):
        success_msg = f"✓ Added log to recipe: {name} ({log_entry.date}: {note})"
        console.print(f"[green]{success_msg}[/green]")
        return success_msg
    else:
        error_msg = f"Recipe '{name}' not found."
        console.print(f"[red]{error_msg}[/red]")
        return error_msg


@export(
    name="list_recipes",
    description="List all recipe names",
    export_type=ExportType.BOTH,
    cli_path="list"
)
def list_recipes() -> str:
    """
    List all recipes.

    Returns:
        Formatted list of recipes
    """
    recipes = storage.list_recipes()

    if not recipes:
        msg = "No recipes found."
        console.print(f"[yellow]{msg}[/yellow]")
        return msg

    console.print("[bold]Recipes:[/bold]")
    for recipe in recipes:
        console.print(f"  • {recipe}")

    return f"Found {len(recipes)} recipes: {', '.join(recipes)}"


@export(
    name="search_recipes",
    description="Search recipes by content, title, or tags",
    export_type=ExportType.BOTH,
    cli_path="grep"
)
def search_recipes(search_term: str) -> str:
    """
    Search recipes for a term.

    Args:
        search_term: Term to search for

    Returns:
        List of matching recipes
    """
    matches = storage.grep(search_term)

    if not matches:
        msg = f"No recipes found matching '{search_term}'"
        console.print(f"[yellow]{msg}[/yellow]")
        return msg

    console.print(f"[bold]Recipes matching '{search_term}':[/bold]")
    for recipe in matches:
        console.print(f"  • {recipe}")

    return f"Found {len(matches)} recipes: {', '.join(matches)}"


@export(
    name="show_recipe",
    description="Display a recipe with formatting",
    export_type=ExportType.BOTH,
    cli_path="show"
)
def show_recipe(name: str) -> str:
    """
    Show a recipe with formatting.

    Args:
        name: Recipe name to show

    Returns:
        Formatted recipe content
    """
    recipe = storage.load(name)

    if not recipe:
        error_msg = f"Recipe '{name}' not found."
        console.print(f"[red]{error_msg}[/red]")
        return error_msg

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
    return content


@export(
    name="get_recipe_summary",
    description="Get a brief summary of a recipe",
    export_type=ExportType.TOOL  # CLI only - not exposed as tool
)
def get_recipe_summary(name: str) -> str:
    """
    Get a brief summary of a recipe (for agent use).

    Args:
        name: Recipe name

    Returns:
        Brief recipe summary
    """
    recipe = storage.load(name)

    if not recipe:
        return f"Recipe '{name}' not found."

    summary = f"{recipe.frontmatter.title} (serves {recipe.frontmatter.servings})"

    if recipe.frontmatter.tags:
        summary += f" - Tags: {', '.join(recipe.frontmatter.tags)}"

    if recipe.frontmatter.prep_time or recipe.frontmatter.cook_time:
        times = []
        if recipe.frontmatter.prep_time:
            times.append(f"Prep: {recipe.frontmatter.prep_time}min")
        if recipe.frontmatter.cook_time:
            times.append(f"Cook: {recipe.frontmatter.cook_time}min")
        summary += f" - {', '.join(times)}"

    return summary


@export(
    name="get_random_recipe",
    description="Get a random recipe suggestion",
    export_type=ExportType.TOOL  # Tool only - not exposed as CLI
)
def get_random_recipe() -> str:
    """
    Get a random recipe suggestion.

    Returns:
        Recipe name and brief info
    """
    import random

    recipes = storage.list_recipes()
    if not recipes:
        return "No recipes available."

    random_recipe = random.choice(recipes)
    return get_recipe_summary(random_recipe)
