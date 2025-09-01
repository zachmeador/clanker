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

# Help text
USAGE_TEXT = """{app_name} - LLM app environment

Usage:
  clanker                    - Launch interactive console
  clanker [request]          - Natural language request (one-shot)
  clanker app <command>      - App management
  clanker system <command>   - System management

App Commands:
  clanker app list           - List available apps
  clanker app run <name>     - Run an app
  clanker app info <name>    - Show app details

System Commands:
  clanker system models      - Show available AI models
  clanker system profile     - Manage profiles
  clanker system config      - Configuration settings
  clanker system help        - Show help
  clanker system version     - Show version"""

HELP_MESSAGE = "Use 'clanker system help' for help"


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
        # No args provided, launch interactive console
        try:
            from .console import InteractiveConsole
            console = InteractiveConsole()
            asyncio.run(console.run())
        except KeyboardInterrupt:
            typer.echo("\nExiting...")
        except Exception as e:
            typer.echo(f"Error launching console: {e}", err=True)
            raise typer.Exit(1)
        return

    # Create app state for this command execution
    state = create_app_state()

    # Resolve input type
    resolution = state.resolver.resolve(args)

    if resolution["type"] == "system_command":
        # Handle system or app commands
        command = resolution["command"]
        if command == "system":
            handle_system_command(resolution["args"], state)
        elif command == "app":
            handle_app_command(resolution["args"], state)
        else:
            typer.echo(f"Unknown command: {command}")
            raise typer.Exit(1)

    elif resolution["type"] == "natural_language":
        # Handle as natural language request (one-shot)
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

    else:
        # Fallback
        typer.echo(f"Unknown command type: {resolution['type']}")
        raise typer.Exit(1)


def handle_system_command(args: List[str], state: AppState):
    """Handle system commands."""
    if not args:
        typer.echo("System commands: models, profile, config, help, version")
        return
    
    subcommand = args[0]
    sub_args = args[1:] if len(args) > 1 else []
    
    if subcommand == "models":
        handle_models_command(sub_args)
    elif subcommand == "profile":
        handle_profile_command(sub_args)
    elif subcommand == "config":
        handle_config_command(sub_args)
    elif subcommand == "help":
        typer.echo(USAGE_TEXT.format(app_name=APP_NAME))
    elif subcommand == "version":
        typer.echo(f"{APP_NAME} {VERSION}")
    else:
        typer.echo(f"Unknown system command: {subcommand}")
        typer.echo("Available: models, profile, config, help, version")


def handle_app_command(args: List[str], state: AppState):
    """Handle app management commands."""
    if not args:
        typer.echo("App commands: list, run <name>, info <name>")
        return
    
    subcommand = args[0]
    sub_args = args[1:] if len(args) > 1 else []
    
    if subcommand == "list":
        apps_module.list_apps()
    elif subcommand == "run":
        if not sub_args:
            typer.echo("Usage: clanker app run <name> [args]")
            return
        app_name = sub_args[0]
        app_args = sub_args[1:] if len(sub_args) > 1 else []
        exit_code = apps_module.run(app_name, app_args)
        raise typer.Exit(exit_code)
    elif subcommand == "info":
        if not sub_args:
            typer.echo("Usage: clanker app info <name>")
            return
        app_name = sub_args[0]
        # Get app info from resolver
        app_info = state.resolver.get_app_info(app_name)
        if app_info:
            typer.echo(f"App: {app_name}")
            if app_info.get('description'):
                typer.echo(f"Description: {app_info['description']}")
            if app_info.get('commands'):
                typer.echo(f"Commands: {', '.join(app_info['commands'])}")
        else:
            typer.echo(f"App '{app_name}' not found")
    else:
        typer.echo(f"Unknown app command: {subcommand}")
        typer.echo("Available: list, run, info")


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




# Remove old typer commands - everything goes through main now


def main():
    """Entry point."""
    app()


if __name__ == "__main__":
    main()