"""Enhanced Gmail service with advanced SDK features."""

import logging
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from ..models import Email
from ..config import settings

logger = logging.getLogger(__name__)


class GmailService:
    """Enhanced Gmail service with action-based features."""
    
    def __init__(self, credentials: Dict[str, Any]):
        self.credentials = credentials
        self.service = None
        self._labels_cache = {}
        
    def authenticate(self) -> bool:
        """Authenticate with Gmail API."""
        try:
            creds = Credentials(
                token=self.credentials.get('access_token'),
                refresh_token=self.credentials.get('refresh_token'),
                token_uri=self.credentials.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=self.credentials.get('client_id'),
                client_secret=self.credentials.get('client_secret'),
                scopes=['https://www.googleapis.com/auth/gmail.readonly',
                       'https://www.googleapis.com/auth/gmail.modify']
            )
            
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                
            self.service = build('gmail', 'v1', credentials=creds)
            self._refresh_labels_cache()
            return True
            
        except Exception as e:
            logger.error(f"Gmail authentication failed: {e}")
            return False
    
    def _refresh_labels_cache(self):
        """Refresh the labels cache."""
        try:
            if self.service:
                labels_result = self.service.users().labels().list(userId='me').execute()
                self._labels_cache = {
                    label['name']: label['id'] 
                    for label in labels_result.get('labels', [])
                }
        except Exception as e:
            logger.error(f"Failed to refresh labels cache: {e}")
    
    async def create_action_labels(self) -> Dict[str, str]:
        """Create Gmail labels for action-based organization."""
        action_labels = {
            'EmailAgent/Actions/HighPriority': 'fb4c2f',  # Red
            'EmailAgent/Actions/MeetingRequest': '1c4587',  # Blue
            'EmailAgent/Actions/Deadline': 'ffad47',  # Orange
            'EmailAgent/Actions/WaitingFor': 'fad165',  # Yellow
            'EmailAgent/Actions/Commitment': '8e63ce',  # Purple
            'EmailAgent/Receipts': '666666',  # Gray
            'EmailAgent/Processed': '16a766'  # Green
        }
        
        created_labels = {}
        
        for label_name, color in action_labels.items():
            try:
                if label_name not in self._labels_cache:
                    label_body = {
                        'name': label_name,
                        'labelListVisibility': 'labelShow',
                        'messageListVisibility': 'show',
                        'color': {
                            'backgroundColor': f'#{color}',
                            'textColor': '#ffffff'
                        }
                    }
                    
                    result = self.service.users().labels().create(
                        userId='me', body=label_body
                    ).execute()
                    
                    created_labels[label_name] = result['id']
                    self._labels_cache[label_name] = result['id']
                    logger.info(f"Created Gmail label: {label_name}")
                else:
                    created_labels[label_name] = self._labels_cache[label_name]
                    
            except Exception as e:
                logger.error(f"Failed to create label {label_name}: {e}")
                
        return created_labels
    
    async def apply_action_labels(self, email_id: str, actions: Dict[str, Any]) -> bool:
        """Apply Gmail labels based on extracted actions."""
        try:
            labels_to_add = []
            
            # Check email type first
            email_type = actions.get('email_type', '')
            
            # Receipt emails get special handling
            if email_type == 'receipt' and 'EmailAgent/Receipts' in self._labels_cache:
                labels_to_add.append(self._labels_cache['EmailAgent/Receipts'])
                # Receipts typically don't need other action labels
            else:
                # High priority actions (but not for receipts)
                if actions.get('response_urgency') == 'urgent':
                    if 'EmailAgent/Actions/HighPriority' in self._labels_cache:
                        labels_to_add.append(self._labels_cache['EmailAgent/Actions/HighPriority'])
                
                # Meeting requests
                if actions.get('meeting_requests'):
                    if 'EmailAgent/Actions/MeetingRequest' in self._labels_cache:
                        labels_to_add.append(self._labels_cache['EmailAgent/Actions/MeetingRequest'])
                
                # Deadlines
                action_items = actions.get('action_items', [])
                has_deadlines = any(item.get('deadline') for item in action_items)
                if has_deadlines:
                    if 'EmailAgent/Actions/Deadline' in self._labels_cache:
                        labels_to_add.append(self._labels_cache['EmailAgent/Actions/Deadline'])
                
                # Waiting for
                if actions.get('waiting_for'):
                    if 'EmailAgent/Actions/WaitingFor' in self._labels_cache:
                        labels_to_add.append(self._labels_cache['EmailAgent/Actions/WaitingFor'])
                
                # Commitments
                if actions.get('commitments_made'):
                    if 'EmailAgent/Actions/Commitment' in self._labels_cache:
                        labels_to_add.append(self._labels_cache['EmailAgent/Actions/Commitment'])
            
            # Always mark as processed
            if 'EmailAgent/Processed' in self._labels_cache:
                labels_to_add.append(self._labels_cache['EmailAgent/Processed'])
            
            if labels_to_add:
                body = {'addLabelIds': labels_to_add}
                self.service.users().messages().modify(
                    userId='me', id=email_id, body=body
                ).execute()
                
                logger.info(f"Applied {len(labels_to_add)} labels to email {email_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to apply labels to email {email_id}: {e}")
            
        return False
    
    async def create_calendar_event(self, meeting_request: Dict[str, Any], email: Email) -> Optional[str]:
        """Create a calendar event from a meeting request."""
        try:
            # This would require calendar API integration
            # For now, we'll create a structured reminder
            {
                'summary': f"Meeting from: {email.subject}",
                'description': f"Meeting request from {email.sender.email}\n\nOriginal email: {email.body[:200]}...",
                'start': {
                    'dateTime': '2025-08-01T10:00:00-07:00',  # Would parse from meeting_request
                    'timeZone': 'America/Los_Angeles',
                },
                'end': {
                    'dateTime': '2025-08-01T11:00:00-07:00',
                    'timeZone': 'America/Los_Angeles',
                },
                'attendees': [
                    {'email': email.sender.email}
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }
            
            logger.info(f"Would create calendar event for meeting in email {email.id}")
            return "mock_event_id"
            
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
            return None
    
    async def generate_smart_reply(self, email: Email, actions: Dict[str, Any]) -> Optional[str]:
        """Generate smart reply suggestions based on email content and actions."""
        try:
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            
            # Determine reply type based on actions
            reply_context = []
            
            if actions.get('meeting_requests'):
                reply_context.append("This email contains meeting requests")
            
            if actions.get('action_items'):
                reply_context.append("This email contains action items")
            
            if actions.get('needs_response'):
                reply_context.append("This email requires a response")
            
            context_str = "; ".join(reply_context) if reply_context else "General email"
            
            prompt = f"""
            Generate a professional email reply for the following email:
            
            Subject: {email.subject}
            From: {email.sender.name or email.sender.email}
            Body: {email.body[:500]}...
            
            Context: {context_str}
            
            Reply should be:
            - Professional and concise
            - Address any action items or questions
            - Appropriate tone for business communication
            - Include next steps if applicable
            
            Generate only the email body, no subject line.
            """
            
            response = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are a professional email assistant. Generate appropriate email replies."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Failed to generate smart reply: {e}")
            return None
    
    async def create_follow_up_reminder(self, email: Email, deadline: str) -> bool:
        """Create a follow-up reminder for an email with deadline."""
        try:
            # This would integrate with a task management system
            # For now, we'll log the reminder
            logger.info(f"Follow-up reminder created for email {email.id} with deadline {deadline}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create follow-up reminder: {e}")
            return False
    
    async def archive_processed_emails(self, email_ids: List[str]) -> int:
        """Archive emails that have been fully processed."""
        archived_count = 0
        
        try:
            for email_id in email_ids:
                # Remove from inbox label
                body = {'removeLabelIds': ['INBOX']}
                self.service.users().messages().modify(
                    userId='me', id=email_id, body=body
                ).execute()
                archived_count += 1
                
            logger.info(f"Archived {archived_count} processed emails")
            
        except Exception as e:
            logger.error(f"Failed to archive emails: {e}")
            
        return archived_count
    
    async def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all messages in a thread for summarization."""
        try:
            thread = self.service.users().threads().get(
                userId='me', id=thread_id, format='full'
            ).execute()
            
            messages = []
            for message in thread.get('messages', []):
                messages.append({
                    'id': message['id'],
                    'snippet': message.get('snippet', ''),
                    'date': message.get('internalDate'),
                    'headers': {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
                })
            
            return messages
            
        except Exception as e:
            logger.error(f"Failed to get thread messages: {e}")
            return []
    
    async def get_status(self) -> Dict[str, Any]:
        """Get Gmail service status."""
        return {
            'authenticated': self.service is not None,
            'labels_cached': len(self._labels_cache),
            'service_type': 'gmail_enhanced'
        }