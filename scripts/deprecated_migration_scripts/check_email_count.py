#!/usr/bin/env python3
"""Check email count in database."""

from email_agent.storage.database import DatabaseManager
from rich.console import Console
from rich.table import Table

console = Console()

# Initialize database
db = DatabaseManager()

with db.get_session() as session:
    from email_agent.storage.models import EmailORM
    
    # Total emails
    total_emails = session.query(EmailORM).count()
    
    # Unprocessed emails (without ceo_processed tag)
    unprocessed = session.query(EmailORM).filter(
        ~EmailORM.tags.like('%ceo_processed%')
    ).count()
    
    # Already processed
    processed = session.query(EmailORM).filter(
        EmailORM.tags.like('%ceo_processed%')
    ).count()
    
    # Get date range
    oldest = session.query(EmailORM).order_by(EmailORM.received_date.asc()).first()
    newest = session.query(EmailORM).order_by(EmailORM.received_date.desc()).first()
    
    # Create summary table
    table = Table(title="Email Database Summary", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="yellow")
    
    table.add_row("Total Emails", str(total_emails))
    table.add_row("CEO Processed", str(processed))
    table.add_row("Unprocessed", str(unprocessed))
    
    if oldest and newest:
        table.add_row("Date Range", f"{oldest.received_date.strftime('%Y-%m-%d')} to {newest.received_date.strftime('%Y-%m-%d')}")
    
    console.print(table)
    
    # Show some sample subjects
    if unprocessed > 0:
        console.print("\n[bold]Sample unprocessed emails:[/bold]")
        samples = session.query(EmailORM).filter(
            ~EmailORM.tags.like('%ceo_processed%')
        ).limit(5).all()
        
        for email in samples:
            console.print(f"  • {email.subject[:60]}... ({email.received_date.strftime('%Y-%m-%d')})")