"""Daily brief generation and viewing commands."""

import asyncio
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from ...config import settings
from ...storage import DatabaseManager
from ...agents import EmailAgentCrew

console = Console()
app = typer.Typer()


@app.command()
def generate(
    date_str: Optional[str] = typer.Option(
        None,
        "--date",
        help="Date for brief (default: today, format: YYYY-MM-DD)"
    ),
    save: bool = typer.Option(
        True,
        "--save/--no-save",
        help="Save brief to file"
    ),
    format: str = typer.Option(
        "markdown",
        "--format",
        help="Output format (markdown, json, text)"
    )
):
    """Generate daily brief for specified date."""
    
    async def run_generate():
        try:
            # Parse date
            target_date = parse_date_string(date_str) if date_str else date.today()
            
            # Initialize components
            db = DatabaseManager()
            crew = EmailAgentCrew()
            
            # Get emails for the date
            emails = db.get_emails(
                since=datetime.combine(target_date, datetime.min.time()),
                until=datetime.combine(target_date, datetime.max.time()),
                limit=1000
            )
            
            if not emails:
                console.print(f"[yellow]No emails found for {target_date}[/yellow]")
                return
            
            console.print(f"[cyan]Generating brief for {target_date} from {len(emails)} emails[/cyan]")
            
            # Initialize crew and generate brief
            await crew.initialize_crew({})
            
            with console.status("[bold blue]Generating brief..."):
                brief = await crew.execute_task(
                    "generate_brief",
                    emails=emails,
                    date=target_date
                )
            
            # Display brief
            if format == "markdown":
                display_brief_markdown(brief)
            elif format == "json":
                display_brief_json(brief)
            else:
                display_brief_text(brief)
            
            # Save brief if requested
            if save:
                save_brief_to_file(brief, format)
            
            await crew.shutdown()
            
        except Exception as e:
            console.print(f"[red]Brief generation failed: {str(e)}[/red]")
    
    asyncio.run(run_generate())


@app.command()
def show(
    date_str: Optional[str] = typer.Option(
        None,
        "--date",
        help="Date to show (default: today, format: YYYY-MM-DD)"
    ),
    format: str = typer.Option(
        "markdown",
        "--format",
        help="Display format (markdown, json, text)"
    )
):
    """Show existing daily brief."""
    try:
        target_date = parse_date_string(date_str) if date_str else date.today()
        
        # Try to find existing brief file
        brief_file = find_brief_file(target_date, format)
        
        if brief_file and brief_file.exists():
            content = brief_file.read_text()
            
            if format == "markdown":
                console.print(Markdown(content))
            else:
                console.print(content)
        else:
            console.print(f"[yellow]No brief found for {target_date}[/yellow]")
            console.print("Run 'email-agent brief generate' to create one.")
            
    except Exception as e:
        console.print(f"[red]Failed to show brief: {str(e)}[/red]")


