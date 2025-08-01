#!/usr/bin/env python3
"""Fast CEO email processor - optimized for speed."""

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
from rich.table import Table
import time

console = Console()

async def fast_process_ceo_emails(limit: int = 500):
    """Process emails quickly with CEO labels."""
    
    start_time = time.time()
    console.print(f"[bold cyan]⚡ Fast CEO Email Processing - {limit} emails[/bold cyan]\n")
    
    # Initialize components
    db = DatabaseManager()
    ceo_assistant = CEOAssistantAgent()
    
    # Load Gmail service (but we'll minimize API calls)
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
    
    # Get label map once
    results = service.users().labels().list(userId='me').execute()
    label_map = {label['name']: label['id'] for label in results.get('labels', [])}
    
    # Get emails to process
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        
        emails_orm = session.query(EmailORM).filter(
            ~EmailORM.tags.like('%ceo_processed%')
        ).order_by(EmailORM.received_date.desc()).limit(limit).all()
        
        console.print(f"📧 Processing [yellow]{len(emails_orm)}[/yellow] emails\n")
        
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
    
    # Process in batches for efficiency
    batch_size = 10
    total_processed = 0
    total_labeled = 0
    label_counts = {}
    
    for i in range(0, len(emails), batch_size):
        batch = emails[i:i+batch_size]
        batch_start = time.time()
        
        # Analyze batch
        tasks = [ceo_assistant.analyze_for_ceo(email) for email in batch]
        analyses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        gmail_updates = []  # Collect Gmail updates
        
        for email, analysis in zip(batch, analyses):
            if isinstance(analysis, Exception) or 'error' in analysis:
                continue
            
            total_processed += 1
            
            # Get labels
            ceo_label_names = analysis.get('ceo_labels', [])
            if ceo_label_names:
                # Track label usage
                for label in ceo_label_names:
                    label_counts[label] = label_counts.get(label, 0) + 1
                
                # Prepare Gmail update if we have the message ID
                if email.message_id:
                    labels_to_add = []
                    for label_name in ceo_label_names:
                        full_label = f'EmailAgent/CEO/{label_name}'
                        if full_label in label_map:
                            labels_to_add.append(label_map[full_label])
                    
                    if 'EmailAgent/Processed' in label_map:
                        labels_to_add.append(label_map['EmailAgent/Processed'])
                    
                    if labels_to_add:
                        gmail_updates.append({
                            'message_id': email.message_id.strip('<>'),
                            'labels': labels_to_add,
                            'email_id': email.id
                        })
            
            # Update database immediately
            with db.get_session() as session:
                from email_agent.storage.models import EmailORM
                email_orm = session.query(EmailORM).filter_by(id=email.id).first()
                if email_orm:
                    current_tags = json.loads(email_orm.tags) if isinstance(email_orm.tags, str) else (email_orm.tags or [])
                    if 'ceo_processed' not in current_tags:
                        current_tags.append('ceo_processed')
                    email_orm.tags = json.dumps(current_tags)
                    session.commit()
        
        # Batch apply Gmail labels (more efficient)
        if gmail_updates:
            for update in gmail_updates:
                try:
                    query = f'rfc822msgid:{update["message_id"]}'
                    results = service.users().messages().list(userId='me', q=query).execute()
                    
                    if results.get('messages'):
                        gmail_msg_id = results['messages'][0]['id']
                        body = {'addLabelIds': update['labels']}
                        service.users().messages().modify(
                            userId='me', id=gmail_msg_id, body=body
                        ).execute()
                        total_labeled += 1
                except:
                    pass  # Skip Gmail errors silently
        
        # Progress update
        batch_time = time.time() - batch_start
        rate = len(batch) / batch_time
        console.print(f"Batch {i//batch_size + 1}: {len(batch)} emails in {batch_time:.1f}s ({rate:.1f} emails/sec)")
        
        # Small delay between batches
        await asyncio.sleep(0.1)
    
    # Final statistics
    elapsed = time.time() - start_time
    
    console.print(f"\n[bold green]✅ Processing Complete![/bold green]")
    console.print(f"⏱️  Time: {elapsed:.1f} seconds ({total_processed/elapsed:.1f} emails/sec)")
    console.print(f"📊 Processed: {total_processed} emails")
    console.print(f"🏷️  Labeled in Gmail: {total_labeled} emails")
    
    # Label distribution
    if label_counts:
        console.print("\n[bold]Label Distribution:[/bold]")
        sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)
        for label, count in sorted_labels[:10]:
            bar = "█" * (count // 5) if count >= 5 else "▌"
            console.print(f"  {label:<20} {bar} {count}")

if __name__ == "__main__":
    limit = 500
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    
    asyncio.run(fast_process_ceo_emails(limit))