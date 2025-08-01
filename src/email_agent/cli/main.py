"""Main CLI interface for Email Agent."""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from ..config import settings
from ..storage import DatabaseManager
from ..agents import EmailAgentCrew
from ..models import ConnectorConfig, EmailCategory
from .commands import init, pull, brief, rules, categories, config, status, inbox

# Setup logging
logging.basicConfig(level=getattr(logging, settings.log_level.upper()))

# Create console for rich output
console = Console()

# Create main CLI app
app = typer.Typer(
    name="email-agent",
    help="CLI Email Agent for triaging and summarizing high-volume inboxes",
    add_completion=False,
    rich_markup_mode="rich"
)

# Add command groups
app.add_typer(init.app, name="init", help="Initialize and configure Email Agent")
app.add_typer(pull.app, name="pull", help="Pull and sync emails from connectors")
app.add_typer(brief.app, name="brief", help="Generate and view daily briefs")
app.add_typer(rules.app, name="rule", help="Manage categorization rules")
app.add_typer(categories.app, name="cat", help="View and manage email categories")
app.add_typer(config.app, name="config", help="Manage configuration and connectors")
app.add_typer(status.app, name="status", help="View system status and statistics")


@app.command()
def version():
    """Show version information."""
    from .. import __version__
    console.print(f"Email Agent v{__version__}")


@app.command()
def quick_start():
    """Quick start guide for new users."""
    console.print(Panel.fit(
        Text.from_markup("""
[bold cyan]Email Agent Quick Start[/bold cyan]

1. [bold]Initialize:[/bold] email-agent init
2. [bold]Add connector:[/bold] email-agent config add-connector gmail
3. [bold]Pull emails:[/bold] email-agent pull --since yesterday
4. [bold]View brief:[/bold] email-agent brief --today
5. [bold]Check status:[/bold] email-agent status

[dim]For detailed help on any command, use: email-agent [command] --help[/dim]
"""),
        title="Quick Start",
        border_style="cyan"
    ))


@app.command()
def dashboard():
    """Launch interactive dashboard (TUI)."""
    try:
        from ..tui import EmailAgentTUI
        tui = EmailAgentTUI()
        tui.run()
    except ImportError:
        console.print("[red]Dashboard requires additional dependencies. Run: pip install email-agent[tui][/red]")
    except Exception as e:
        console.print(f"[red]Failed to launch dashboard: {str(e)}[/red]")


@app.command()
def sync(
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help="Sync emails since this time (e.g., '2023-01-01', 'yesterday', '1 hour ago')"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be synced without actually doing it"
    ),
    brief: bool = typer.Option(
        True,
        "--brief/--no-brief",
        help="Generate daily brief after sync"
    )
):
    """Full sync: pull emails, categorize, and generate brief."""
    
    async def run_sync():
        try:
            # Initialize components
            db = DatabaseManager()
            crew = EmailAgentCrew()
            
            # Get connector configs
            connector_configs = db.get_connector_configs()
            if not connector_configs:
                console.print("[red]No connectors configured. Run 'email-agent config add-connector' first.[/red]")
                return
            
            # Parse since parameter
            since_datetime = None
            if since:
                since_datetime = parse_time_string(since)
            else:
                since_datetime = datetime.now() - timedelta(hours=24)
            
            console.print(f"[cyan]Starting sync since {since_datetime}[/cyan]")
            
            if dry_run:
                console.print("[yellow]DRY RUN - No changes will be made[/yellow]")
                # Show what would be synced
                for config in connector_configs:
                    console.print(f"  Would sync from: {config.name} ({config.type})")
                return
            
            # Initialize crew
            await crew.initialize_crew({})
            
            # Get rules for categorization
            rules = db.get_rules()
            
            # Execute full processing
            with console.status("[bold green]Processing emails..."):
                results = await crew.execute_task(
                    "full_processing",
                    connector_configs=connector_configs,
                    rules=rules,
                    since=since_datetime,
                    generate_brief=brief
                )
            
            # Display results
            console.print("\n[bold green]Sync completed![/bold green]")
            console.print(f"  Emails collected: {results['emails_collected']}")
            console.print(f"  Emails categorized: {results['emails_categorized']}")
            console.print(f"  Emails saved to database: {results['emails_saved']}")
            
            if results.get('brief_generated'):
                console.print(f"  Daily brief: Generated")
            
            if results.get('errors'):
                console.print(f"[red]  Errors: {len(results['errors'])}[/red]")
                for error in results['errors']:
                    console.print(f"    {error}")
            
            await crew.shutdown()
            
        except Exception as e:
            console.print(f"[red]Sync failed: {str(e)}[/red]")
    
    asyncio.run(run_sync())


@app.command()
def stats():
    """Show email statistics."""
    try:
        db = DatabaseManager()
        stats = db.get_email_stats()
        
        if not stats:
            console.print("[yellow]No email statistics available[/yellow]")
            return
        
        # Create statistics table
        table = Table(title="Email Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="magenta")
        
        table.add_row("Total Emails", str(stats["total"]))
        table.add_row("Unread Emails", str(stats["unread"]))
        table.add_row("Flagged Emails", str(stats["flagged"]))
        
        console.print(table)
        
        # Category breakdown
        if stats["categories"]:
            cat_table = Table(title="Category Breakdown")
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Count", style="magenta")
            
            for category, count in stats["categories"].items():
                cat_table.add_row(category.title(), str(count))
            
            console.print(cat_table)
    
    except Exception as e:
        console.print(f"[red]Failed to get statistics: {str(e)}[/red]")


def parse_time_string(time_str: str) -> datetime:
    """Parse human-readable time strings."""
    time_str = time_str.lower().strip()
    
    if time_str in ["today", "now"]:
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_str == "yesterday":
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
    elif time_str.endswith("ago"):
        # Parse "X hours ago", "X days ago", etc.
        parts = time_str.replace("ago", "").strip().split()
        if len(parts) == 2:
            try:
                amount = int(parts[0])
                unit = parts[1].rstrip("s")  # Remove plural 's'
                
                if unit in ["hour", "hr", "h"]:
                    return datetime.now() - timedelta(hours=amount)
                elif unit in ["day", "d"]:
                    return datetime.now() - timedelta(days=amount)
                elif unit in ["week", "w"]:
                    return datetime.now() - timedelta(weeks=amount)
                elif unit in ["minute", "min", "m"]:
                    return datetime.now() - timedelta(minutes=amount)
            except ValueError:
                pass
    else:
        # Try to parse as ISO date
        try:
            return datetime.fromisoformat(time_str)
        except ValueError:
            pass
    
    # Default fallback
    return datetime.now() - timedelta(days=1)


@app.command()
def smart_inbox(
    limit: int = typer.Option(50, help="Maximum number of emails to process"),
    days: int = typer.Option(7, help="Number of days to look back"),
    show_scores: bool = typer.Option(False, "--scores", help="Show attention scores")
):
    """Create smart inbox with AI-powered triage."""
    from .commands.inbox import _smart_inbox
    asyncio.run(_smart_inbox(limit, days, show_scores, True))


@app.command()
def priority_inbox(
    limit: int = typer.Option(20, help="Maximum number of priority emails to show"),
    min_score: float = typer.Option(0.7, help="Minimum attention score for priority")
):
    """Show priority inbox - emails that need immediate attention."""
    from .commands.inbox import _priority_inbox
    asyncio.run(_priority_inbox(limit, min_score))


@app.command()
def triage_stats():
    """Show triage statistics and performance metrics."""
    from .commands.inbox import _triage_stats
    asyncio.run(_triage_stats())


if __name__ == "__main__":
    app()