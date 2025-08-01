#!/usr/bin/env python3
"""Create remaining CEO labels that failed earlier."""

import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import keyring

# Labels that failed - trying one by one
failed_labels = [
    ('EmailAgent/CEO/Customers', '16a766'),
    ('EmailAgent/CEO/Metrics', 'fad165'),
    ('EmailAgent/CEO/Legal', '8e63ce'),
    ('EmailAgent/CEO/Finance', '16a766'),
    ('EmailAgent/CEO/Product', '1c4587'),
    ('EmailAgent/CEO/Vendors', 'fb4c2f'),
    ('EmailAgent/CEO/SignatureRequired', 'ffad47'),
    ('EmailAgent/CEO/KeyRelationships', '8e63ce'),
    ('EmailAgent/CEO/QuickWins', '16a766'),
    ('EmailAgent/CEO/DeepWork', '8e63ce'),
]

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

# Try creating each label
for label_name, color in failed_labels:
    try:
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
        print(f"✅ Created: {label_name}")
    except Exception as e:
        if "already exists" in str(e):
            print(f"✓ Already exists: {label_name}")
        else:
            # Try without color
            try:
                label_body = {
                    'name': label_name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show'
                }
                result = service.users().labels().create(userId='me', body=label_body).execute()
                print(f"✅ Created without color: {label_name}")
            except Exception as e2:
                print(f"❌ Failed: {label_name} - {str(e2)[:50]}")

print("\n✨ Label creation complete!")