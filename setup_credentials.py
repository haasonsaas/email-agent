#!/usr/bin/env python3
"""Setup script to configure Gmail credentials for Email Agent."""

import json
import os
import sys
from pathlib import Path

def main():
    """Main setup function."""
    print("🔧 Email Agent - Gmail Credentials Setup")
    print("=" * 50)
    
    # Check for credentials file
    creds_file = Path("client_credentials.json")
    if not creds_file.exists():
        print("❌ client_credentials.json not found!")
        print("\nPlease follow these steps:")
        print("1. Open: https://console.cloud.google.com/apis/credentials?project=email-agent-1754023493")
        print("2. Create OAuth 2.0 Client ID (Desktop application)")
        print("3. Download the JSON file and save it as 'client_credentials.json' in this directory")
        print("4. Run this script again")
        return 1
    
    try:
        # Load credentials
        with open(creds_file) as f:
            creds_data = json.load(f)
        
        # Extract client info
        if "installed" in creds_data:
            client_info = creds_data["installed"]
        elif "web" in creds_data:
            client_info = creds_data["web"]
        else:
            print("❌ Invalid credentials file format!")
            return 1
        
        client_id = client_info.get("client_id")
        client_secret = client_info.get("client_secret")
        
        if not client_id or not client_secret:
            print("❌ Missing client_id or client_secret in credentials file!")
            return 1
        
        print(f"✅ Found credentials:")
        print(f"   Client ID: {client_id[:20]}...")
        print(f"   Client Secret: {client_secret[:10]}...")
        
        # Create or update .env file
        env_file = Path(".env")
        env_content = []
        
        if env_file.exists():
            with open(env_file) as f:
                env_content = f.read().splitlines()
        
        # Update or add Google credentials
        google_client_id_set = False
        google_client_secret_set = False
        
        new_content = []
        for line in env_content:
            if line.startswith("GOOGLE_CLIENT_ID="):
                new_content.append(f"GOOGLE_CLIENT_ID={client_id}")
                google_client_id_set = True
            elif line.startswith("GOOGLE_CLIENT_SECRET="):
                new_content.append(f"GOOGLE_CLIENT_SECRET={client_secret}")
                google_client_secret_set = True
            else:
                new_content.append(line)
        
        # Add missing credentials
        if not google_client_id_set:
            new_content.append(f"GOOGLE_CLIENT_ID={client_id}")
        
        if not google_client_secret_set:
            new_content.append(f"GOOGLE_CLIENT_SECRET={client_secret}")
        
        # Write updated .env file
        with open(env_file, 'w') as f:
            f.write('\n'.join(new_content) + '\n')
        
        print(f"✅ Updated {env_file} with Gmail credentials")
        
        # Test the setup
        print("\n🧪 Testing Email Agent setup...")
        
        try:
            # Import and test
            sys.path.insert(0, str(Path("src")))
            from email_agent.connectors.gmail import GmailConnector
            
            # Create test connector
            config = {
                "client_id": client_id,
                "client_secret": client_secret
            }
            
            connector = GmailConnector(config)
            print("✅ Gmail connector created successfully")
            
            print("\n🎉 Setup completed successfully!")
            print("\nNext steps:")
            print("1. Run: email-agent init setup")
            print("2. Add Gmail connector: email-agent config add-connector gmail")
            print("3. Test connection: email-agent pull test gmail")
            print("4. Pull emails: email-agent pull --since yesterday")
            
            # Clean up sensitive file
            if input("\n🗑️  Remove client_credentials.json? (recommended) [y/N]: ").lower() == 'y':
                creds_file.unlink()
                print("✅ Removed client_credentials.json")
            
            return 0
            
        except ImportError as e:
            print(f"⚠️  Email Agent modules not found: {e}")
            print("Make sure you're in the correct directory and have installed dependencies")
            return 1
        except Exception as e:
            print(f"⚠️  Setup test failed: {e}")
            print("Credentials were saved but there may be an issue with the setup")
            return 1
    
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())