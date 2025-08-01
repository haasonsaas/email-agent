#!/usr/bin/env python3
"""Test complete email processing flow with Gmail labels."""

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

async def test_complete_flow():
    """Test the complete flow: extract actions and apply Gmail labels."""
    
    print("🚀 Complete Email Agent Flow Test")
    print("=" * 50)
    
    # 1. Get some emails from database
    db = DatabaseManager()
    extractor = ActionExtractorAgent()
    
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        # Get emails that don't have action_processed tag
        emails_orm = session.query(EmailORM).filter(
            ~EmailORM.tags.like('%action_processed%')
        ).limit(5).all()
        
        print(f"\n📧 Found {len(emails_orm)} unprocessed emails")
        
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
    
    # 2. Extract actions from emails
    print("\n🔍 Extracting actions from emails...")
    
    # Load Gmail credentials
    creds_json = keyring.get_password("email_agent", "gmail_credentials_default")
    if not creds_json:
        print("❌ No Gmail credentials found")
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
    
    print(f"\n🏷️  Found {len([l for l in label_map if l.startswith('EmailAgent/')])} EmailAgent labels")
    
    # Process each email
    processed = 0
    for email in emails[:3]:  # Process first 3
        print(f"\n📧 Processing: {email.subject[:50]}...")
        print(f"   From: {email.sender.email}")
        
        # Extract actions
        actions = await extractor.extract_actions(email)
        
        if 'error' not in actions:
            # Determine which labels to apply
            labels_to_add = []
            
            if actions.get('response_urgency') == 'urgent':
                if 'EmailAgent/Actions/HighPriority' in label_map:
                    labels_to_add.append(label_map['EmailAgent/Actions/HighPriority'])
                    print("   🔴 High Priority")
            
            if actions.get('meeting_requests'):
                if 'EmailAgent/Actions/MeetingRequest' in label_map:
                    labels_to_add.append(label_map['EmailAgent/Actions/MeetingRequest'])
                    print("   📅 Meeting Request")
            
            if any(item.get('deadline') for item in actions.get('action_items', [])):
                if 'EmailAgent/Actions/Deadline' in label_map:
                    labels_to_add.append(label_map['EmailAgent/Actions/Deadline'])
                    print("   ⏰ Has Deadline")
            
            if actions.get('waiting_for'):
                if 'EmailAgent/Actions/WaitingFor' in label_map:
                    labels_to_add.append(label_map['EmailAgent/Actions/WaitingFor'])
                    print("   ⏳ Waiting For Response")
            
            if actions.get('commitments_made'):
                if 'EmailAgent/Actions/Commitment' in label_map:
                    labels_to_add.append(label_map['EmailAgent/Actions/Commitment'])
                    print("   🤝 Contains Commitment")
            
            # Always add processed label
            if 'EmailAgent/Processed' in label_map:
                labels_to_add.append(label_map['EmailAgent/Processed'])
            
            # Apply labels if we have the message ID
            if email.message_id and labels_to_add:
                try:
                    # Gmail message IDs in database might have angle brackets
                    msg_id = email.message_id.strip('<>')
                    
                    # Search for the message by Message-ID header
                    query = f'rfc822msgid:{msg_id}'
                    results = service.users().messages().list(userId='me', q=query).execute()
                    
                    if results.get('messages'):
                        gmail_msg_id = results['messages'][0]['id']
                        
                        body = {'addLabelIds': labels_to_add}
                        service.users().messages().modify(
                            userId='me', id=gmail_msg_id, body=body
                        ).execute()
                        
                        print(f"   ✅ Applied {len(labels_to_add)} labels in Gmail")
                        processed += 1
                    else:
                        print(f"   ⚠️  Message not found in Gmail")
                except Exception as e:
                    print(f"   ❌ Failed to apply labels: {e}")
            
            # Update database to mark as processed
            with db.get_session() as session:
                email_orm = session.query(EmailORM).filter_by(id=email.id).first()
                if email_orm:
                    current_tags = json.loads(email_orm.tags) if email_orm.tags else []
                    if 'action_processed' not in current_tags:
                        current_tags.append('action_processed')
                    email_orm.tags = json.dumps(current_tags)
                    session.commit()
        else:
            print(f"   ❌ Error extracting actions: {actions['error']}")
    
    print(f"\n✅ Complete! Processed {processed} emails with Gmail labels")
    print("\n📌 Check your Gmail to see the applied labels!")

if __name__ == "__main__":
    asyncio.run(test_complete_flow())