"""Example app to test discovery."""

import typer
from clanker.logger import get_logger
from clanker.models import list_available_providers

logger = get_logger("example")
app = typer.Typer(help="Example app demonstrating clanker integration")


@app.command()
def hello(name: str = typer.Argument("World", help="Name to greet")):
    """Say hello using clanker features."""
    logger.info(f"Greeting {name}")
    print(f"Hello, {name}!")
    
    providers = list_available_providers()
    if providers:
        print(f"Available AI providers: {', '.join(providers)}")
    else:
        print("No AI providers configured")


@app.command()
def test():
    """Test command."""
    logger.debug("Running test command")
    print("Test successful")


if __name__ == "__main__":
    app()