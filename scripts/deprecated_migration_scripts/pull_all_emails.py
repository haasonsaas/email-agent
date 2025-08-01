#!/usr/bin/env python3
"""Pull all emails from Gmail into the database."""

import asyncio
from datetime import datetime, timedelta
from email_agent.cli.commands.pull import pull_emails
from email_agent.storage.database import DatabaseManager
from rich.console import Console

console = Console()

async def pull_all_emails():
    """Pull emails from Gmail going back further."""
    console.print("[bold cyan]📥 Pulling emails from Gmail...[/bold cyan]")
    
    # Check current email count
    db = DatabaseManager()
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        current_count = session.query(EmailORM).count()
        console.print(f"Current emails in database: [yellow]{current_count}[/yellow]")
    
    # Pull emails from the last 3 months
    days_back = 90
    console.print(f"\nPulling emails from the last [cyan]{days_back}[/cyan] days...")
    
    # Use the pull command with a longer timeframe
    result = await pull_emails(days=days_back, limit=1000, credentials="default")
    
    # Check new count
    with db.get_session() as session:
        new_count = session.query(EmailORM).count()
        console.print(f"\nNew total emails in database: [green]{new_count}[/green]")
        console.print(f"Added: [cyan]{new_count - current_count}[/cyan] emails")

if __name__ == "__main__":
    asyncio.run(pull_all_emails())