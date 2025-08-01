#!/usr/bin/env python3
"""Bulk label emails with intelligent action detection."""

import asyncio
import json
from datetime import datetime, timedelta
from email_agent.agents.action_extractor import ActionExtractorAgent
from email_agent.storage.database import DatabaseManager
from email_agent.models import Email, EmailAddress, EmailCategory, EmailPriority
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import keyring
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

console = Console()

async def bulk_label_emails(limit: int = 50, skip_processed: bool = True):
    """Bulk process and label emails with AI analysis."""
    
    console.print("[bold cyan]🤖 Bulk Email Labeling System[/bold cyan]")
    console.print("=" * 50)
    
    # Initialize components
    db = DatabaseManager()
    extractor = ActionExtractorAgent()
    
    # Get emails from database
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        
        query = session.query(EmailORM)
        
        if skip_processed:
            # Skip emails already processed
            query = query.filter(~EmailORM.tags.like('%action_processed%'))
        
        # Order by most recent first
        emails_orm = query.order_by(EmailORM.received_date.desc()).limit(limit).all()
        
        console.print(f"\n📧 Found [yellow]{len(emails_orm)}[/yellow] emails to process")
        
        if not emails_orm:
            console.print("[green]✅ All emails are already processed![/green]")
            return
        
        emails = []
        for e in emails_orm:
            # Parse tags properly
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
                body=e.body_text or '',
                is_read=e.is_read,
                is_flagged=e.is_flagged,
                category=EmailCategory(e.category) if e.category else EmailCategory.PERSONAL,
                priority=EmailPriority(e.priority) if e.priority else EmailPriority.NORMAL,
                tags=tags
            )
            emails.append(email)
    
    # Load Gmail credentials
    console.print("\n🔐 Authenticating with Gmail...")
    creds_json = keyring.get_password("email_agent", "gmail_credentials_default")
    if not creds_json:
        console.print("[red]❌ No Gmail credentials found. Run authenticate_gmail.py first.[/red]")
        return
    
    creds_data = json.loads(creds_json)
    creds = Credentials.from_authorized_user_info(creds_data, [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ])
    
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        keyring.set_password("email_agent", "gmail_credentials_default", creds.to_json())
    
    service = build('gmail', 'v1', credentials=creds)
    
    # Get label IDs
    results = service.users().labels().list(userId='me').execute()
    label_map = {label['name']: label['id'] for label in results.get('labels', [])}
    
    email_agent_labels = [l for l in label_map if l.startswith('EmailAgent/')]
    console.print(f"✅ Connected to Gmail with [cyan]{len(email_agent_labels)}[/cyan] EmailAgent labels ready")
    
    # Statistics
    stats = {
        'total': len(emails),
        'processed': 0,
        'labeled': 0,
        'high_priority': 0,
        'meetings': 0,
        'deadlines': 0,
        'commitments': 0,
        'waiting': 0,
        'errors': 0
    }
    
    # Process emails with progress bar
    console.print(f"\n🔍 Analyzing emails and applying labels...\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Processing emails...", total=len(emails))
        
        # Process in batches to avoid rate limits
        batch_size = 5
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            
            # Extract actions for batch
            batch_actions = await extractor.extract_batch_actions(batch)
            
            for email, actions in zip(batch, batch_actions):
                progress.update(task, description=f"[cyan]Processing: {email.subject[:40]}...")
                
                if 'error' in actions:
                    stats['errors'] += 1
                    continue
                
                stats['processed'] += 1
                
                # Determine which labels to apply
                labels_to_add = []
                applied_labels = []
                
                # High Priority
                if actions.get('response_urgency') == 'urgent':
                    if 'EmailAgent/Actions/HighPriority' in label_map:
                        labels_to_add.append(label_map['EmailAgent/Actions/HighPriority'])
                        applied_labels.append('HighPriority')
                        stats['high_priority'] += 1
                
                # Meeting Requests
                if actions.get('meeting_requests'):
                    if 'EmailAgent/Actions/MeetingRequest' in label_map:
                        labels_to_add.append(label_map['EmailAgent/Actions/MeetingRequest'])
                        applied_labels.append('Meeting')
                        stats['meetings'] += 1
                
                # Deadlines
                if any(item.get('deadline') for item in actions.get('action_items', [])):
                    if 'EmailAgent/Actions/Deadline' in label_map:
                        labels_to_add.append(label_map['EmailAgent/Actions/Deadline'])
                        applied_labels.append('Deadline')
                        stats['deadlines'] += 1
                
                # Waiting For
                if actions.get('waiting_for'):
                    if 'EmailAgent/Actions/WaitingFor' in label_map:
                        labels_to_add.append(label_map['EmailAgent/Actions/WaitingFor'])
                        applied_labels.append('WaitingFor')
                        stats['waiting'] += 1
                
                # Commitments
                if actions.get('commitments_made'):
                    if 'EmailAgent/Actions/Commitment' in label_map:
                        labels_to_add.append(label_map['EmailAgent/Actions/Commitment'])
                        applied_labels.append('Commitment')
                        stats['commitments'] += 1
                
                # Always add processed label
                if 'EmailAgent/Processed' in label_map:
                    labels_to_add.append(label_map['EmailAgent/Processed'])
                
                # Apply labels in Gmail
                if email.message_id and labels_to_add:
                    try:
                        # Clean message ID
                        msg_id = email.message_id.strip('<>')
                        
                        # Search for the message
                        query = f'rfc822msgid:{msg_id}'
                        results = service.users().messages().list(userId='me', q=query).execute()
                        
                        if results.get('messages'):
                            gmail_msg_id = results['messages'][0]['id']
                            
                            body = {'addLabelIds': labels_to_add}
                            service.users().messages().modify(
                                userId='me', id=gmail_msg_id, body=body
                            ).execute()
                            
                            stats['labeled'] += 1
                            
                            # Show what labels were applied
                            if applied_labels:
                                label_str = ", ".join(applied_labels)
                                progress.console.print(f"   ✅ {email.subject[:40]}... → [green]{label_str}[/green]")
                    except Exception as e:
                        if "notFound" not in str(e):  # Ignore not found errors
                            progress.console.print(f"   ❌ Failed: {email.subject[:30]}... - {str(e)[:50]}")
                
                # Update database
                with db.get_session() as session:
                    email_orm = session.query(EmailORM).filter_by(id=email.id).first()
                    if email_orm:
                        current_tags = json.loads(email_orm.tags) if isinstance(email_orm.tags, str) else (email_orm.tags or [])
                        if 'action_processed' not in current_tags:
                            current_tags.append('action_processed')
                        email_orm.tags = json.dumps(current_tags)
                        
                        # Also update priority if urgent
                        if actions.get('response_urgency') == 'urgent':
                            email_orm.priority = 'urgent'
                            email_orm.is_flagged = True
                        
                        session.commit()
                
                progress.advance(task)
            
            # Small delay between batches to avoid rate limits
            if i + batch_size < len(emails):
                await asyncio.sleep(0.5)
    
    # Display summary statistics
    console.print("\n[bold green]📊 Labeling Complete![/bold green]\n")
    
    # Create summary table
    table = Table(title="Labeling Statistics", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan", width=25)
    table.add_column("Count", justify="right", style="magenta")
    table.add_column("Percentage", justify="right", style="green")
    
    table.add_row("Total Emails", str(stats['total']), "100%")
    table.add_row("Successfully Processed", str(stats['processed']), f"{stats['processed']/stats['total']*100:.1f}%")
    table.add_row("Labels Applied in Gmail", str(stats['labeled']), f"{stats['labeled']/stats['total']*100:.1f}%")
    table.add_row("", "", "")
    table.add_row("🔴 High Priority", str(stats['high_priority']), f"{stats['high_priority']/stats['total']*100:.1f}%")
    table.add_row("📅 Meeting Requests", str(stats['meetings']), f"{stats['meetings']/stats['total']*100:.1f}%")
    table.add_row("⏰ Has Deadlines", str(stats['deadlines']), f"{stats['deadlines']/stats['total']*100:.1f}%")
    table.add_row("🤝 Commitments", str(stats['commitments']), f"{stats['commitments']/stats['total']*100:.1f}%")
    table.add_row("⏳ Waiting For", str(stats['waiting']), f"{stats['waiting']/stats['total']*100:.1f}%")
    
    if stats['errors'] > 0:
        table.add_row("", "", "")
        table.add_row("❌ Errors", str(stats['errors']), f"{stats['errors']/stats['total']*100:.1f}%", style="red")
    
    console.print(table)
    
    # Insights
    console.print("\n[bold]💡 Insights:[/bold]")
    
    if stats['high_priority'] > 0:
        console.print(f"  🔴 You have [red]{stats['high_priority']}[/red] high-priority emails requiring urgent attention")
    
    if stats['meetings'] > 0:
        console.print(f"  📅 Found [blue]{stats['meetings']}[/blue] meeting requests to schedule")
    
    if stats['deadlines'] > 0:
        console.print(f"  ⏰ [yellow]{stats['deadlines']}[/yellow] emails contain items with deadlines")
    
    if stats['commitments'] > 0:
        console.print(f"  🤝 You made commitments in [magenta]{stats['commitments']}[/magenta] emails")
    
    not_in_gmail = stats['processed'] - stats['labeled']
    if not_in_gmail > 0:
        console.print(f"\n  ℹ️  [dim]{not_in_gmail} emails were processed but not found in Gmail (may be deleted or in different account)[/dim]")
    
    console.print(f"\n✨ Check your Gmail to see all the applied labels!")
    console.print("   Labels are visible in the left sidebar under 'EmailAgent'")

if __name__ == "__main__":
    # Run with command line arguments
    import sys
    
    limit = 50  # Default
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except:
            pass
    
    asyncio.run(bulk_label_emails(limit=limit))