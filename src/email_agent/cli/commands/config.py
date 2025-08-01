"""Configuration management commands."""

import typer
from rich.console import Console

console = Console()
app = typer.Typer()

@app.command()
def show():
    """Show current configuration."""
    console.print("[yellow]Config show not yet implemented[/yellow]")

@app.command()
def add_connector():
    """Add a new email connector."""
    console.print("[yellow]Add connector not yet implemented[/yellow]")

@app.command()
def list_connectors():
    """List configured connectors."""
    console.print("[yellow]List connectors not yet implemented[/yellow]")