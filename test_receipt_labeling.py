#!/usr/bin/env python3
"""Test the improved receipt labeling system."""

import asyncio
import json
from email_agent.agents.action_extractor import ActionExtractorAgent
from email_agent.storage.database import DatabaseManager
from email_agent.models import Email, EmailAddress, EmailCategory, EmailPriority
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import keyring
from rich.console import Console
from rich.table import Table

console = Console()

async def test_receipt_labeling(limit: int = 10):
    """Test improved labeling on a small batch, focusing on receipt detection."""
    
    console.print("[bold cyan]🧪 Testing Improved Receipt Labeling[/bold cyan]")
    console.print("=" * 50)
    
    # Initialize components
    db = DatabaseManager()
    extractor = ActionExtractorAgent()
    
    # Get recent emails containing common receipt keywords
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        
        # Look for emails with receipt-like subjects
        query = session.query(EmailORM).filter(
            EmailORM.subject.ilike('%receipt%') |
            EmailORM.subject.ilike('%transaction%') |
            EmailORM.subject.ilike('%order%') |
            EmailORM.subject.ilike('%payment%') |
            EmailORM.subject.ilike('%card%') |
            EmailORM.subject.ilike('%purchase%')
        ).order_by(EmailORM.received_date.desc()).limit(limit)
        
        emails_orm = query.all()
        
        console.print(f"\n📧 Found [yellow]{len(emails_orm)}[/yellow] potential receipt emails")
        
        if not emails_orm:
            console.print("[yellow]No receipt-like emails found. Testing with general emails instead.[/yellow]")
            # Fall back to any recent emails
            emails_orm = session.query(EmailORM).order_by(EmailORM.received_date.desc()).limit(limit).all()
        
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
    
    # Get label IDs
    results = service.users().labels().list(userId='me').execute()
    label_map = {label['name']: label['id'] for label in results.get('labels', [])}
    
    # Create result table
    table = Table(title="Email Analysis Results", show_header=True, header_style="bold cyan")
    table.add_column("Email Subject", style="cyan", width=40)
    table.add_column("Type", style="yellow", width=12)
    table.add_column("Urgency", style="green", width=10)
    table.add_column("Labels Applied", style="magenta", width=30)
    
    console.print("\n🔍 Analyzing emails...\n")
    
    # Process emails
    for email in emails:
        actions = await extractor.extract_actions(email)
        
        # Determine labels
        labels_applied = []
        
        # Check if it's a receipt
        email_type = actions.get('email_type', 'unknown')
        response_urgency = actions.get('response_urgency', 'low')
        
        if email_type == 'receipt':
            labels_applied.append('Receipts')
        else:
            if response_urgency == 'urgent':
                labels_applied.append('HighPriority')
            
            if actions.get('meeting_requests'):
                labels_applied.append('Meeting')
            
            if any(item.get('deadline') for item in actions.get('action_items', [])):
                labels_applied.append('Deadline')
            
            if actions.get('commitments_made'):
                labels_applied.append('Commitment')
            
            if actions.get('waiting_for'):
                labels_applied.append('WaitingFor')
        
        # Add to table
        subject_display = email.subject[:37] + "..." if len(email.subject) > 40 else email.subject
        labels_display = ", ".join(labels_applied) if labels_applied else "None"
        
        table.add_row(
            subject_display,
            email_type,
            response_urgency,
            labels_display
        )
        
        # Actually apply labels in Gmail
        if email.message_id and labels_applied:
            try:
                msg_id = email.message_id.strip('<>')
                query = f'rfc822msgid:{msg_id}'
                results = service.users().messages().list(userId='me', q=query).execute()
                
                if results.get('messages'):
                    gmail_msg_id = results['messages'][0]['id']
                    
                    label_ids = []
                    for label in labels_applied:
                        full_label = f'EmailAgent/{label}' if label != 'Receipts' else 'EmailAgent/Receipts'
                        if label == 'HighPriority':
                            full_label = 'EmailAgent/Actions/HighPriority'
                        elif label == 'Meeting':
                            full_label = 'EmailAgent/Actions/MeetingRequest'
                        elif label == 'Deadline':
                            full_label = 'EmailAgent/Actions/Deadline'
                        elif label == 'Commitment':
                            full_label = 'EmailAgent/Actions/Commitment'
                        elif label == 'WaitingFor':
                            full_label = 'EmailAgent/Actions/WaitingFor'
                        
                        if full_label in label_map:
                            label_ids.append(label_map[full_label])
                    
                    # Always add processed label
                    if 'EmailAgent/Processed' in label_map:
                        label_ids.append(label_map['EmailAgent/Processed'])
                    
                    if label_ids:
                        body = {'addLabelIds': label_ids}
                        service.users().messages().modify(
                            userId='me', id=gmail_msg_id, body=body
                        ).execute()
            except Exception as e:
                if "notFound" not in str(e):
                    console.print(f"[dim]Failed to apply labels for: {email.subject[:30]}[/dim]")
    
    console.print(table)
    
    console.print("\n[bold green]✅ Test Complete![/bold green]")
    console.print("\n💡 Key improvements:")
    console.print("  • Receipt emails now get 'Receipts' label instead of 'HighPriority'")
    console.print("  • Only truly urgent emails get marked as high priority")
    console.print("  • Better differentiation between transactional and actionable emails")

if __name__ == "__main__":
    asyncio.run(test_receipt_labeling())