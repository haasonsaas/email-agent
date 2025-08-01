"""Category management commands."""

import typer
from rich.console import Console

console = Console()
app = typer.Typer()

@app.command()
def list():
    """List email categories and counts."""
    console.print("[yellow]Category management not yet implemented[/yellow]")

@app.command()
def stats():
    """Show category statistics.""" 
    console.print("[yellow]Category stats not yet implemented[/yellow]")