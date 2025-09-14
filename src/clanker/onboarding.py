"""Onboarding system for first-time Clanker users."""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .models import _get_available_providers
from .logger import get_logger

logger = get_logger("onboarding")
console = Console()


def check_api_keys() -> Tuple[List[str], List[str]]:
    """Check which API keys are configured.

    Returns:
        Tuple of (configured_providers, missing_providers)
    """
    providers = _get_available_providers()
    configured = []
    missing = []

    for provider, key in providers.items():
        if key and key.strip():
            configured.append(provider)
        else:
            missing.append(provider)

    return configured, missing


def check_coding_tools() -> Dict[str, bool]:
    """Check which coding CLI tools are installed.

    Returns:
        Dict mapping tool names to availability
    """
    tools = {
        "claude": "claude",
        "cursor": "cursor-agent",
        "gemini": "gemini",
        "codex": "codex"
    }

    availability = {}
    for tool_name, command in tools.items():
        availability[tool_name] = shutil.which(command) is not None

    return availability


def needs_onboarding() -> bool:
    """Check if user needs onboarding.

    Returns True if no API keys are configured.
    """
    configured, missing = check_api_keys()

    # User needs onboarding if no providers are configured
    return len(configured) == 0


def show_setup_guidance() -> None:
    """Display comprehensive setup guidance."""
    console.print()

    # Welcome header
    welcome_text = """
[bold cyan]Welcome to Clanker![/bold cyan]

Clanker is an LLM application framework that helps you build and manage AI-powered apps.
To get started, you'll need to configure API keys and optionally install coding CLI tools.
"""
    console.print(Panel(welcome_text.strip(), border_style="cyan"))

    # Check current status
    configured, missing = check_api_keys()
    tool_status = check_coding_tools()

    if configured:
        console.print(f"\n✅ [green]Configured providers:[/green] {', '.join(configured)}")

    if missing:
        console.print(f"\n⚠️  [yellow]Missing providers:[/yellow] {', '.join(missing)}")

        # API Key setup section
        console.print("\n[bold]🔑 API Key Setup[/bold]")
        console.print("For the best experience, we recommend configuring at least one of these providers:")

        # Create recommendation table
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Provider", style="cyan")
        table.add_column("Recommended", style="green")
        table.add_column("Models", style="dim")
        table.add_column("Get API Key", style="blue")

        # Priority recommendations
        table.add_row(
            "Anthropic", "✅ Recommended",
            "Claude Opus, Sonnet, Haiku",
            "https://console.anthropic.com/"
        )
        table.add_row(
            "OpenAI", "✅ Recommended",
            "GPT-5, GPT-5 Mini",
            "https://platform.openai.com/"
        )
        table.add_row(
            "Google", "Optional",
            "Gemini Pro, Flash",
            "https://aistudio.google.com/"
        )
        table.add_row(
            "Groq", "Optional",
            "Llama, Mixtral (fast)",
            "https://console.groq.com/"
        )

        console.print(table)

        console.print("\n[dim]Add your API keys to a .env file in your project directory:[/dim]")
        console.print("[dim]  ANTHROPIC_API_KEY=your_key_here[/dim]")
        console.print("[dim]  OPENAI_API_KEY=your_key_here[/dim]")

    # Coding tools section
    console.print("\n[bold]🛠️  Coding CLI Tools[/bold]")
    console.print("Clanker can launch coding sessions with these tools:")

    # Create tools table
    tools_table = Table(show_header=True, header_style="bold blue")
    tools_table.add_column("Tool", style="cyan")
    tools_table.add_column("Status", style="white")

    tool_info = {
        "claude": "Claude Code",
        "cursor": "Cursor Agent",
        "gemini": "Gemini CLI",
        "codex": "OpenAI Codex"
    }

    for tool, available in tool_status.items():
        name = tool_info.get(tool, tool.title())
        status = "✅ Installed" if available else "❌ Not found"
        status_style = "green" if available else "red"

        tools_table.add_row(
            name,
            f"[{status_style}]{status}[/{status_style}]"
        )

    console.print(tools_table)

    installed_tools = [tool for tool, available in tool_status.items() if available]
    if installed_tools:
        console.print(f"\n✅ [green]You can use:[/green] {', '.join(f'clanker {tool}' for tool in installed_tools)}")
    else:
        console.print("\n💡 [yellow]Install at least one coding tool to get the full Clanker experience![/yellow]")

    # Next steps
    console.print("\n[bold]🚀 Next Steps[/bold]")
    if not configured:
        console.print("1. Set up API keys in .env file")
        console.print("2. Install a coding CLI tool (recommended: claude or cursor)")
        console.print("3. Try: [cyan]clanker \"help me get started\"[/cyan]")
    else:
        console.print("1. Install a coding CLI tool if desired")
        console.print("2. Try: [cyan]clanker \"list my apps\"[/cyan] or [cyan]clanker \"help\"[/cyan]")


def offer_env_creation() -> bool:
    """Offer to create .env file from template.

    Returns True if .env file was created.
    """
    env_path = Path(".env")
    env_example_path = Path(".env.example")

    # Don't offer if .env already exists
    if env_path.exists():
        return False

    # Don't offer if no .env.example exists
    if not env_example_path.exists():
        return False

    console.print()
    if Confirm.ask("Would you like me to create a .env file from the template?", default=True):
        try:
            shutil.copy2(env_example_path, env_path)
            console.print(f"✅ [green]Created .env file![/green]")
            console.print(f"[dim]Edit {env_path} to add your API keys[/dim]")
            return True
        except Exception as e:
            console.print(f"❌ [red]Failed to create .env file: {e}[/red]")
            return False

    return False


def run_onboarding() -> None:
    """Run the complete onboarding process."""
    logger.info("Running first-time onboarding")

    try:
        show_setup_guidance()

        # Offer to create .env file
        if offer_env_creation():
            console.print("\n[dim]You can now restart Clanker to use your configured API keys.[/dim]")

        console.print()

    except KeyboardInterrupt:
        console.print("\n[yellow]Onboarding interrupted[/yellow]")
    except Exception as e:
        logger.error(f"Onboarding failed: {e}", exc_info=True)
        console.print(f"[red]Onboarding error: {e}[/red]")


def get_config_status() -> Dict[str, any]:
    """Get current configuration status for display.

    Returns:
        Dict with keys: providers, tools, needs_setup
    """
    configured, missing = check_api_keys()
    tools = check_coding_tools()

    return {
        "providers": configured,
        "tools": [tool for tool, available in tools.items() if available],
        "needs_setup": len(configured) == 0
    }