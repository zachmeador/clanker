"""Exported functions for the example app."""

from typing import Optional
from clanker.exports import export, ExportType
from clanker.logger import get_logger
from clanker.models import list_available_providers

logger = get_logger("example")


@export(
    name="greet_user",
    description="Greet a user and show available AI providers",
    export_type=ExportType.BOTH,
    cli_path="hello"
)
def greet_user(name: str = "World") -> str:
    """
    Say hello using clanker features.

    Args:
        name: Name of the person to greet

    Returns:
        Greeting message with provider information
    """
    logger.info(f"Greeting {name}")

    greeting = f"Hello, {name}!"

    providers = list_available_providers()
    if providers:
        provider_info = f"Available AI providers: {', '.join(providers)}"
        full_message = f"{greeting}\n{provider_info}"
        print(full_message)
        return full_message
    else:
        full_message = f"{greeting}\nNo AI providers configured"
        print(full_message)
        return full_message


@export(
    name="run_test",
    description="Run a simple test to verify the app is working",
    export_type=ExportType.BOTH,
    cli_path="test"
)
def run_test() -> str:
    """
    Test command to verify app functionality.

    Returns:
        Success message
    """
    logger.debug("Running test command")
    message = "Test successful"
    print(message)
    return message


@export(
    name="get_system_info",
    description="Get information about the current system and available providers",
    export_type=ExportType.TOOL  # Tool only - not exposed as CLI
)
def get_system_info() -> str:
    """
    Get system information for agent use.

    Returns:
        Formatted system information
    """
    providers = list_available_providers()
    provider_count = len(providers) if providers else 0

    info = f"""System Information:
- Available AI Providers: {provider_count}
"""

    if providers:
        for i, provider in enumerate(providers, 1):
            info += f"  {i}. {provider}\n"
    else:
        info += "- No providers configured\n"

    return info.strip()


@export(
    name="validate_name",
    description="Validate if a name is acceptable for greeting",
    export_type=ExportType.TOOL  # Tool only - internal utility
)
def validate_name(name: str) -> bool:
    """
    Validate if a name is acceptable.

    Args:
        name: Name to validate

    Returns:
        True if name is valid, False otherwise
    """
    if not name or not name.strip():
        return False

    # Basic validation - not empty, not too long, no special chars
    name = name.strip()
    if len(name) > 50:
        return False

    # Allow alphanumeric, spaces, hyphens, apostrophes
    import re
    if not re.match(r"^[a-zA-Z0-9\s\-']+$", name):
        return False

    return True


@export(
    name="create_greeting",
    description="Create a personalized greeting message",
    export_type=ExportType.TOOL  # Tool only - helper function
)
def create_greeting(name: str, style: str = "formal") -> str:
    """
    Create a greeting with different styles.

    Args:
        name: Person's name
        style: Greeting style ("formal", "casual", "excited")

    Returns:
        Formatted greeting
    """
    if not validate_name(name):
        return "Hello there!"  # Fallback for invalid names

    styles = {
        "formal": f"Good day, {name}.",
        "casual": f"Hey {name}!",
        "excited": f"Hello {name}!!! 🎉"
    }

    return styles.get(style.lower(), styles["formal"])
