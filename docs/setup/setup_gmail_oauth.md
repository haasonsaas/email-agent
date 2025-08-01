# Gmail OAuth Setup Guide

## Project Information
- **Project ID**: `email-agent-1754023493`
- **Project Name**: Email Agent Project
- **APIs Enabled**: ✅ Gmail API, ✅ People API

## Manual Setup Steps Required

### 1. Configure OAuth Consent Screen

Visit: https://console.cloud.google.com/apis/credentials/consent/edit?project=email-agent-1754023493

**OAuth Consent Screen Configuration:**
- **User Type**: External (for personal Gmail accounts)
- **Application Name**: Email Agent
- **User Support Email**: jonathan@haas.holdings  
- **Application Homepage**: https://github.com/your-username/email-agent
- **Application Privacy Policy**: (can be same as homepage for now)
- **Application Terms of Service**: (can be same as homepage for now)
- **Authorized Domains**: (leave empty for testing)
- **Developer Contact Email**: jonathan@haas.holdings

**Scopes to Add:**
```
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/gmail.modify
https://www.googleapis.com/auth/userinfo.email
https://www.googleapis.com/auth/userinfo.profile
```

**Test Users** (for development):
- Add: jonathan@haas.holdings

### 2. Create OAuth 2.0 Credentials

Visit: https://console.cloud.google.com/apis/credentials?project=email-agent-1754023493

1. Click **"+ CREATE CREDENTIALS"**
2. Select **"OAuth 2.0 Client IDs"**
3. Choose **"Desktop application"**
4. Name: `Email Agent Desktop Client`
5. Click **"Create"**

### 3. Download Credentials

After creating the OAuth client:
1. Click the download button (⬇️) next to your new OAuth client
2. Save the JSON file as `client_credentials.json` in the email_agent directory
3. The file should contain:
   ```json
   {
     "installed": {
       "client_id": "your-client-id.apps.googleusercontent.com",
       "client_secret": "your-client-secret",
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://oauth2.googleapis.com/token",
       ...
     }
   }
   ```

## Quick Links

- **Project Console**: https://console.cloud.google.com/home/dashboard?project=email-agent-1754023493
- **OAuth Consent Screen**: https://console.cloud.google.com/apis/credentials/consent?project=email-agent-1754023493
- **Credentials**: https://console.cloud.google.com/apis/credentials?project=email-agent-1754023493
- **Gmail API**: https://console.cloud.google.com/apis/api/gmail.googleapis.com?project=email-agent-1754023493

## After Manual Setup

Once you have the `client_credentials.json` file, run:

```bash
cd /Users/jonathanhaas/email_agent
python setup_credentials.py
```

This will configure Email Agent with your new Gmail credentials.