@app.command()
def list(
    days: int = typer.Option(
        7,
        "--days",
        help="Number of recent days to show"
    )
):
    """List recent daily briefs."""
    try:
        briefs_dir = settings.briefs_dir
        
        if not briefs_dir.exists():
            console.print("[yellow]No briefs directory found[/yellow]")
            return
        
        # Find brief files
        brief_files = []
        for i in range(days):
            check_date = date.today() - timedelta(days=i)
            brief_file = briefs_dir / f"{check_date.isoformat()}.md"
            
            if brief_file.exists():
                stat = brief_file.stat()
                brief_files.append({
                    "date": check_date,
                    "file": brief_file,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime)
                })
        
        if not brief_files:
            console.print(f"[yellow]No briefs found in the last {days} days[/yellow]")
            return
        
        # Display table
        table = Table(title=f"Daily Briefs (Last {days} days)")
        table.add_column("Date", style="cyan")
        table.add_column("Size", style="magenta")
        table.add_column("Generated", style="yellow")
        
        for brief_info in brief_files:
            table.add_row(
                brief_info["date"].isoformat(),
                f"{brief_info['size']:,} bytes",
                brief_info["modified"].strftime("%H:%M")
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to list briefs: {str(e)}[/red]")


@app.command()
def stats():
    """Show brief generation statistics."""
    try:
        briefs_dir = settings.briefs_dir
        
        if not briefs_dir.exists():
            console.print("[yellow]No briefs directory found[/yellow]")
            return
        
        # Count brief files
        brief_files = list(briefs_dir.glob("*.md"))
        
        if not brief_files:
            console.print("[yellow]No briefs found[/yellow]")
            return
        
        # Calculate stats
        total_size = sum(f.stat().st_size for f in brief_files)
        oldest_brief = min(brief_files, key=lambda f: f.stat().st_mtime)
        newest_brief = max(brief_files, key=lambda f: f.stat().st_mtime)
        
        # Display stats
        table = Table(title="Brief Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Total Briefs", str(len(brief_files)))
        table.add_row("Total Size", f"{total_size:,} bytes")
        table.add_row("Oldest Brief", oldest_brief.stem)
        table.add_row("Newest Brief", newest_brief.stem)
        table.add_row("Briefs Directory", str(briefs_dir))
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Failed to get brief stats: {str(e)}[/red]")


def parse_date_string(date_str: str) -> date:
    """Parse date string."""
    try:
        return datetime.fromisoformat(date_str).date()
    except ValueError:
        # Try some common formats
        for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"]:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Default to today
        return date.today()


def display_brief_markdown(brief):
    """Display brief in markdown format."""
    markdown_content = f"""# Daily Email Brief - {brief.date.strftime('%Y-%m-%d')}

## {brief.headline}

{brief.summary}

### Statistics
- **Total Emails:** {brief.total_emails}
- **Unread Emails:** {brief.unread_emails}

### Action Items
"""
    
    if brief.action_items:
        for item in brief.action_items:
            markdown_content += f"- {item}\n"
    else:
        markdown_content += "- No action items\n"
    
    markdown_content += "\n### Deadlines\n"
    
    if brief.deadlines:
        for deadline in brief.deadlines:
            markdown_content += f"- {deadline}\n"
    else:
        markdown_content += "- No deadlines\n"
    
    console.print(Markdown(markdown_content))


def display_brief_json(brief):
    """Display brief in JSON format."""
    import json
    brief_dict = brief.dict()
    console.print(json.dumps(brief_dict, indent=2, default=str))


def display_brief_text(brief):
    """Display brief in plain text format."""
    console.print(Panel.fit(
        f"""[bold cyan]{brief.headline}[/bold cyan]

{brief.summary}

[bold]Statistics:[/bold]
• Total Emails: {brief.total_emails}
• Unread Emails: {brief.unread_emails}

[bold]Action Items:[/bold]
{chr(10).join(f"• {item}" for item in brief.action_items) if brief.action_items else "• No action items"}

[bold]Deadlines:[/bold]
{chr(10).join(f"• {item}" for item in brief.deadlines) if brief.deadlines else "• No deadlines"}
""",
        title=f"Daily Brief - {brief.date.strftime('%Y-%m-%d')}",
        border_style="cyan"
    ))


def save_brief_to_file(brief, format: str):
    """Save brief to file."""
    try:
        briefs_dir = settings.briefs_dir
        briefs_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = brief.date.strftime('%Y-%m-%d')
        
        if format == "markdown":
            filename = f"{date_str}.md"
            content = create_markdown_content(brief)
        elif format == "json":
            filename = f"{date_str}.json"
            import json
            content = json.dumps(brief.dict(), indent=2, default=str)
        else:
            filename = f"{date_str}.txt"
            content = create_text_content(brief)
        
        file_path = briefs_dir / filename
        file_path.write_text(content)
        
        console.print(f"[green]Brief saved to: {file_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]Failed to save brief: {str(e)}[/red]")


def create_markdown_content(brief) -> str:
    """Create markdown content for brief."""
    return f"""# Daily Email Brief - {brief.date.strftime('%Y-%m-%d')}

## {brief.headline}

{brief.summary}

## Statistics

- **Total Emails:** {brief.total_emails}
- **Unread Emails:** {brief.unread_emails}
- **Generated:** {brief.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
- **Model:** {brief.model_used or 'rule_based'}

## Action Items

{chr(10).join(f"- {item}" for item in brief.action_items) if brief.action_items else "- No action items"}

## Deadlines

{chr(10).join(f"- {item}" for item in brief.deadlines) if brief.deadlines else "- No deadlines"}

---
*Generated by Email Agent*
"""


def create_text_content(brief) -> str:
    """Create plain text content for brief."""
    return f"""Daily Email Brief - {brief.date.strftime('%Y-%m-%d')}

{brief.headline}

{brief.summary}

STATISTICS:
Total Emails: {brief.total_emails}
Unread Emails: {brief.unread_emails}
Generated: {brief.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
Model: {brief.model_used or 'rule_based'}

ACTION ITEMS:
{chr(10).join(f"- {item}" for item in brief.action_items) if brief.action_items else "- No action items"}

DEADLINES:
{chr(10).join(f"- {item}" for item in brief.deadlines) if brief.deadlines else "- No deadlines"}

---
Generated by Email Agent
"""


def find_brief_file(target_date: date, format: str) -> Optional[Path]:
    """Find brief file for date."""
    briefs_dir = settings.briefs_dir
    
    if not briefs_dir.exists():
        return None
    
    date_str = target_date.isoformat()
    
    extensions = {
        "markdown": ".md",
        "json": ".json",
        "text": ".txt"
    }
    
    ext = extensions.get(format, ".md")
    return briefs_dir / f"{date_str}{ext}"