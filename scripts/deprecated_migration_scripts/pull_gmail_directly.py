#!/usr/bin/env python3
"""Pull emails directly from Gmail API."""

import asyncio
import json
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import keyring
from email_agent.storage.database import DatabaseManager
from email_agent.models import Email, EmailAddress, EmailCategory
from email_agent.connectors.gmail import GmailConnector
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()

async def pull_gmail_emails(days_back: int = 90, max_emails: int = 1000):
    """Pull emails directly from Gmail."""
    console.print(f"[bold cyan]📥 Pulling Gmail emails from the last {days_back} days[/bold cyan]")
    
    # Initialize database
    db = DatabaseManager()
    
    # Check current email count
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        initial_count = session.query(EmailORM).count()
        console.print(f"Current emails in database: [yellow]{initial_count}[/yellow]")
    
    # Load Gmail credentials
    console.print("\n🔐 Authenticating with Gmail...")
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
    console.print("✅ Connected to Gmail")
    
    # Calculate date range
    since_date = datetime.now() - timedelta(days=days_back)
    date_str = since_date.strftime('%Y/%m/%d')
    
    # Build query to get ALL emails (not just inbox)
    query = f'after:{date_str}'
    console.print(f"\n🔍 Searching for emails after {date_str}...")
    
    # Use page tokens to get more emails
    all_messages = []
    page_token = None
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Fetching email list...", total=None)
        
        while len(all_messages) < max_emails:
            try:
                # Get batch of message IDs
                if page_token:
                    results = service.users().messages().list(
                        userId='me',
                        q=query,
                        pageToken=page_token,
                        maxResults=500  # Max allowed per request
                    ).execute()
                else:
                    results = service.users().messages().list(
                        userId='me',
                        q=query,
                        maxResults=500
                    ).execute()
                
                messages = results.get('messages', [])
                if not messages:
                    break
                
                all_messages.extend(messages)
                progress.update(task, description=f"[cyan]Found {len(all_messages)} emails...")
                
                # Check if there are more pages
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                console.print(f"[red]Error fetching messages: {str(e)}[/red]")
                break
    
    console.print(f"\n✅ Found [green]{len(all_messages)}[/green] total emails")
    
    # Now fetch full details and save to database
    console.print("\n📥 Downloading email details and saving to database...")
    
    # Initialize Gmail connector for parsing
    connector = GmailConnector({
        'client_id': creds_data.get('client_id'),
        'client_secret': creds_data.get('client_secret')
    })
    connector.service = service
    connector.authenticated = True
    
    saved_count = 0
    error_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Processing emails...", total=len(all_messages))
        
        # Process in batches
        batch_size = 10
        for i in range(0, len(all_messages), batch_size):
            batch = all_messages[i:i+batch_size]
            
            for msg in batch:
                try:
                    # Fetch full message
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    # Parse into Email object
                    email_obj = connector._parse_message(message)
                    
                    # Save to database
                    with db.get_session() as session:
                        from email_agent.storage.models import EmailORM
                        
                        # Check if already exists
                        existing = session.query(EmailORM).filter_by(
                            message_id=email_obj.message_id
                        ).first()
                        
                        if not existing:
                            # Generate a unique ID if not provided
                            email_id = email_obj.id or f"gmail_{msg['id']}"
                            
                            email_orm = EmailORM(
                                id=email_id,  # Add explicit ID
                                message_id=email_obj.message_id,
                                thread_id=email_obj.thread_id,
                                subject=email_obj.subject,
                                sender_email=email_obj.sender.email,
                                sender_name=email_obj.sender.name,
                                recipients=json.dumps([r.email for r in email_obj.recipients]),
                                cc=json.dumps([r.email for r in email_obj.cc]) if email_obj.cc else None,
                                bcc=json.dumps([r.email for r in email_obj.bcc]) if email_obj.bcc else None,
                                date=email_obj.date,
                                received_date=email_obj.received_date,
                                body_text=email_obj.body_text,
                                body_html=email_obj.body_html,
                                is_read=email_obj.is_read,
                                is_flagged=email_obj.is_flagged,
                                category=email_obj.category.value if email_obj.category else 'primary',
                                priority=email_obj.priority.value if hasattr(email_obj, 'priority') else 'normal',
                                tags=json.dumps([]),
                                connector_type='gmail',
                                connector_data=json.dumps(email_obj.connector_data) if email_obj.connector_data else None
                            )
                            session.add(email_orm)
                            session.commit()
                            saved_count += 1
                    
                except Exception as e:
                    error_count += 1
                    console.print(f"[dim]Error processing email {msg['id']}: {str(e)[:50]}[/dim]")
                
                progress.advance(task)
            
            # Small delay between batches
            await asyncio.sleep(0.1)
    
    # Final count
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        final_count = session.query(EmailORM).count()
    
    console.print(f"\n[bold green]📊 Pull Complete![/bold green]")
    console.print(f"  • New emails saved: [green]{saved_count}[/green]")
    console.print(f"  • Errors: [red]{error_count}[/red]")
    console.print(f"  • Total emails now: [cyan]{final_count}[/cyan]")

if __name__ == "__main__":
    import sys
    
    days = 90
    limit = 1000
    
    if len(sys.argv) > 1:
        days = int(sys.argv[1])
    if len(sys.argv) > 2:
        limit = int(sys.argv[2])
    
    asyncio.run(pull_gmail_emails(days_back=days, max_emails=limit))