#!/usr/bin/env python3
"""Create the new Receipts label."""

import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import keyring

# Load credentials
creds_json = keyring.get_password("email_agent", "gmail_credentials_default")
if not creds_json:
    print("❌ No credentials found")
    exit(1)

creds_data = json.loads(creds_json)
creds = Credentials.from_authorized_user_info(creds_data, [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
])

if creds.expired and creds.refresh_token:
    creds.refresh(Request())

service = build('gmail', 'v1', credentials=creds)

# Create Receipts label
try:
    label_body = {
        'name': 'EmailAgent/Receipts',
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show',
        'color': {
            'backgroundColor': '#666666',
            'textColor': '#ffffff'
        }
    }
    
    result = service.users().labels().create(userId='me', body=label_body).execute()
    print(f"✅ Created label: EmailAgent/Receipts (ID: {result['id']})")
except Exception as e:
    if "already exists" in str(e):
        print("✓ Label already exists: EmailAgent/Receipts")
    else:
        print(f"❌ Failed to create label: {e}")