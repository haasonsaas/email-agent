#!/usr/bin/env python3
"""Script to authenticate Gmail and test label creation."""

import asyncio
import json
from email_agent.connectors.gmail import GmailConnector
from email_agent.connectors.gmail_service import GmailService
from email_agent.storage.database import DatabaseManager

async def authenticate_gmail():
    """Authenticate Gmail and create labels."""
    
    print("🔐 Gmail Authentication & Label Setup")
    print("=" * 50)
    
    # Get Gmail connector config
    db = DatabaseManager()
    with db.get_session() as session:
        from email_agent.storage.models import ConnectorConfigORM
        connector_orm = session.query(ConnectorConfigORM).filter_by(type='gmail').first()
        
        if not connector_orm:
            print("❌ No Gmail connector found. Please run: email-agent config add-connector gmail")
            return
        
        config = json.loads(connector_orm.config) if isinstance(connector_orm.config, str) else connector_orm.config
    
    # Initialize Gmail connector
    print("\n📧 Initializing Gmail connector...")
    gmail = GmailConnector(config)
    
    try:
        # Authenticate
        print("\n🔑 Authenticating with Gmail...")
        print("   This will open your browser for OAuth authorization.")
        print("   Please authorize the Email Agent to access your Gmail.")
        
        authenticated = await gmail.authenticate()
        
        if authenticated:
            print("\n✅ Successfully authenticated with Gmail!")
            
            # Get user email
            service = gmail.service
            profile = service.users().getProfile(userId='me').execute()
            email_address = profile.get('emailAddress', 'Unknown')
            print(f"   Authenticated as: {email_address}")
            
            # Now test Gmail service with labels
            print("\n🏷️  Setting up Gmail labels...")
            
            # Get credentials for GmailService
            creds = gmail.credentials
            creds_dict = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            }
            
            gmail_service = GmailService(creds_dict)
            if gmail_service.authenticate():
                labels = await gmail_service.create_action_labels()
                
                print("\n✅ Created/verified Gmail labels:")
                for label_name in labels:
                    print(f"   • {label_name}")
                
                print(f"\n📊 Total labels ready: {len(labels)}")
                
                # Test fetching some emails
                print("\n📥 Testing email fetch...")
                from datetime import datetime, timedelta
                since = datetime.now() - timedelta(days=1)
                emails = await gmail.pull(since=since)
                print(f"   Fetched {len(emails[:5])} recent emails (showing first 5)")
                
                return True
            else:
                print("❌ Failed to initialize Gmail service")
                return False
        else:
            print("❌ Authentication failed")
            return False
            
    except Exception as e:
        print(f"\n❌ Error during authentication: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(authenticate_gmail())
    
    if success:
        print("\n🎉 Gmail is now configured and ready!")
        print("\nYou can now run:")
        print("  email-agent smart-actions --apply-labels")
        print("  email-agent sync")
        print("\nTo see the labels in Gmail:")
        print("  1. Open Gmail in your browser")
        print("  2. Look for 'EmailAgent' labels in the left sidebar")
    else:
        print("\n❌ Setup failed. Please check the error messages above.")