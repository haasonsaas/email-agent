"""Email pulling and synchronization commands."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ...storage import DatabaseManager
from ...agents import EmailAgentCrew

console = Console()
app = typer.Typer()


@app.command()
def sync(
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help="Pull emails since this time (e.g., 'yesterday', '2023-01-01', '1 hour ago')"
    ),
    connector: Optional[str] = typer.Option(
        None,
        "--connector",
        help="Only sync specific connector by name"
    ),
    limit: int = typer.Option(
        1000,
        "--limit",
        help="Maximum number of emails to pull"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be pulled without actually doing it"
    )
):
    """Pull and sync emails from configured connectors."""
    
    async def run_pull():
        try:
            # Initialize components
            db = DatabaseManager()
            crew = EmailAgentCrew()
            
            # Get connector configurations
            all_configs = db.get_connector_configs()
            if not all_configs:
                console.print("[red]No connectors configured. Run 'email-agent config add-connector' first.[/red]")
                return
            
            # Filter by connector name if specified
            configs = all_configs
            if connector:
                configs = [c for c in all_configs if c.name == connector]
                if not configs:
                    console.print(f"[red]Connector '{connector}' not found.[/red]")
                    return
            
            # Parse since parameter
            since_datetime = parse_time_string(since) if since else datetime.now() - timedelta(hours=24)
            
            console.print(f"[cyan]Pulling emails since {since_datetime}[/cyan]")
            console.print(f"[cyan]Connectors: {', '.join([c.name for c in configs])}[/cyan]")
            
            if dry_run:
                console.print("[yellow]DRY RUN - No emails will be pulled[/yellow]")
                return
            
            # Initialize crew
            await crew.initialize_crew({})
            
            # Pull emails
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Pulling emails...", total=None)
                
                emails = await crew.execute_task(
                    "collect_emails",
                    connector_configs=configs,
                    since=since_datetime
                )
                
                progress.update(task, description=f"Pulled {len(emails)} emails")
            
            if emails:
                # Save to database
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Saving emails...", total=None)
                    
                    saved_count = db.save_emails(emails)
                    progress.update(task, description=f"Saved {saved_count} emails")
                
                console.print(f"[green]Successfully pulled and saved {saved_count} emails[/green]")
                
                # Show summary
                show_pull_summary(emails)
            else:
                console.print("[yellow]No new emails found[/yellow]")
            
            await crew.shutdown()
            
        except Exception as e:
            console.print(f"[red]Pull failed: {str(e)}[/red]")
    
    asyncio.run(run_pull())


@app.command()
def status():
    """Show sync status for all connectors."""
    try:
        db = DatabaseManager()
        configs = db.get_connector_configs()
        
        if not configs:
            console.print("[yellow]No connectors configured[/yellow]")
            return
        
        table = Table(title="Connector Sync Status")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Last Sync", style="yellow")
        table.add_column("Emails Synced", style="blue")
        
        for config in configs:
            status = "Enabled" if config.enabled else "Disabled"
            last_sync = config.last_sync.strftime("%Y-%m-%d %H:%M") if config.last_sync else "Never"
            
            table.add_row(
                config.name,
                config.type,
                status,
                last_sync,
                str(getattr(config, 'total_emails_synced', 0))
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to get sync status: {str(e)}[/red]")


@app.command()
def test(
    connector: str = typer.Argument(help="Connector name to test")
):
    """Test connection to a specific connector."""
    
    async def run_test():
        try:
            db = DatabaseManager()
            configs = db.get_connector_configs()
            
            # Find the connector
            config = None
            for c in configs:
                if c.name == connector:
                    config = c
                    break
            
            if not config:
                console.print(f"[red]Connector '{connector}' not found[/red]")
                return
            
            # Test the connector
            from ...agents import CollectorAgent
            collector = CollectorAgent()
            
            with console.status(f"[bold blue]Testing {connector}..."):
                result = await collector.test_connector(config)
            
            # Display results
            if result["success"]:
                console.print(f"[green]✓[/green] {connector} connection successful")
                console.print(f"  Authentication: {result['auth_status']}")
                if result["test_results"]:
                    console.print(f"  Test results: {result['test_results']}")
            else:
                console.print(f"[red]✗[/red] {connector} connection failed")
                if result["error"]:
                    console.print(f"  Error: {result['error']}")
            
        except Exception as e:
            console.print(f"[red]Test failed: {str(e)}[/red]")
    
    asyncio.run(run_test())


def parse_time_string(time_str: Optional[str]) -> datetime:
    """Parse human-readable time strings."""
    if not time_str:
        return datetime.now() - timedelta(days=1)
    
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


def show_pull_summary(emails):
    """Show summary of pulled emails."""
    from ...models import EmailCategory
    
    # Count by category
    category_counts = {}
    for category in EmailCategory:
        category_counts[category.value] = 0
    
    unread_count = 0
    
    for email in emails:
        category_counts[email.category.value] += 1
        if not email.is_read:
            unread_count += 1
    
    # Create summary table
    table = Table(title="Pull Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="magenta")
    
    for category, count in category_counts.items():
        if count > 0:
            table.add_row(category.title(), str(count))
    
    table.add_row("Unread", str(unread_count), style="bold yellow")
    
    console.print(table)