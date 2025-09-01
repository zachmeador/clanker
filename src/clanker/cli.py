"""Clanker CLI."""

import typer
from typing import Optional, List

from . import apps as apps_module
from .models import list_available_providers, list_available_models

app = typer.Typer(help="Clanker - LLM app environment")
apps = typer.Typer(help="Manage apps")
app.add_typer(apps, name="apps")


@apps.command("list")
def apps_list():
    """List available apps."""
    apps_module.list_apps()


@apps.command("run")
def apps_run(
    app_name: str = typer.Argument(..., help="App to run"),
    args: List[str] = typer.Argument(None, help="Arguments to pass to app")
):
    """Run an app."""
    raise typer.Exit(apps_module.run(app_name, args))


@app.command("run")
def run(
    app_name: str = typer.Argument(..., help="App to run"),
    args: List[str] = typer.Argument(None, help="Arguments to pass to app")
):
    """Run an app."""
    raise typer.Exit(apps_module.run(app_name, args))


@app.command()
def models():
    """Show available models."""
    providers = list_available_providers()
    if not providers:
        print("No API keys configured. Set these in .env:")
        print("  OPENAI_API_KEY=...")
        print("  ANTHROPIC_API_KEY=...")
        print("  GOOGLE_API_KEY=...")
        print("  GROQ_API_KEY=...")
        return
    
    print(f"Configured providers: {', '.join(providers)}")
    
    available = list_available_models()
    if available:
        print("\nAvailable models:")
        for provider, models in available.items():
            print(f"  {provider}:")
            for model in models:
                print(f"    - {model}")


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()