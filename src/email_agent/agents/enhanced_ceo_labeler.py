#!/usr/bin/env python3
"""Enhanced CEO email labeling with advanced intelligence based on deep analysis."""

import asyncio
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from .ceo_assistant import CEOAssistantAgent
from ..storage.database import DatabaseManager
from ..models import Email, EmailAddress, EmailCategory, EmailPriority
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import keyring
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel

console = Console()

@dataclass
class SenderProfile:
    """Profile for email sender reputation and context."""
    email: str
    name: str
    total_emails: int
    recent_emails: int
    strategic_importance: str  # critical, high, medium, low
    relationship_type: str  # board, investor, customer, team, vendor, unknown
    avg_response_time: Optional[int] = None
    last_interaction: Optional[datetime] = None
    importance_score: float = 0.0
    keywords: List[str] = None
    typical_labels: List[str] = None

@dataclass
class ThreadContext:
    """Context for email thread continuity."""
    thread_id: str
    participants: List[str]
    labels_applied: List[str]
    importance_level: str
    last_updated: datetime
    key_topics: List[str]

class EnhancedCEOLabeler:
    """Advanced CEO email labeling with relationship intelligence."""
    
    def __init__(self):
        self.console = Console()
        self.sender_profiles: Dict[str, SenderProfile] = {}
        self.thread_contexts: Dict[str, ThreadContext] = {}
        
        # Strategic relationship patterns (from deep analysis insights)
        self.board_patterns = [
            r'\b(?:board|director|chairman|chair)\b',
            r'\b(?:governance|board meeting|board deck)\b'
        ]
        
        self.investor_patterns = [
            r'\b(?:investor|investment|funding|venture|equity)\b',
            r'\b(?:due diligence|term sheet|cap table|valuation)\b',
            r'\b(?:series [a-z]|round|raise)\b'
        ]
        
        self.customer_patterns = [
            r'\b(?:customer|client|user|feedback)\b',
            r'\b(?:churn|retention|satisfaction|nps)\b',
            r'\b(?:feature request|bug report|support)\b'
        ]
        
        # High-value domains (from analysis)
        self.strategic_domains = {
            'haas.holdings': 'internal',
            'rippling.com': 'vendor_critical',
            'docusign.com': 'vendor_critical',
            'github.com': 'vendor_important', 
            'amazonaws.com': 'vendor_critical',
            'google.com': 'vendor_important',
            'apple.com': 'vendor_important',
            'microsoft.com': 'vendor_important'
        }
        
        # Known important contacts (would be populated from CRM/contacts)
        self.vip_contacts = {
            'jonathan@haas.holdings': {'type': 'founder', 'importance': 'critical'},
            # Would add board members, key investors, etc.
        }
        
        # Spam/promotional patterns (enhanced from improved labeler)
        self.spam_patterns = [
            r'\b(?:save|off|discount|deal|sale|limited time|expires|hurry|act now)\b',
            r'\b(?:free|bonus|gift|prize|winner|congratulations|lottery)\b',
            r'\b(?:unsubscribe|marketing|promotional|advertisement)\b',
            r'\b(?:newsletter|update|tips|guide|101|how to|best practices)\b',
            r'\b(?:webinar|demo|trial|get started|sign up|download)\b'
        ]

    async def build_sender_profiles(self, emails: List[Email]) -> None:
        """Build sender reputation profiles from email history."""
        console.print("🧠 Building sender intelligence profiles...")
        
        sender_stats = defaultdict(lambda: {
            'count': 0, 'recent_count': 0, 'subjects': [], 
            'keywords': Counter(), 'labels': Counter()
        })
        
        # Analyze historical patterns
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for email in emails:
            sender_key = email.sender.email.lower()
            sender_stats[sender_key]['count'] += 1
            sender_stats[sender_key]['subjects'].append(email.subject.lower())
            
            # Count as recent if within 30 days
            if email.received_date and email.received_date > cutoff_date:
                sender_stats[sender_key]['recent_count'] += 1
            
            # Extract keywords from subjects
            subject_words = re.findall(r'\b\w{4,}\b', email.subject.lower())
            for word in subject_words:
                sender_stats[sender_key]['keywords'][word] += 1
        
        # Build profiles
        for sender_email, stats in sender_stats.items():
            # Determine relationship type
            relationship_type = self._classify_relationship(sender_email, stats['subjects'])
            
            # Calculate importance score
            importance_score = self._calculate_importance_score(
                sender_email, stats['count'], stats['recent_count'], relationship_type
            )
            
            # Determine strategic importance
            strategic_importance = self._determine_strategic_importance(
                importance_score, relationship_type, sender_email
            )
            
            profile = SenderProfile(
                email=sender_email,
                name=sender_email.split('@')[0],  # Would get from contacts in real system
                total_emails=stats['count'],
                recent_emails=stats['recent_count'],
                strategic_importance=strategic_importance,
                relationship_type=relationship_type,
                importance_score=importance_score,
                keywords=list(stats['keywords'].most_common(5)),
                typical_labels=[]  # Would be populated from historical labeling
            )
            
            self.sender_profiles[sender_email] = profile
        
        console.print(f"  ✅ Created profiles for {len(self.sender_profiles)} senders")

    def _classify_relationship(self, sender_email: str, subjects: List[str]) -> str:
        """Classify sender relationship based on email patterns."""
        combined_text = ' '.join(subjects)
        
        # Check for VIP contacts first
        if sender_email in self.vip_contacts:
            return self.vip_contacts[sender_email]['type']
        
        # Check domain-based classification
        domain = sender_email.split('@')[-1] if '@' in sender_email else ''
        if domain in self.strategic_domains:
            return self.strategic_domains[domain]
        
        # Pattern-based classification
        if any(re.search(pattern, combined_text, re.IGNORECASE) for pattern in self.board_patterns):
            return 'board'
        elif any(re.search(pattern, combined_text, re.IGNORECASE) for pattern in self.investor_patterns):
            return 'investor'
        elif any(re.search(pattern, combined_text, re.IGNORECASE) for pattern in self.customer_patterns):
            return 'customer'
        elif 'team' in combined_text or 'employee' in combined_text:
            return 'team'
        else:
            return 'unknown'

    def _calculate_importance_score(self, sender_email: str, total_count: int, 
                                  recent_count: int, relationship_type: str) -> float:
        """Calculate sender importance score (0-100)."""
        score = 0.0
        
        # Base score from email frequency
        score += min(total_count * 2, 30)  # Max 30 points for frequency
        
        # Recent activity bonus
        score += min(recent_count * 5, 25)  # Max 25 points for recent activity
        
        # Relationship type multiplier
        relationship_scores = {
            'founder': 45, 'board': 40, 'investor': 35, 'vendor_critical': 30,
            'customer': 25, 'team': 20, 'vendor_important': 15, 'unknown': 0
        }
        score += relationship_scores.get(relationship_type, 0)
        
        # VIP bonus
        if sender_email in self.vip_contacts:
            score += 20
        
        return min(score, 100.0)

    def _determine_strategic_importance(self, importance_score: float, 
                                      relationship_type: str, sender_email: str) -> str:
        """Determine strategic importance level."""
        if importance_score >= 80 or relationship_type in ['founder', 'board']:
            return 'critical'
        elif importance_score >= 60 or relationship_type in ['investor', 'vendor_critical']:
            return 'high'
        elif importance_score >= 30 or relationship_type in ['customer', 'team']:
            return 'medium'
        else:
            return 'low'

    def _is_promotional_spam(self, email: Email) -> bool:
        """Enhanced spam detection."""
        subject_lower = email.subject.lower()
        body_lower = (email.body_text or '').lower()
        sender_lower = email.sender.email.lower()
        
        # Check sender profile first
        sender_profile = self.sender_profiles.get(sender_lower)
        if sender_profile and sender_profile.strategic_importance in ['critical', 'high']:
            return False  # Never mark important senders as spam
        
        # Spam pattern scoring
        spam_score = 0
        combined_text = f"{subject_lower} {body_lower[:200]}"
        
        for pattern in self.spam_patterns:
            if re.search(pattern, combined_text, re.IGNORECASE):
                spam_score += 1
        
        # Additional spam indicators
        if any(word in sender_lower for word in ['noreply', 'no-reply', 'marketing', 'promo']):
            spam_score += 1
            
        if re.search(r'\b(?:click here|limited time|act now|don\'t miss)\b', combined_text):
            spam_score += 2
            
        # High spam score = likely promotional
        return spam_score >= 3

    async def get_enhanced_labels(self, email: Email) -> Tuple[List[str], str]:
        """Get enhanced labels with relationship intelligence."""
        sender_lower = email.sender.email.lower()
        sender_profile = self.sender_profiles.get(sender_lower)
        
        # Skip obvious spam/promotional emails
        if self._is_promotional_spam(email):
            return [], "promotional/spam"
        
        # Auto-escalate for critical relationships
        if sender_profile and sender_profile.strategic_importance == 'critical':
            base_labels = ['DecisionRequired'] if 'decision' in email.subject.lower() else ['QuickWins']
        else:
            # Use CEO assistant for analysis
            ceo_assistant = CEOAssistantAgent()
            try:
                analysis = await ceo_assistant.analyze_for_ceo(email)
                if 'error' in analysis:
                    return [], "analysis_error"
                base_labels = analysis.get('ceo_labels', [])
            except Exception as e:
                console.print(f"[dim red]Analysis error: {str(e)[:50]}[/dim red]")
                return [], "analysis_error"
        
        # Context-aware label enhancement
        enhanced_labels = self._enhance_with_context(email, base_labels, sender_profile)
        
        # Limit to most important labels (max 3)
        final_labels = self._prioritize_labels(enhanced_labels, sender_profile)
        
        return final_labels[:3], "processed"

    def _enhance_with_context(self, email: Email, base_labels: List[str], 
                            sender_profile: Optional[SenderProfile]) -> List[str]:
        """Enhance labels with sender and thread context."""
        enhanced = base_labels.copy()
        
        if not sender_profile:
            return enhanced
        
        # Relationship-based enhancements
        if sender_profile.relationship_type == 'board' and 'Board' not in enhanced:
            enhanced.append('Board')
        elif sender_profile.relationship_type == 'investor' and 'Investors' not in enhanced:
            enhanced.append('Investors')
        elif sender_profile.relationship_type == 'customer' and 'Customers' not in enhanced:
            enhanced.append('Customers')
        
        # Strategic importance enhancements
        if sender_profile.strategic_importance == 'critical':
            if 'DecisionRequired' not in enhanced and any(
                word in email.subject.lower() for word in ['approve', 'sign', 'decide', 'urgent']
            ):
                enhanced.append('DecisionRequired')
        
        # Remove contradictory labels
        if 'ReadLater' in enhanced and sender_profile.strategic_importance in ['critical', 'high']:
            enhanced.remove('ReadLater')
        
        return enhanced

    def _prioritize_labels(self, labels: List[str], 
                         sender_profile: Optional[SenderProfile]) -> List[str]:
        """Prioritize labels based on strategic importance."""
        if not labels:
            return []
        
        # Label priority order
        priority_order = [
            'DecisionRequired', 'SignatureRequired', 'Board', 'Investors',
            'Customers', 'QuickWins', 'Team', 'Finance', 'Legal',
            'Delegatable', 'ReadLater'
        ]
        
        # Sort labels by priority
        prioritized = []
        for priority_label in priority_order:
            if priority_label in labels:
                prioritized.append(priority_label)
        
        # Add any remaining labels not in priority list
        for label in labels:
            if label not in prioritized:
                prioritized.append(label)
        
        return prioritized

