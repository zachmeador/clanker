"""Clanker CLI with natural language support."""

import asyncio
import typer
from pathlib import Path
from typing import Optional, List, Annotated

from . import apps as apps_module
from .models import list_available_providers, list_available_models
from .agent import ClankerAgent
from .models import ModelTier
from .logger import get_logger
from .runtime import bootstrap_runtime_context

logger = get_logger("cli")

# Constants
VERSION = "0.1.0"
APP_NAME = "Clanker"

# Main app
app = typer.Typer(
    help=f"{APP_NAME} - LLM app environment",
    epilog="Examples: clanker app list | clanker system version | clanker claude \"help\" | clanker \"create todo app\"",
    context_settings={"help_option_names": ["-h", "--help"]}
)

# Subcommand groups with automatic help display
app_group = typer.Typer(
    help="App management commands",
    invoke_without_command=True,
    no_args_is_help=True
)
system_group = typer.Typer(
    help="System management commands",
    invoke_without_command=True,
    no_args_is_help=True
)

app.add_typer(app_group, name="app")
app.add_typer(system_group, name="system")

# Supported coding tools
CODING_TOOLS = {"claude", "cursor", "gemini", "codex"}

# Simple module-level instances - lazy initialized
_agent: Optional[ClankerAgent] = None

def get_agent() -> ClankerAgent:
    """Get or create the agent instance."""
    global _agent
    if _agent is None:
        logger.debug("Creating ClankerAgent instance")
        runtime = bootstrap_runtime_context()
        _agent = ClankerAgent(runtime=runtime)
        logger.debug("ClankerAgent created successfully")
    return _agent


def _bootstrap_startup() -> None:
    """Initialize required services and autostart enabled daemons."""
    try:
        runtime = bootstrap_runtime_context()
    except Exception as e:
        logger.error(f"Failed to bootstrap runtime context: {e}", exc_info=True)
        runtime = None

    try:
        if runtime is None:
            runtime = bootstrap_runtime_context()
        from .daemon import DaemonManager
        manager = DaemonManager(runtime=runtime)
        cleaned = manager.cleanup_stale_entries()
        if cleaned:
            logger.info(f"Cleaned {cleaned} stale daemon entries during startup")
        manager.start_enabled_daemons()
    except Exception as e:
        logger.error(f"Failed to start enabled daemons during startup: {e}", exc_info=True)


@app.callback()
def main(ctx: typer.Context):
    """Main entry point. Supports structured commands and natural language requests."""
    # Bootstrap shared services and autostart daemons on every CLI entry
    _bootstrap_startup()


@app.command(hidden=True)
def _console():
    """Launch interactive console (internal command)."""
    try:
        from .console import InteractiveConsole
        console = InteractiveConsole()
        asyncio.run(console.run())
    except KeyboardInterrupt:
        typer.echo("\nExiting...")
    except Exception as e:
        typer.echo(f"Error launching console: {e}", err=True)
        raise typer.Exit(1)


# Direct coding tool commands
@app.command()
def claude(
    request: Annotated[Optional[List[str]], typer.Argument(help="Request to pass to Claude")] = None
):
    """Launch Claude Code with context."""
    handle_coding_tool_command("claude", " ".join(request) if request else "")


@app.command()
def cursor(
    request: Annotated[Optional[List[str]], typer.Argument(help="Request to pass to Cursor")] = None
):
    """Launch Cursor-agent with context."""
    handle_coding_tool_command("cursor", " ".join(request) if request else "")


@app.command()
def gemini(
    request: Annotated[Optional[List[str]], typer.Argument(help="Request to pass to Gemini")] = None
):
    """Launch Gemini CLI with context."""
    handle_coding_tool_command("gemini", " ".join(request) if request else "")


@app.command()
def codex(
    request: Annotated[Optional[List[str]], typer.Argument(help="Request to pass to Codex")] = None
):
    """Launch OpenAI Codex CLI with context."""
    handle_coding_tool_command("codex", " ".join(request) if request else "")


