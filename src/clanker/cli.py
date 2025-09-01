"""Clanker CLI with natural language support."""

import asyncio
import typer
from typing import Optional, List

from . import apps as apps_module
from .models import list_available_providers, list_available_models
from .agent import ClankerAgent
from .input_resolution import InputResolver
from .models import ModelTier
from .logger import get_logger

logger = get_logger("cli")

app = typer.Typer(help="Clanker - LLM app environment")
apps = typer.Typer(help="Manage apps")
app.add_typer(apps, name="apps")

# Global agent instance
_agent: Optional[ClankerAgent] = None
_resolver = InputResolver()

def get_agent() -> ClankerAgent:
    """Get or create the global agent instance."""
    global _agent
    if _agent is None:
        logger.debug("Creating new ClankerAgent instance")
        _agent = ClankerAgent()
        logger.debug("ClankerAgent created successfully")
    return _agent


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

    # Resolve input type
    resolution = _resolver.resolve(args)

    if resolution["type"] == "natural_language":
        # Handle as natural language request
        logger.info(f"Natural language request: '{resolution['request']}'")
        try:
            logger.debug("Getting agent instance")
            agent = get_agent()
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
        handle_system_command(resolution["command"], resolution["args"])

    elif resolution["type"] == "flag_command":
        # Handle flags
        handle_flag_command(resolution["flag"], resolution["args"])

    else:
        # Fallback
        typer.echo(f"Unknown command type: {resolution['type']}")
        raise typer.Exit(1)


def handle_system_command(command: str, args: List[str]):
    """Handle system commands."""
    if command == "launch":
        handle_launch_command(args)
    elif command in ["app", "apps"]:
        handle_app_command(args)
    elif command == "profile":
        handle_profile_command(args)
    elif command == "config":
        handle_config_command(args)
    elif command == "models":
        handle_models_command(args)
    elif command in ["help", "--help"]:
        typer.echo("Use 'clanker --help' for help")
    elif command in ["version", "--version"]:
        typer.echo("Clanker v0.1.0")
    else:
        typer.echo(f"Unknown system command: {command}")


def handle_launch_command(args: List[str]):
    """Handle launch commands for dev tools."""
    if not args:
        typer.echo("Usage: clanker launch <tool> [request]")
        return

    tool_name = args[0]
    request = " ".join(args[1:]) if len(args) > 1 else ""

    try:
        agent = get_agent()
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


def handle_flag_command(flag: str, args: List[str]):
    """Handle flag commands."""
    if flag in ["--help", "-h"]:
        typer.echo("Clanker - LLM app environment")
        typer.echo("\nUsage:")
        typer.echo("  clanker [request]          - Natural language request")
        typer.echo("  clanker app list           - List available apps")
        typer.echo("  clanker run <app> [args]   - Run an app")
        typer.echo("  clanker launch <tool>      - Launch dev tool")
        typer.echo("  clanker models             - Show available models")
    elif flag in ["--version", "-v"]:
        typer.echo("Clanker v0.1.0")
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