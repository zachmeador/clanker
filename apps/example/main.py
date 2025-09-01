"""Example app with CLI commands for export testing."""

import typer
from rich.console import Console

app = typer.Typer(help="Example app demonstrating CLI-based exports")
console = Console()


@app.command()
def hello(name: str = typer.Argument("World", help="Name to greet")):
    """Greet a user."""
    greeting = f"Hello, {name}!"
    console.print(f"[green]{greeting}[/green]")
    return greeting


@app.command()
def status():
    """Show app status."""
    status_msg = "Example app is running"
    console.print(f"[blue]{status_msg}[/blue]")
    return status_msg


if __name__ == "__main__":
    app()