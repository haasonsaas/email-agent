#!/usr/bin/env python3
"""Actually label ALL emails in Gmail with CEO labels."""

import asyncio
import json
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
from collections import defaultdict

console = Console()

async def label_all_emails(limit: int = 1000):
    """Actually apply CEO labels to emails in Gmail."""
    
    console.print("[bold cyan]🏷️  Gmail CEO Labeling System[/bold cyan]\n")
    
    # Initialize
    db = DatabaseManager()
    ceo_assistant = CEOAssistantAgent()
    
    # Gmail setup
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
    
    # Get unprocessed emails from database
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        
        emails_orm = session.query(EmailORM).filter(
            ~EmailORM.tags.like('%ceo_labeled%')
        ).limit(limit).all()
        
        console.print(f"📧 Found [yellow]{len(emails_orm)}[/yellow] emails to label\n")
        
        emails = []
        email_map = {}  # Map email ID to ORM object for quick updates
        
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
            email_map[email.id] = e
    
    # Statistics
    stats = defaultdict(int)
    label_counts = defaultdict(int)
    errors = []
    
    # Process emails
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Labeling emails...", total=len(emails))
        
        # Process in batches
        batch_size = 5
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i+batch_size]
            
            # Analyze batch
            for email in batch:
                try:
                    # Get CEO analysis
                    analysis = await ceo_assistant.analyze_for_ceo(email)
                    
                    if 'error' not in analysis:
                        ceo_labels = analysis.get('ceo_labels', [])
                        
                        if ceo_labels and email.message_id:
                            # Find email in Gmail
                            msg_id = email.message_id.strip('<>')
                            query = f'rfc822msgid:{msg_id}'
                            
                            try:
                                results = service.users().messages().list(
                                    userId='me', q=query
                                ).execute()
                                
                                if results.get('messages'):
                                    gmail_msg_id = results['messages'][0]['id']
                                    
                                    # Build label list
                                    labels_to_add = []
                                    for label_name in ceo_labels:
                                        full_label = f'EmailAgent/CEO/{label_name}'
                                        if full_label in label_map:
                                            labels_to_add.append(label_map[full_label])
                                            label_counts[label_name] += 1
                                    
                                    # Always add processed label
                                    if 'EmailAgent/Processed' in label_map:
                                        labels_to_add.append(label_map['EmailAgent/Processed'])
                                    
                                    # Apply labels
                                    if labels_to_add:
                                        body = {'addLabelIds': labels_to_add}
                                        service.users().messages().modify(
                                            userId='me', id=gmail_msg_id, body=body
                                        ).execute()
                                        
                                        stats['labeled'] += 1
                                        
                                        # Show what we did
                                        label_str = ', '.join(ceo_labels[:3])
                                        if len(ceo_labels) > 3:
                                            label_str += f' +{len(ceo_labels)-3}'
                                        
                                        progress.console.print(
                                            f"   ✅ {email.subject[:40]}... → [green]{label_str}[/green]"
                                        )
                                else:
                                    stats['not_found'] += 1
                            except Exception as e:
                                if "notFound" not in str(e):
                                    errors.append(f"{email.subject[:30]}: {str(e)[:30]}")
                                stats['gmail_errors'] += 1
                        else:
                            stats['no_labels'] += 1
                    else:
                        stats['analysis_errors'] += 1
                    
                    # Mark as processed in database
                    with db.get_session() as session:
                        email_orm = session.query(EmailORM).filter_by(id=email.id).first()
                        if email_orm:
                            current_tags = json.loads(email_orm.tags) if isinstance(email_orm.tags, str) else (email_orm.tags or [])
                            if 'ceo_labeled' not in current_tags:
                                current_tags.append('ceo_labeled')
                            email_orm.tags = json.dumps(current_tags)
                            session.commit()
                    
                except Exception as e:
                    errors.append(f"Error: {str(e)[:50]}")
                    stats['total_errors'] += 1
                
                progress.advance(task)
            
            # Small delay between batches
            await asyncio.sleep(0.2)
    
    # Display results
    console.print("\n[bold green]✅ Labeling Complete![/bold green]\n")
    
    # Statistics
    console.print("[bold]📊 Results:[/bold]")
    console.print(f"  • Emails processed: {len(emails)}")
    console.print(f"  • Successfully labeled in Gmail: [green]{stats['labeled']}[/green]")
    console.print(f"  • Not found in Gmail: [yellow]{stats['not_found']}[/yellow]")
    console.print(f"  • No labels needed: [dim]{stats['no_labels']}[/dim]")
    console.print(f"  • Errors: [red]{stats['total_errors']}[/red]")
    
    # Label distribution
    if label_counts:
        console.print("\n[bold]🏷️  Labels Applied:[/bold]")
        sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)
        for label, count in sorted_labels[:10]:
            bar = "█" * min(count // 2, 30)
            console.print(f"  {label:<20} {bar} {count}")
    
    # Errors
    if errors:
        console.print(f"\n[red]❌ Errors ({len(errors)}):[/red]")
        for err in errors[:5]:
            console.print(f"  • {err}")
        if len(errors) > 5:
            console.print(f"  ... and {len(errors)-5} more")
    
    console.print("\n✨ Check your Gmail to see all the applied labels!")

if __name__ == "__main__":
    import sys
    limit = 1000
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    
    asyncio.run(label_all_emails(limit))