async def enhanced_label_emails(limit: int = 200, dry_run: bool = False):
    """Enhanced CEO email labeling with relationship intelligence."""
    
    console.print(Panel.fit(
        "[bold cyan]🧠 Enhanced CEO Email Intelligence System[/bold cyan]",
        border_style="cyan"
    ))
    
    labeler = EnhancedCEOLabeler()
    db = DatabaseManager()
    
    # Gmail setup
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
    
    # Get label map
    results = service.users().labels().list(userId='me').execute()
    label_map = {label['name']: label['id'] for label in results.get('labels', [])}
    
    # Get emails for analysis
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        
        # Get larger dataset for profile building
        all_emails_orm = session.query(EmailORM).order_by(
            EmailORM.received_date.desc()
        ).limit(1000).all()
        
        # Convert to Email objects
        all_emails = []
        for e in all_emails_orm:
            email = Email(
                id=e.id,
                message_id=e.message_id,
                thread_id=e.thread_id,
                subject=e.subject,
                sender=EmailAddress(email=e.sender_email, name=e.sender_name),
                recipients=[],
                date=e.date,
                received_date=e.received_date,
                body_text=e.body_text or '',
                is_read=e.is_read,
                is_flagged=e.is_flagged,
                category=EmailCategory(e.category) if e.category else EmailCategory.PERSONAL,
                priority=EmailPriority(e.priority) if e.priority else EmailPriority.NORMAL,
                tags=json.loads(e.tags) if e.tags else []
            )
            all_emails.append(email)
    
    # Build sender intelligence profiles
    await labeler.build_sender_profiles(all_emails)
    
    # Get unprocessed emails for labeling
    emails_to_process = [email for email in all_emails[:limit] 
                        if 'enhanced_ceo_labeled' not in email.tags]
    
    console.print(f"\n📧 Processing [yellow]{len(emails_to_process)}[/yellow] emails with enhanced intelligence\n")
    
    # Statistics
    stats = defaultdict(int)
    label_counts = defaultdict(int)
    sender_insights = defaultdict(list)
    
    # Process emails with enhanced intelligence
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Applying enhanced intelligence...", total=len(emails_to_process))
        
        for email in emails_to_process:
            try:
                # Get enhanced labels
                labels, reason = await labeler.get_enhanced_labels(email)
                
                if reason == "promotional/spam":
                    stats['spam_filtered'] += 1
                    progress.console.print(f"   🚫 [dim]{email.subject[:40]}... (filtered: promotional)[/dim]")
                elif reason == "analysis_error":
                    stats['errors'] += 1
                elif labels:
                    # Track sender insights
                    sender_profile = labeler.sender_profiles.get(email.sender.email.lower())
                    if sender_profile:
                        sender_insights[sender_profile.strategic_importance].append({
                            'sender': email.sender.email,
                            'subject': email.subject,
                            'labels': labels
                        })
                    
                    # Apply labels in Gmail (if not dry run)
                    if not dry_run and email.message_id:
                        try:
                            msg_id = email.message_id.strip('<>')
                            query = f'rfc822msgid:{msg_id}'
                            results = service.users().messages().list(userId='me', q=query).execute()
                            
                            if results.get('messages'):
                                gmail_msg_id = results['messages'][0]['id']
                                
                                labels_to_add = []
                                for label_name in labels:
                                    full_label = f'EmailAgent/CEO/{label_name}'
                                    if full_label in label_map:
                                        labels_to_add.append(label_map[full_label])
                                        label_counts[label_name] += 1
                                
                                if labels_to_add:
                                    body = {'addLabelIds': labels_to_add}
                                    service.users().messages().modify(
                                        userId='me', id=gmail_msg_id, body=body
                                    ).execute()
                                    stats['labeled'] += 1
                        except:
                            stats['gmail_errors'] += 1
                    
                    # Show intelligent insights
                    importance = sender_profile.strategic_importance if sender_profile else 'unknown'
                    color = {'critical': 'red', 'high': 'yellow', 'medium': 'cyan', 'low': 'dim'}.get(importance, 'white')
                    label_str = ', '.join(labels)
                    progress.console.print(f"   {'🔍' if dry_run else '🧠'} [{color}]{importance.upper()}[/{color}] {email.subject[:35]}... → [green]{label_str}[/green]")
                    
                    stats['processed'] += 1
                else:
                    stats['skipped'] += 1
                
                # Mark as processed
                if not dry_run:
                    email.tags.append('enhanced_ceo_labeled')
                    # Would update database here
                
            except Exception as e:
                stats['errors'] += 1
                console.print(f"[red]Error: {str(e)[:50]}[/red]")
            
            progress.advance(task)
    
    # Display enhanced results
    console.print(f"\n[bold green]✅ Enhanced Intelligence Processing Complete![/bold green]\n")
    
    # Statistics
    console.print("[bold]📊 Enhanced Results:[/bold]")
    console.print(f"  • Processed with intelligence: {stats['processed']}")
    console.print(f"  • Spam/promotional filtered: [yellow]{stats['spam_filtered']}[/yellow]")
    if not dry_run:
        console.print(f"  • Successfully labeled: [green]{stats['labeled']}[/green]")
    console.print(f"  • Errors: [red]{stats['errors']}[/red]")
    
    # Sender intelligence insights
    if sender_insights:
        console.print("\n[bold]🧠 Sender Intelligence Insights:[/bold]")
        for importance, emails in sender_insights.items():
            if emails:
                color = {'critical': 'red', 'high': 'yellow', 'medium': 'cyan', 'low': 'dim'}.get(importance, 'white')
                console.print(f"  [{color}]{importance.upper()} Importance ({len(emails)} emails)[/{color}]")
                for email_info in emails[:3]:  # Show top 3
                    console.print(f"    • {email_info['subject'][:45]}...")
                    console.print(f"      From: {email_info['sender'][:30]} → {', '.join(email_info['labels'])}")
    
    # Label distribution
    if label_counts:
        console.print("\n[bold]🏷️  Intelligent Label Distribution:[/bold]")
        sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)
        for label, count in sorted_labels[:10]:
            bar = "█" * min(count // 2, 20)
            console.print(f"  {label:<20} {bar} {count}")

if __name__ == "__main__":
    import sys
    limit = 200
    dry_run = '--dry-run' in sys.argv
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        limit = int(sys.argv[1])
    
    asyncio.run(enhanced_label_emails(limit, dry_run))