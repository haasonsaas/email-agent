#!/usr/bin/env python3
"""Process large batches of emails with CEO labels efficiently."""

import asyncio
import json
import sys
from datetime import datetime
from email_agent.agents.ceo_assistant import CEOAssistantAgent
from email_agent.storage.database import DatabaseManager
from email_agent.models import Email, EmailAddress, EmailCategory, EmailPriority
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import keyring
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
import time

console = Console()

async def process_batch(emails, ceo_assistant, service, label_map, db, progress, task):
    """Process a batch of emails efficiently."""
    stats = {
        'processed': 0,
        'labeled': 0,
        'decisions_required': 0,
        'investor_emails': 0,
        'customer_emails': 0,
        'quick_wins': 0,
        'errors': 0
    }
    
    for email in emails:
        try:
            # Quick progress update
            progress.update(task, description=f"[cyan]Processing: {email.subject[:40]}...")
            
            # Analyze email
            analysis = await ceo_assistant.analyze_for_ceo(email)
            
            if 'error' not in analysis:
                stats['processed'] += 1
                
                # Get labels to apply
                ceo_label_names = analysis.get('ceo_labels', [])
                labels_to_add = []
                
                for label_name in ceo_label_names:
                    full_label = f'EmailAgent/CEO/{label_name}'
                    if full_label in label_map:
                        labels_to_add.append(label_map[full_label])
                        
                        # Quick stats update
                        if label_name == 'DecisionRequired':
                            stats['decisions_required'] += 1
                        elif label_name == 'Investors':
                            stats['investor_emails'] += 1
                        elif label_name == 'Customers':
                            stats['customer_emails'] += 1
                        elif label_name == 'QuickWins':
                            stats['quick_wins'] += 1
                
                # Add processed label
                if 'EmailAgent/Processed' in label_map:
                    labels_to_add.append(label_map['EmailAgent/Processed'])
                
                # Apply labels in Gmail (with error handling)
                if email.message_id and labels_to_add:
                    try:
                        msg_id = email.message_id.strip('<>')
                        query = f'rfc822msgid:{msg_id}'
                        results = service.users().messages().list(userId='me', q=query).execute()
                        
                        if results.get('messages'):
                            gmail_msg_id = results['messages'][0]['id']
                            body = {'addLabelIds': labels_to_add}
                            service.users().messages().modify(
                                userId='me', id=gmail_msg_id, body=body
                            ).execute()
                            stats['labeled'] += 1
                    except Exception as e:
                        if "notFound" not in str(e):
                            console.print(f"[dim]Gmail error for {email.subject[:30]}[/dim]")
                
                # Update database
                with db.get_session() as session:
                    from email_agent.storage.models import EmailORM
                    email_orm = session.query(EmailORM).filter_by(id=email.id).first()
                    if email_orm:
                        current_tags = json.loads(email_orm.tags) if isinstance(email_orm.tags, str) else (email_orm.tags or [])
                        if 'ceo_processed' not in current_tags:
                            current_tags.append('ceo_processed')
                        email_orm.tags = json.dumps(current_tags)
                        session.commit()
            else:
                stats['errors'] += 1
                
        except Exception as e:
            stats['errors'] += 1
            console.print(f"[red]Error: {str(e)[:50]}[/red]")
        
        progress.advance(task)
    
    return stats

