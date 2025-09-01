"""Clanker CLI with natural language support."""

import asyncio
import typer
from typing import Optional, List
from dataclasses import dataclass

from . import apps as apps_module
from .models import list_available_providers, list_available_models
from .agent import ClankerAgent
from .input_resolution import InputResolver
from .models import ModelTier
from .logger import get_logger

logger = get_logger("cli")

# Constants
VERSION = "0.1.0"
APP_NAME = "Clanker"

app = typer.Typer(help=f"{APP_NAME} - LLM app environment")
apps = typer.Typer(help="Manage apps")
app.add_typer(apps, name="apps")

# Help text
USAGE_TEXT = """{app_name} - LLM app environment

Usage:
  clanker [request]          - Natural language request
  clanker app list           - List available apps
  clanker run <app> [args]   - Run an app
  clanker launch <tool>      - Launch dev tool
  clanker models             - Show available models"""

LAUNCH_USAGE = "Usage: clanker launch <tool> [request]"
HELP_MESSAGE = "Use 'clanker --help' for help"


@dataclass
class AppState:
    """Simple state container for clanker CLI."""
    agent: Optional[ClankerAgent] = None
    resolver: Optional[InputResolver] = None

    def __post_init__(self):
        if self.resolver is None:
            self.resolver = InputResolver()

    def get_agent(self) -> ClankerAgent:
        """Get or create the agent instance."""
        if self.agent is None:
            logger.debug("Creating new ClankerAgent instance")
            self.agent = ClankerAgent()
            logger.debug("ClankerAgent created successfully")
        return self.agent


def create_app_state() -> AppState:
    """Create a new app state instance."""
    return AppState()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    args: List[str] = typer.Argument(None, help="Natural language request or command")
):
    """Main clanker command - handles natural language requests and commands."""
    if ctx.invoked_subcommand is not None:
        # Subcommand was invoked, let it handle
        return

    if not args:
        # No args provided, show help
        typer.echo(ctx.get_help())
        return

    # Create app state for this command execution
    state = create_app_state()

    # Resolve input type
    resolution = state.resolver.resolve(args)

    if resolution["type"] == "natural_language":
        # Handle as natural language request
        logger.info(f"Natural language request: '{resolution['request']}'")
        try:
            logger.debug("Getting agent instance")
            agent = state.get_agent()
            logger.debug("Calling agent.handle_request()")
            result = agent.handle_request(resolution["request"])
            logger.debug(f"Agent returned result: '{result[:100]}...'")
            typer.echo(result)
        except Exception as e:
            logger.error(f"CLI natural language handling failed: {str(e)}", exc_info=True)
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

    elif resolution["type"] == "app_command":
        # Handle as app command
        try:
            exit_code = apps_module.run(resolution["app_name"], resolution["args"])
            raise typer.Exit(exit_code)
        except Exception as e:
            typer.echo(f"Error running app: {e}", err=True)
            raise typer.Exit(1)

    elif resolution["type"] == "system_command":
        # Handle system commands
        handle_system_command(resolution["command"], resolution["args"], state)

    elif resolution["type"] == "flag_command":
        # Handle flags
        handle_flag_command(resolution["flag"], resolution["args"], state)

    else:
        # Fallback
        typer.echo(f"Unknown command type: {resolution['type']}")
        raise typer.Exit(1)


def handle_system_command(command: str, args: List[str], state: AppState):
    """Handle system commands."""
    if command == "launch":
        handle_launch_command(args, state)
    elif command in ["app", "apps"]:
        handle_app_command(args)
    elif command == "profile":
        handle_profile_command(args)
    elif command == "config":
        handle_config_command(args)
    elif command == "models":
        handle_models_command(args)
    elif command in ["help", "--help"]:
        typer.echo(HELP_MESSAGE)
    elif command in ["version", "--version"]:
        typer.echo(f"{APP_NAME} {VERSION}")
    else:
        typer.echo(f"Unknown system command: {command}")


def handle_launch_command(args: List[str], state: AppState):
    """Handle launch commands for dev tools."""
    if not args:
        typer.echo(LAUNCH_USAGE)
        return

    tool_name = args[0]
    request = " ".join(args[1:]) if len(args) > 1 else ""

    try:
        agent = state.get_agent()
        result = agent.handle_request(f"launch {tool_name} to {request}")
        typer.echo(result)
    except Exception as e:
        typer.echo(f"Error launching tool: {e}", err=True)


def handle_app_command(args: List[str]):
    """Handle app management commands."""
    if not args:
        apps_module.list_apps()
        return

    subcommand = args[0]
    if subcommand == "list":
        apps_module.list_apps()
    else:
        typer.echo(f"Unknown app command: {subcommand}")


def handle_profile_command(args: List[str]):
    """Handle profile commands."""
    typer.echo("Profile management not yet implemented")


def handle_config_command(args: List[str]):
    """Handle config commands."""
    typer.echo("Configuration management not yet implemented")


def handle_models_command(args: List[str]):
    """Handle models command."""
    # Reuse existing models command logic
    providers = list_available_providers()
    if not providers:
        typer.echo("No API keys configured. Set these in .env:")
        typer.echo("  OPENAI_API_KEY=...")
        typer.echo("  ANTHROPIC_API_KEY=...")
        typer.echo("  GOOGLE_API_KEY=...")
        typer.echo("  GROQ_API_KEY=...")
        typer.echo("  MISTRAL_API_KEY=...")
        return

    typer.echo(f"Configured providers: {', '.join(providers)}")

    available = list_available_models()
    if available:
        typer.echo("\nAvailable models:")
        for provider, models in available.items():
            typer.echo(f"  {provider}:")
            for model in models:
                typer.echo(f"    - {model}")


def handle_flag_command(flag: str, args: List[str], state: AppState):
    """Handle flag commands."""
    if flag in ["--help", "-h"]:
        typer.echo(USAGE_TEXT.format(app_name=APP_NAME))
    elif flag in ["--version", "-v"]:
        typer.echo(f"{APP_NAME} {VERSION}")
    else:
        typer.echo(f"Unknown flag: {flag}")


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
    handle_models_command([])


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()