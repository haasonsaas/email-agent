"""Gmail connector implementation."""

import base64
import email
import json
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import keyring
from google.auth import exceptions as google_exceptions
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..models import Email, EmailAddress, EmailAttachment, EmailCategory
from ..sdk.base import BaseConnector
from ..sdk.exceptions import AuthenticationError, ConnectorError, RateLimitError


class GmailConnector(BaseConnector):
    """Gmail API connector for email operations."""
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.service = None
        self.credentials = None
        self.user_email = None
    
    @property
    def connector_type(self) -> str:
        return "gmail"
    
    @property
    def supports_push(self) -> bool:
        return True
    
    async def authenticate(self) -> bool:
        """Authenticate with Gmail API using OAuth2."""
        try:
            # Try to load existing credentials
            creds = self._load_credentials()
            
            # If there are no (valid) credentials available, request authorization
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        self._save_credentials(creds)
                    except google_exceptions.RefreshError:
                        creds = self._request_new_credentials()
                else:
                    creds = self._request_new_credentials()
            
            self.credentials = creds
            self.service = build('gmail', 'v1', credentials=creds)
            
            # Get user profile to verify authentication
            profile = self.service.users().getProfile(userId='me').execute()
            self.user_email = profile.get('emailAddress')
            self.authenticated = True
            
            return True
            
        except Exception as e:
            raise AuthenticationError(f"Gmail authentication failed: {str(e)}")
    
    def _load_credentials(self) -> Optional[Credentials]:
        """Load credentials from keyring."""
        try:
            creds_json = keyring.get_password("email_agent", f"gmail_credentials_{self.user_email or 'default'}")
            if creds_json:
                creds_data = json.loads(creds_json)
                return Credentials.from_authorized_user_info(creds_data, self.SCOPES)
        except Exception:
            pass
        return None
    
    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to keyring."""
        try:
            creds_json = creds.to_json()
            keyring.set_password("email_agent", f"gmail_credentials_{self.user_email or 'default'}", creds_json)
        except Exception as e:
            raise ConnectorError(f"Failed to save credentials: {str(e)}")
    
    def _request_new_credentials(self) -> Credentials:
        """Request new credentials via OAuth flow."""
        client_id = self.config.get('client_id')
        client_secret = self.config.get('client_secret')
        
        if not client_id or not client_secret:
            raise AuthenticationError("Gmail client_id and client_secret must be provided in config")
        
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
            }
        }
        
        flow = InstalledAppFlow.from_client_config(client_config, self.SCOPES)
        creds = flow.run_local_server(port=0)
        self._save_credentials(creds)
        return creds
    
    async def pull(self, since: Optional[datetime] = None) -> List[Email]:
        """Pull emails from Gmail."""
        if not self.authenticated:
            await self.authenticate()
        
        try:
            # Build query
            query = ""
            if since:
                query = f"after:{int(since.timestamp())}"
            
            # Get message list
            result = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=self.config.get('max_results', 100)
            ).execute()
            
            messages = result.get('messages', [])
            emails = []
            
            for msg in messages:
                try:
                    email_obj = await self._fetch_email(msg['id'])
                    if email_obj:
                        emails.append(email_obj)
                except Exception as e:
                    # Log error but continue processing other emails
                    print(f"Error processing email {msg['id']}: {str(e)}")
                    continue
            
            return emails
            
        except HttpError as e:
            if e.resp.status == 429:
                raise RateLimitError("Gmail API rate limit exceeded")
            raise ConnectorError(f"Gmail API error: {str(e)}")
        except Exception as e:
            raise ConnectorError(f"Failed to pull emails: {str(e)}")
    
    async def _fetch_email(self, message_id: str) -> Optional[Email]:
        """Fetch a single email by ID."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            return self._parse_message(message)
            
        except HttpError as e:
            if e.resp.status == 404:
                return None
            raise ConnectorError(f"Failed to fetch email {message_id}: {str(e)}")
    
    def _parse_message(self, message: Dict[str, Any]) -> Email:
        """Parse Gmail message into Email object."""
        headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
        
        # Extract basic info
        message_id = headers.get('Message-ID', message['id'])
        thread_id = message.get('threadId')
        subject = headers.get('Subject', '(No Subject)')
        
        # Parse sender
        sender_str = headers.get('From', '')
        sender = self._parse_email_address(sender_str)
        
        # Parse recipients
        recipients = self._parse_email_addresses(headers.get('To', ''))
        cc = self._parse_email_addresses(headers.get('Cc', ''))
        bcc = self._parse_email_addresses(headers.get('Bcc', ''))
        
        # Parse dates
        date_str = headers.get('Date')
        date = self._parse_date(date_str) if date_str else datetime.now(timezone.utc)
        
        # Extract body and attachments
        body_text, body_html, attachments = self._extract_content(message['payload'])
        
        # Determine read status
        is_read = 'UNREAD' not in message.get('labelIds', [])
        is_flagged = 'STARRED' in message.get('labelIds', [])
        
        # Initial categorization based on labels
        category = self._infer_category(message.get('labelIds', []))
        
        return Email(
            id=message['id'],
            message_id=message_id,
            thread_id=thread_id,
            subject=subject,
            sender=sender,
            recipients=recipients,
            cc=cc,
            bcc=bcc,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            date=date,
            received_date=date,
            is_read=is_read,
            is_flagged=is_flagged,
            category=category,
            raw_headers=headers,
            connector_data={'gmail_labels': message.get('labelIds', [])}
        )
    
    def _parse_email_address(self, addr_str: str) -> EmailAddress:
        """Parse an email address string."""
        if not addr_str:
            return EmailAddress(email="", name=None)
        
        try:
            parsed = email.utils.parseaddr(addr_str)
            name = parsed[0] if parsed[0] else None
            email_addr = parsed[1] if parsed[1] else addr_str
            return EmailAddress(email=email_addr, name=name)
        except Exception:
            return EmailAddress(email=addr_str, name=None)
    
    def _parse_email_addresses(self, addrs_str: str) -> List[EmailAddress]:
        """Parse multiple email addresses."""
        if not addrs_str:
            return []
        
        try:
            addresses = email.utils.getaddresses([addrs_str])
            return [EmailAddress(email=addr[1], name=addr[0] if addr[0] else None) 
                   for addr in addresses if addr[1]]
        except Exception:
            return [EmailAddress(email=addrs_str, name=None)]
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse email date string."""
        try:
            parsed_date = email.utils.parsedate_to_datetime(date_str)
            return parsed_date.astimezone(timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)
    
    def _extract_content(self, payload: Dict[str, Any]) -> tuple[Optional[str], Optional[str], List[EmailAttachment]]:
        """Extract body text, HTML, and attachments from message payload."""
        body_text = None
        body_html = None
        attachments = []
        
        def process_part(part):
            nonlocal body_text, body_html
            
            mime_type = part.get('mimeType', '')
            
            if mime_type == 'text/plain':
                data = part.get('body', {}).get('data')
                if data:
                    body_text = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
            elif mime_type == 'text/html':
                data = part.get('body', {}).get('data')
                if data:
                    body_html = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            
            elif part.get('filename'):
                # This is an attachment
                attachment = EmailAttachment(
                    filename=part['filename'],
                    content_type=mime_type,
                    size=part.get('body', {}).get('size', 0),
                    content_id=None,  # Could extract from headers if needed
                    inline=False
                )
                attachments.append(attachment)
            
            # Process sub-parts recursively
            for sub_part in part.get('parts', []):
                process_part(sub_part)
        
        process_part(payload)
        
        return body_text, body_html, attachments
    
    def _infer_category(self, label_ids: List[str]) -> EmailCategory:
        """Infer category from Gmail labels."""
        if 'CATEGORY_SOCIAL' in label_ids:
            return EmailCategory.SOCIAL
        elif 'CATEGORY_PROMOTIONS' in label_ids:
            return EmailCategory.PROMOTIONS
        elif 'CATEGORY_UPDATES' in label_ids:
            return EmailCategory.UPDATES
        elif 'CATEGORY_FORUMS' in label_ids:
            return EmailCategory.FORUMS
        elif 'SPAM' in label_ids:
            return EmailCategory.SPAM
        else:
            return EmailCategory.PRIMARY
    
    async def get_email(self, email_id: str) -> Optional[Email]:
        """Get a specific email by ID."""
        return await self._fetch_email(email_id)
    
    async def mark_read(self, email_id: str) -> bool:
        """Mark an email as read."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except HttpError:
            return False
    
    async def mark_unread(self, email_id: str) -> bool:
        """Mark an email as unread."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            return True
        except HttpError:
            return False
    
    async def archive(self, email_id: str) -> bool:
        """Archive an email."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=email_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            return True
        except HttpError:
            return False
    
    async def delete(self, email_id: str) -> bool:
        """Delete an email."""
        try:
            self.service.users().messages().trash(
                userId='me',
                id=email_id
            ).execute()
            return True
        except HttpError:
            return False