async def process_ceo_emails_batch(total_limit: int = 500):
    """Process large batches of emails with CEO labels."""
    
    console.print(Panel.fit("[bold cyan]🎯 CEO Batch Email Processing[/bold cyan]", border_style="cyan"))
    
    # Initialize components
    db = DatabaseManager()
    ceo_assistant = CEOAssistantAgent()
    
    # Get total count of unprocessed emails
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        
        total_unprocessed = session.query(EmailORM).filter(
            ~EmailORM.tags.like('%ceo_processed%')
        ).count()
        
        console.print(f"\n📊 Total unprocessed emails: [yellow]{total_unprocessed}[/yellow]")
        console.print(f"📧 Will process up to: [cyan]{total_limit}[/cyan] emails\n")
    
    # Load Gmail credentials once
    console.print("🔐 Authenticating with Gmail...")
    creds_json = keyring.get_password("email_agent", "gmail_credentials_default")
    if not creds_json:
        console.print("[red]❌ No Gmail credentials found.[/red]")
        return
    
    creds_data = json.loads(creds_json)
    creds = Credentials.from_authorized_user_info(creds_data, [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ])
    
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
    service = build('gmail', 'v1', credentials=creds)
    
    # Get label map
    results = service.users().labels().list(userId='me').execute()
    label_map = {label['name']: label['id'] for label in results.get('labels', [])}
    console.print(f"✅ Connected with [cyan]{len([l for l in label_map if l.startswith('EmailAgent/CEO/')])}[/cyan] CEO labels\n")
    
    # Process in chunks
    batch_size = 50
    total_stats = {
        'total': 0,
        'processed': 0,
        'labeled': 0,
        'decisions_required': 0,
        'investor_emails': 0,
        'customer_emails': 0,
        'quick_wins': 0,
        'errors': 0
    }
    
    emails_processed = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Processing emails...", total=min(total_limit, total_unprocessed))
        
        while emails_processed < total_limit:
            # Get next batch
            with db.get_session() as session:
                from email_agent.storage.models import EmailORM
                
                # Get older emails that haven't been processed
                emails_orm = session.query(EmailORM).filter(
                    ~EmailORM.tags.like('%ceo_processed%')
                ).order_by(EmailORM.received_date.asc()).limit(batch_size).all()  # Changed to ascending to get older emails first
                
                if not emails_orm:
                    console.print("\n[green]✅ No more emails to process![/green]")
                    break
                
                # Convert to Email objects
                emails = []
                for e in emails_orm:
                    tags = []
                    if e.tags:
                        try:
                            tags = json.loads(e.tags) if isinstance(e.tags, str) else e.tags
                        except:
                            tags = []
                    
                    email = Email(
                        id=e.id,
                        message_id=e.message_id,
                        thread_id=e.thread_id,
                        subject=e.subject,
                        sender=EmailAddress(email=e.sender_email, name=e.sender_name),
                        recipients=[],
                        date=e.date,
                        received_date=e.received_date,
                        body_text=e.body_text or '',
                        is_read=e.is_read,
                        is_flagged=e.is_flagged,
                        category=EmailCategory(e.category) if e.category else EmailCategory.PERSONAL,
                        priority=EmailPriority(e.priority) if e.priority else EmailPriority.NORMAL,
                        tags=tags
                    )
                    emails.append(email)
            
            # Process this batch
            batch_stats = await process_batch(emails, ceo_assistant, service, label_map, db, progress, task)
            
            # Update total stats
            total_stats['total'] += len(emails)
            for key in ['processed', 'labeled', 'decisions_required', 'investor_emails', 'customer_emails', 'quick_wins', 'errors']:
                total_stats[key] += batch_stats[key]
            
            emails_processed += len(emails)
            
            # Small delay between batches
            await asyncio.sleep(0.5)
    
    # Display final statistics
    console.print("\n[bold green]📊 Batch Processing Complete![/bold green]\n")
    
    table = Table(title="CEO Email Processing Results", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan", width=30)
    table.add_column("Count", justify="right", style="magenta")
    table.add_column("Percentage", justify="right", style="green")
    
    table.add_row("Total Emails Processed", str(total_stats['total']), "100%")
    table.add_row("Successfully Analyzed", str(total_stats['processed']), f"{total_stats['processed']/total_stats['total']*100:.1f}%")
    table.add_row("Labels Applied in Gmail", str(total_stats['labeled']), f"{total_stats['labeled']/total_stats['total']*100:.1f}%")
    table.add_row("", "", "")
    table.add_row("🔴 Decisions Required", str(total_stats['decisions_required']), f"{total_stats['decisions_required']/total_stats['total']*100:.1f}%")
    table.add_row("💰 Investor Communications", str(total_stats['investor_emails']), f"{total_stats['investor_emails']/total_stats['total']*100:.1f}%")
    table.add_row("👥 Customer Related", str(total_stats['customer_emails']), f"{total_stats['customer_emails']/total_stats['total']*100:.1f}%")
    table.add_row("✅ Quick Wins (<5 min)", str(total_stats['quick_wins']), f"{total_stats['quick_wins']/total_stats['total']*100:.1f}%")
    
    if total_stats['errors'] > 0:
        table.add_row("", "", "")
        table.add_row("❌ Errors", str(total_stats['errors']), f"{total_stats['errors']/total_stats['total']*100:.1f}%", style="red")
    
    console.print(table)
    
    # Key insights
    console.print("\n[bold]💡 Key Insights:[/bold]")
    
    if total_stats['decisions_required'] > 0:
        console.print(f"  🔴 You have [red]{total_stats['decisions_required']}[/red] emails requiring CEO decisions")
    
    if total_stats['investor_emails'] > 0:
        console.print(f"  💰 Found [yellow]{total_stats['investor_emails']}[/yellow] investor-related emails")
    
    if total_stats['customer_emails'] > 0:
        console.print(f"  👥 Identified [green]{total_stats['customer_emails']}[/green] customer communications")
    
    if total_stats['quick_wins'] > 0:
        console.print(f"  ✅ [cyan]{total_stats['quick_wins']}[/cyan] quick wins you can handle in under 5 minutes")
    
    console.print(f"\n✨ All {total_stats['total']} emails have been analyzed and labeled!")
    console.print("   Check your Gmail to see the organized inbox with CEO labels")

if __name__ == "__main__":
    limit = 500
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except:
            pass
    
    asyncio.run(process_ceo_emails_batch(limit))