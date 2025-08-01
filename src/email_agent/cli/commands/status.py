"""Status and monitoring commands."""

import typer
from rich.console import Console

console = Console()
app = typer.Typer()

@app.command()
def show():
    """Show system status."""
    console.print("[yellow]Status show not yet implemented[/yellow]")

@app.command()
def agents():
    """Show agent status."""
    console.print("[yellow]Agent status not yet implemented[/yellow]")