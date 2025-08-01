"""Rule management commands."""

import typer
from rich.console import Console

console = Console()
app = typer.Typer()

@app.command()
def list():
    """List all categorization rules."""
    console.print("[yellow]Rules management not yet implemented[/yellow]")

@app.command() 
def add():
    """Add a new categorization rule."""
    console.print("[yellow]Add rule not yet implemented[/yellow]")

@app.command()
def remove(rule_id: str):
    """Remove a categorization rule."""
    console.print(f"[yellow]Remove rule {rule_id} not yet implemented[/yellow]")