"""Clanker CLI with natural language support."""

import asyncio
import typer
from pathlib import Path
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
  clanker <tool> [request]   - Launch coding tool directly (claude, cursor, gemini)
  clanker app <command>      - App management
  clanker system <command>   - System management

Coding Tools:
  clanker claude [request]   - Launch Claude Code with context
  clanker cursor [request]   - Launch Cursor-agent with context  
  clanker gemini [request]   - Launch Gemini CLI with context

App Commands:
  clanker app list           - List available apps
  clanker app run <name>     - Run an app
  clanker app info <name>    - Show app details
  clanker app scaffold       - Create new app with guidance

System Commands:
  clanker system models      - Show available AI models
  clanker system profile     - Manage profiles
  clanker system config      - Configuration settings
  clanker system launch      - Launch coding tools with advanced options
  clanker system help        - Show help
  clanker system version     - Show version"""

HELP_MESSAGE = "Use 'clanker system help' for help"


# Supported coding tools
CODING_TOOLS = {"claude", "cursor", "gemini"}

# Simple module-level instances - lazy initialized
_agent: Optional[ClankerAgent] = None
_resolver = InputResolver()

def get_agent() -> ClankerAgent:
    """Get or create the agent instance."""
    global _agent
    if _agent is None:
        logger.debug("Creating ClankerAgent instance")
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

    # Check if first argument is a coding tool
    if args[0].lower() in CODING_TOOLS:
        tool_name = args[0].lower()
        request = " ".join(args[1:]) if len(args) > 1 else "general development work"
        handle_coding_tool_command(tool_name, request)
        return

    # Resolve input type for other commands
    resolution = _resolver.resolve(args)

    if resolution["type"] == "system_command":
        # Handle system or app commands
        command = resolution["command"]
        if command == "system":
            handle_system_command(resolution["args"])
        elif command == "app":
            handle_app_command(resolution["args"])
        else:
            typer.echo(f"Unknown command: {command}")
            raise typer.Exit(1)

    elif resolution["type"] == "natural_language":
        # Handle as natural language request (one-shot)
        logger.info(f"Natural language request: '{resolution['request']}'")
        try:
            logger.debug("Getting agent instance")
            agent = get_agent()
            logger.debug("Calling agent.handle_request()")
            result = agent.handle_request(resolution["request"])
            logger.debug(f"Agent returned result: '{result['response'][:100]}...'")
            typer.echo(result['response'])
        except Exception as e:
            logger.error(f"CLI natural language handling failed: {str(e)}", exc_info=True)
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1)

    else:
        # Fallback
        typer.echo(f"Unknown command type: {resolution['type']}")
        raise typer.Exit(1)


def handle_coding_tool_command(tool_name: str, request: str):
    """Handle direct coding tool launch commands."""
    logger.info(f"Launching {tool_name} with request: '{request}'")
    
    from .tools import launch_coding_tool
    try:
        result = launch_coding_tool(tool_name, request)
        # If we get here, launch failed - show error
        if result and result.startswith("❌"):
            typer.echo(result, err=True)
    except Exception as e:
        typer.echo(f"Launch failed: {e}", err=True)
        raise typer.Exit(1)


def handle_system_command(args: List[str]):
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
    elif subcommand == "launch":
        handle_launch_command(sub_args)
    elif subcommand == "help":
        typer.echo(USAGE_TEXT.format(app_name=APP_NAME))
    elif subcommand == "version":
        typer.echo(f"{APP_NAME} {VERSION}")
    else:
        typer.echo(f"Unknown system command: {subcommand}")
        typer.echo("Available: models, profile, config, launch, help, version")


def handle_app_command(args: List[str]):
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
        # Get app info from apps module
        from . import apps as apps_module
        discovered = apps_module.discover()
        app_info = discovered.get(app_name)
        if app_info:
            typer.echo(f"App: {app_name}")
            if app_info.get('description'):
                typer.echo(f"Description: {app_info['description']}")
            if app_info.get('exports'):
                typer.echo(f"CLI Exports: {', '.join(app_info['exports'])}")
            if app_info.get('entry'):
                typer.echo(f"Entry: {app_info['entry']}")
            if app_info.get('path'):
                typer.echo(f"Path: {app_info['path']}")
        else:
            typer.echo(f"App '{app_name}' not found")
    elif subcommand == "scaffold":
        if len(sub_args) < 2:
            typer.echo("Usage: clanker app scaffold <name> <description>")
            return
        app_name = sub_args[0]
        description = " ".join(sub_args[1:])
        handle_scaffold_command(app_name, description)
    else:
        typer.echo(f"Unknown app command: {subcommand}")
        typer.echo("Available: list, run, info, scaffold")


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


def handle_launch_command(args: List[str]):
    """Handle launch command for coding tools."""
    if not args:
        typer.echo("Usage: clanker system launch <tool> [--app <app_name>] [--request <request>]")
        typer.echo("Tools: claude, cursor, gemini")
        return

    tool_name = args[0]
    app_name = None
    user_request = None

    # Parse optional args
    i = 1
    while i < len(args):
        if args[i] == "--app" and i + 1 < len(args):
            app_name = args[i + 1]
            i += 2
        elif args[i] == "--request" and i + 1 < len(args):
            user_request = " ".join(args[i + 1:])
            break
        else:
            i += 1

    # Build query from args for consistency with agent approach
    query_parts = []
    if app_name:
        query_parts.append(f"working on {app_name}")
    if user_request:
        query_parts.append(user_request)
    query = " ".join(query_parts) if query_parts else "general development work"

    # Use the same launch tool as the agent
    from .tools import launch_coding_tool
    try:
        result = launch_coding_tool(tool_name, query)
        # If we get here, launch failed - show error
        if result and result.startswith("❌"):
            typer.echo(result, err=True)
    except Exception as e:
        typer.echo(f"Launch failed: {e}", err=True)


def handle_scaffold_command(app_name: str, description: str):
    """Handle scaffold command for new apps."""
    # Create app directory
    app_dir = Path(f"apps/{app_name}")
    if app_dir.exists():
        typer.echo(f"App directory apps/{app_name} already exists!", err=True)
        return

    try:
        app_dir.mkdir(parents=True)
        typer.echo(f"Created apps/{app_name}/")

        # Generate scaffold context
        from clanker.context.templates import app_scaffold_context
        instructions = app_scaffold_context(app_name, description)

        # Write INSTRUCTIONS.md
        instructions_file = app_dir / "INSTRUCTIONS.md"
        with open(instructions_file, "w") as f:
            f.write(instructions)

        typer.echo(f"Generated INSTRUCTIONS.md with scaffold guide")
        typer.echo(f"Next steps:")
        typer.echo(f"  cd apps/{app_name}")
        typer.echo(f"  Follow the instructions in INSTRUCTIONS.md")

    except Exception as e:
        typer.echo(f"Error creating scaffold: {e}", err=True)


# Remove old typer commands - everything goes through main now


def main():
    """Entry point for the clanker CLI."""
    app()


if __name__ == "__main__":
    main()