def handle_coding_tool_command(tool_name: str, request: str):
    """Handle direct coding tool launch commands."""
    logger.info(f"Launching {tool_name} with request: '{request}'")

    from .tools import launch_coding_tool_cli
    try:
        err = launch_coding_tool_cli(tool_name, request)
        if err:
            typer.echo(err, err=True)
    except Exception as e:
        typer.echo(f"Launch failed: {e}", err=True)
        raise typer.Exit(1)


# App management commands
@app_group.command("list")
def app_list():
    """List available apps."""
    apps_module.list_apps()


@app_group.command("run")
def app_run(
    name: Annotated[str, typer.Argument(help="App name to run")],
    args: Annotated[Optional[List[str]], typer.Argument(help="Arguments to pass to the app")] = None
):
    """Run an app."""
    exit_code = apps_module.run(name, args or [])
    raise typer.Exit(exit_code)


@app_group.command("info")
def app_info(
    name: Annotated[str, typer.Argument(help="App name to show info for")]
):
    """Show app details."""
    discovered = apps_module.discover()
    app_info = discovered.get(name)
    if app_info:
        typer.echo(f"App: {name}")
        if app_info.get('description'):
            typer.echo(f"Description: {app_info['description']}")
        if app_info.get('exports'):
            typer.echo(f"CLI Exports: {', '.join(app_info['exports'])}")
        if app_info.get('entry'):
            typer.echo(f"Entry: {app_info['entry']}")
        if app_info.get('path'):
            typer.echo(f"Path: {app_info['path']}")
    else:
        typer.echo(f"App '{name}' not found")
        raise typer.Exit(1)


@app_group.command("scaffold")
def app_scaffold(
    name: Annotated[str, typer.Argument(help="App name to create")],
    description: Annotated[str, typer.Argument(help="App description")]
):
    """Create new app with guidance."""
    # Create app directory
    app_dir = Path(f"apps/{name}")
    if app_dir.exists():
        typer.echo(f"App directory apps/{name} already exists!", err=True)
        raise typer.Exit(1)

    try:
        app_dir.mkdir(parents=True)
        typer.echo(f"Created apps/{name}/")

        # Generate scaffold context
        from clanker.context.templates import app_scaffold_context
        instructions = app_scaffold_context(name, description)

        # Write INSTRUCTIONS.md
        instructions_file = app_dir / "INSTRUCTIONS.md"
        with open(instructions_file, "w") as f:
            f.write(instructions)

        typer.echo(f"Generated INSTRUCTIONS.md with scaffold guide")
        typer.echo(f"Next steps:")
        typer.echo(f"  cd apps/{name}")
        typer.echo(f"  Follow the instructions in INSTRUCTIONS.md")

    except Exception as e:
        typer.echo(f"Error creating scaffold: {e}", err=True)
        raise typer.Exit(1)


# System management commands
@system_group.command("models")
def system_models():
    """Show available AI models."""
    providers = list_available_providers()
    if not providers:
        typer.echo("No API keys configured. Set these in .env:")
        typer.echo("  OPENAI_API_KEY=...")
        typer.echo("  ANTHROPIC_API_KEY=...")
        typer.echo("  GOOGLE_API_KEY=...")
        return

    typer.echo(f"Configured providers: {', '.join(providers)}")

    available = list_available_models()
    if available:
        typer.echo("\nAvailable models:")
        for provider, models in available.items():
            typer.echo(f"  {provider}:")
            for model in models:
                typer.echo(f"    - {model}")


@system_group.command("profile")
def system_profile():
    """Manage profiles."""
    typer.echo("Profile management not yet implemented")


@system_group.command("config")
def system_config():
    """Configuration settings."""
    typer.echo("Configuration management not yet implemented")


