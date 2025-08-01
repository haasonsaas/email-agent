#!/usr/bin/env python3
"""Direct test of Gmail label creation."""

import asyncio
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import keyring
import json

async def test_gmail_labels():
    """Test Gmail label creation directly."""
    
    print("🏷️  Testing Gmail Label Creation")
    print("=" * 50)
    
    # Load credentials from keyring
    creds_json = keyring.get_password("email_agent", "gmail_credentials_default")
    if not creds_json:
        # Try user-specific key
        creds_json = keyring.get_password("email_agent", "gmail_credentials_jonathan@haas.holdings")
    
    if not creds_json:
        print("❌ No credentials found. Run authenticate_gmail.py first.")
        return
    
    creds_data = json.loads(creds_json)
    creds = Credentials.from_authorized_user_info(creds_data, [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ])
    
    # Refresh if needed
    if creds.expired and creds.refresh_token:
        print("🔄 Refreshing credentials...")
        creds.refresh(Request())
        # Save refreshed credentials
        keyring.set_password("email_agent", "gmail_credentials_default", creds.to_json())
    
    # Build Gmail service
    service = build('gmail', 'v1', credentials=creds)
    
    # Test label creation with Gmail's allowed color palette
    action_labels = {
        'EmailAgent/Actions/HighPriority': 'fb4c2f',  # Red
        'EmailAgent/Actions/MeetingRequest': '1c4587',  # Blue
        'EmailAgent/Actions/Deadline': 'ffad47',  # Orange
        'EmailAgent/Actions/WaitingFor': 'fad165',  # Yellow
        'EmailAgent/Actions/Commitment': '8e63ce',  # Purple
        'EmailAgent/Processed': '16a766'  # Green
    }
    
    created = 0
    existing = 0
    
    # First, list existing labels
    try:
        results = service.users().labels().list(userId='me').execute()
        existing_labels = {label['name']: label['id'] for label in results.get('labels', [])}
        print(f"\n📋 Found {len(existing_labels)} existing labels")
    except Exception as e:
        print(f"❌ Failed to list labels: {e}")
        return
    
    # Create or verify each label
    for label_name, color in action_labels.items():
        try:
            if label_name in existing_labels:
                print(f"✓ Label exists: {label_name}")
                existing += 1
            else:
                label_body = {
                    'name': label_name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show',
                    'color': {
                        'backgroundColor': f'#{color}',
                        'textColor': '#ffffff'
                    }
                }
                
                result = service.users().labels().create(userId='me', body=label_body).execute()
                print(f"✅ Created label: {label_name} (ID: {result['id']})")
                created += 1
                
        except Exception as e:
            print(f"❌ Failed to create {label_name}: {e}")
    
    print(f"\n📊 Summary:")
    print(f"   Created: {created} new labels")
    print(f"   Existing: {existing} labels already present")
    print(f"   Total: {created + existing}/{len(action_labels)} labels ready")
    
    # Test applying a label to an email
    if created + existing > 0:
        print("\n🧪 Testing label application...")
        try:
            # Get a recent email
            messages = service.users().messages().list(userId='me', maxResults=1).execute()
            if messages.get('messages'):
                msg_id = messages['messages'][0]['id']
                
                # Apply the "Processed" label if it exists
                processed_label_id = existing_labels.get('EmailAgent/Processed')
                if processed_label_id:
                    body = {'addLabelIds': [processed_label_id]}
                    service.users().messages().modify(userId='me', id=msg_id, body=body).execute()
                    print(f"✅ Successfully applied 'EmailAgent/Processed' label to message {msg_id}")
                else:
                    print("⚠️  'EmailAgent/Processed' label not found")
            else:
                print("⚠️  No messages found to test with")
                
        except Exception as e:
            print(f"❌ Label application test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_gmail_labels())