@system_group.command("launch")
def system_launch(
    tool: Annotated[str, typer.Argument(help="Tool to launch (claude, cursor, gemini)")],
    app_name: Annotated[Optional[str], typer.Option("--app", help="App context to use")] = None,
    request: Annotated[Optional[str], typer.Option("--request", help="Request to pass to tool")] = None
):
    """Launch coding tools with advanced options."""
    if tool not in CODING_TOOLS:
        typer.echo(f"Unknown tool: {tool}")
        typer.echo(f"Available tools: {', '.join(CODING_TOOLS)}")
        raise typer.Exit(1)

    # Build query from args for consistency with agent approach
    query_parts = []
    if app_name:
        query_parts.append(f"working on {app_name}")
    if request:
        query_parts.append(request)
    query = " ".join(query_parts) if query_parts else ""

    # Use CLI variant to take over the process
    from .tools import launch_coding_tool_cli
    try:
        err = launch_coding_tool_cli(tool, query)
        if err:
            typer.echo(err, err=True)
            raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Launch failed: {e}", err=True)
        raise typer.Exit(1)


@system_group.command("build")
def system_build():
    """Build instruction files from snippets."""
    try:
        from .context import build_all_contexts

        # Build all contexts without query
        results = build_all_contexts()

        # Show results
        successful = [name for name, success in results.items() if success]
        failed = [name for name, success in results.items() if not success]

        if successful:
            typer.echo(f"✅ Successfully rebuilt: {', '.join(successful)}")

        if failed:
            typer.echo(f"❌ Failed to rebuild: {', '.join(failed)}", err=True)
            raise typer.Exit(1)

        if not successful and not failed:
            typer.echo("⚠️ No instruction files to rebuild")

    except Exception as e:
        typer.echo(f"❌ Rebuild failed: {e}", err=True)
        raise typer.Exit(1)


@system_group.command("setup")
def system_setup():
    """Show setup guidance for API keys and coding tools."""
    try:
        from .onboarding import show_setup_guidance, offer_env_creation

        # Show the setup guidance
        show_setup_guidance()

        # Offer to create .env file
        if offer_env_creation():
            typer.echo("You can now restart Clanker to use your configured API keys.")

    except KeyboardInterrupt:
        typer.echo("\nSetup interrupted")
    except Exception as e:
        typer.echo(f"Setup failed: {e}", err=True)
        raise typer.Exit(1)


@system_group.command("version")
def system_version():
    """Show version."""
    typer.echo(f"{APP_NAME} {VERSION}")


def main():
    """Entry point for the clanker CLI."""
    import sys
    import os

    # Check if no arguments provided - launch console
    if len(sys.argv) == 1:
        # Check if user needs onboarding (no API keys configured)
        try:
            from .onboarding import needs_onboarding, run_onboarding
            if needs_onboarding():
                run_onboarding()
                return
        except Exception as e:
            # If onboarding fails, continue to console
            logger.warning(f"Onboarding check failed: {e}")

        try:
            from .console import InteractiveConsole
            console = InteractiveConsole()
            asyncio.run(console.run())
        except KeyboardInterrupt:
            typer.echo("\nExiting...")
        except Exception as e:
            typer.echo(f"Error launching console: {e}", err=True)
            sys.exit(1)
        return

    # Pre-parse to decide natural language vs structured before invoking Typer
    known_entrypoints = {"app", "system", "claude", "cursor", "gemini", "codex", "_console"}
    if sys.argv[1] not in known_entrypoints and not any(x in sys.argv for x in ("-h", "--help", "help")):
        request_str = " ".join(sys.argv[1:])
        logger.info(f"Natural language fallback for: '{request_str}'")
        try:
            agent = get_agent()
            result = agent.handle_request(request_str)
            typer.echo(result['response'])
        except Exception as nl_error:
            logger.error(f"CLI natural language handling failed: {str(nl_error)}", exc_info=True)
            typer.echo(f"Error: {nl_error}", err=True)
            sys.exit(1)
        return

    # Otherwise, run the Typer app normally
    app()


if __name__ == "__main__":
    main()