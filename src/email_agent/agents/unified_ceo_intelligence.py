#!/usr/bin/env python3
"""Unified CEO Email Intelligence System - Complete Solution."""

import asyncio
import json
from typing import Dict, List, Any
from dataclasses import dataclass
from collections import defaultdict

# Import our intelligence systems
from .enhanced_ceo_labeler import EnhancedCEOLabeler
from .relationship_intelligence import RelationshipIntelligence
from .thread_intelligence import ThreadIntelligence

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
class UnifiedIntelligence:
    """Unified intelligence combining all systems."""
    sender_intelligence: Dict[str, Any]
    relationship_intelligence: Dict[str, Any]
    thread_intelligence: Dict[str, Any]
    predictive_patterns: Dict[str, Any]
    auto_escalation_rules: List[Dict[str, Any]]

@dataclass
class EmailPrediction:
    """Prediction for email handling."""
    suggested_labels: List[str]
    confidence_score: float
    reasoning: List[str]
    escalation_recommended: bool
    predicted_response_time: str
    similar_historical_emails: List[str]

class UnifiedCEOIntelligence:
    """Master system integrating all CEO email intelligence."""
    
    def __init__(self):
        self.console = Console()
        self.enhanced_labeler = EnhancedCEOLabeler()
        self.relationship_intel = RelationshipIntelligence()
        self.thread_intel = ThreadIntelligence()
        
        # Auto-escalation rules
        self.escalation_rules = [
            {
                'name': 'Board Member Priority',
                'condition': lambda profile, email: (
                    profile and profile.relationship_type == 'board'
                ),
                'action': 'immediate_escalation',
                'labels': ['DecisionRequired', 'Board']
            },
            {
                'name': 'Critical Sender Urgent',
                'condition': lambda profile, email: (
                    profile and profile.strategic_importance == 'critical' and
                    any(word in email.subject.lower() for word in ['urgent', 'asap', 'critical'])
                ),
                'action': 'high_priority',
                'labels': ['DecisionRequired', 'QuickWins']
            },
            {
                'name': 'Investor Communication',
                'condition': lambda profile, email: (
                    profile and profile.relationship_type == 'investor'
                ),
                'action': 'strategic_attention',
                'labels': ['Investors', 'WeeklyReview']
            },
            {
                'name': 'Legal/Signature Required',
                'condition': lambda profile, email: (
                    any(word in email.subject.lower() for word in ['sign', 'signature', 'contract', 'legal'])
                ),
                'action': 'signature_required',
                'labels': ['SignatureRequired', 'Legal']
            }
        ]
        
        # Predictive patterns storage
        self.historical_patterns = {}
        self.labeling_patterns = defaultdict(list)

    async def initialize_intelligence(self, emails: List[Email]) -> UnifiedIntelligence:
        """Initialize all intelligence systems with email data."""
        console.print("🧠 Initializing Unified CEO Intelligence System...")
        
        # Build sender profiles
        await self.enhanced_labeler.build_sender_profiles(emails)
        
        # Analyze relationships
        relationship_results = await self.relationship_intel.analyze_relationships(emails)
        
        # Analyze thread patterns
        thread_results = await self.thread_intel.analyze_thread_patterns(emails)
        
        # Build predictive patterns
        predictive_patterns = await self._build_predictive_patterns(emails)
        
        # Compile auto-escalation rules
        auto_escalation_rules = self._compile_escalation_rules()
        
        unified = UnifiedIntelligence(
            sender_intelligence={
                'profiles': self.enhanced_labeler.sender_profiles,
                'insights': 'Enhanced sender reputation and importance scoring'
            },
            relationship_intelligence={
                'contacts': self.relationship_intel.contact_profiles,
                'contexts': self.relationship_intel.relationship_contexts,
                'insights': relationship_results
            },
            thread_intelligence={
                'threads': self.thread_intel.thread_profiles,
                'conversations': self.thread_intel.conversation_contexts,
                'insights': thread_results
            },
            predictive_patterns=predictive_patterns,
            auto_escalation_rules=auto_escalation_rules
        )
        
        console.print("  ✅ Unified intelligence system initialized")
        return unified

    async def _build_predictive_patterns(self, emails: List[Email]) -> Dict[str, Any]:
        """Build predictive patterns from historical email data."""
        console.print("🔮 Building predictive patterns...")
        
        # Analyze historical labeling patterns
        sender_label_patterns = defaultdict(lambda: defaultdict(int))
        subject_label_patterns = defaultdict(lambda: defaultdict(int))
        time_patterns = defaultdict(list)
        
        for email in emails:
            sender = email.sender.email.lower()
            
            # Mock historical labels (in production, would come from actual labeling history)
            historical_labels = self._mock_historical_labels(email)
            
            for label in historical_labels:
                sender_label_patterns[sender][label] += 1
                
                # Extract subject keywords
                subject_words = email.subject.lower().split()
                for word in subject_words:
                    if len(word) > 3:
                        subject_label_patterns[word][label] += 1
            
            # Track timing patterns
            if email.received_date:
                hour = email.received_date.hour
                day_of_week = email.received_date.weekday()
                time_patterns[sender].append({'hour': hour, 'day': day_of_week, 'labels': historical_labels})
        
        return {
            'sender_patterns': dict(sender_label_patterns),
            'subject_patterns': dict(subject_label_patterns),
            'time_patterns': dict(time_patterns),
            'pattern_confidence': self._calculate_pattern_confidence(sender_label_patterns)
        }

    def _mock_historical_labels(self, email: Email) -> List[str]:
        """Mock historical labels for pattern building (replace with actual data)."""
        labels = []
        subject_lower = email.subject.lower()
        sender_lower = email.sender.email.lower()
        
        # Mock patterns based on content
        if 'board' in subject_lower or 'board' in sender_lower:
            labels.append('Board')
        if 'investor' in subject_lower or any(word in subject_lower for word in ['funding', 'investment']):
            labels.append('Investors')
        if any(word in subject_lower for word in ['sign', 'signature', 'contract']):
            labels.append('SignatureRequired')
        if any(word in subject_lower for word in ['urgent', 'asap', 'critical']):
            labels.append('DecisionRequired')
        if any(word in subject_lower for word in ['customer', 'client', 'user']):
            labels.append('Customers')
        if any(word in subject_lower for word in ['team', 'hire', 'interview']):
            labels.append('Team')
        
        return labels

    def _calculate_pattern_confidence(self, patterns: Dict) -> Dict[str, float]:
        """Calculate confidence scores for predictive patterns."""
        confidence_scores = {}
        
        for sender, label_counts in patterns.items():
            if sum(label_counts.values()) >= 5:  # Need minimum data
                total_emails = sum(label_counts.values())
                max_label_count = max(label_counts.values()) if label_counts else 0
                confidence = max_label_count / total_emails if total_emails > 0 else 0
                confidence_scores[sender] = confidence
        
        return confidence_scores

    def _compile_escalation_rules(self) -> List[Dict[str, Any]]:
        """Compile auto-escalation rules with metadata."""
        compiled_rules = []
        
        for rule in self.escalation_rules:
            compiled_rules.append({
                'name': rule['name'],
                'priority': rule.get('priority', 'medium'),
                'action': rule['action'],
                'labels': rule['labels'],
                'description': f"Auto-escalation rule: {rule['name']}"
            })
        
        return compiled_rules

    async def predict_email_handling(self, email: Email, unified_intel: UnifiedIntelligence) -> EmailPrediction:
        """Use unified intelligence to predict optimal email handling."""
        sender_key = email.sender.email.lower()
        
        # Get intelligence data
        sender_profile = unified_intel.sender_intelligence['profiles'].get(sender_key)
        contact_profile = unified_intel.relationship_intelligence['contacts'].get(sender_key)
        thread_profile = None
        if email.thread_id:
            thread_profile = unified_intel.thread_intelligence['threads'].get(email.thread_id)
        
        # Predictive analysis
        suggested_labels = []
        reasoning = []
        confidence_score = 0.0
        escalation_recommended = False
        
        # Sender-based predictions
        if sender_profile:
            if sender_profile.strategic_importance == 'critical':
                suggested_labels.extend(['DecisionRequired', 'QuickWins'])
                reasoning.append(f"Critical sender (importance: {sender_profile.importance_score:.1f})")
                confidence_score += 0.3
            
            # Historical pattern predictions
            sender_patterns = unified_intel.predictive_patterns['sender_patterns'].get(sender_key, {})
            if sender_patterns:
                most_common_label = max(sender_patterns.items(), key=lambda x: x[1])[0]
                if most_common_label not in suggested_labels:
                    suggested_labels.append(most_common_label)
                    reasoning.append(f"Historical pattern: usually gets '{most_common_label}' label")
                    confidence_score += 0.2
        
        # Relationship-based predictions
        if contact_profile:
            if contact_profile.relationship_type == 'board':
                if 'Board' not in suggested_labels:
                    suggested_labels.append('Board')
                reasoning.append("Board member relationship")
                confidence_score += 0.4
                escalation_recommended = True
            elif contact_profile.relationship_type == 'investor':
                if 'Investors' not in suggested_labels:
                    suggested_labels.append('Investors')
                reasoning.append("Investor relationship")
                confidence_score += 0.3
        
        # Thread-based predictions
        if thread_profile:
            if thread_profile.thread_type == 'decision':
                if 'DecisionRequired' not in suggested_labels:
                    suggested_labels.append('DecisionRequired')
                reasoning.append("Part of decision thread")
                confidence_score += 0.25
            
            # Inherit thread labels for consistency
            for label in thread_profile.labels_applied:
                if label.startswith('CEO/') and label not in suggested_labels:
                    suggested_labels.append(label.replace('CEO/', ''))
                    reasoning.append(f"Thread consistency: {label}")
                    confidence_score += 0.15
        
        # Content-based predictions
        subject_lower = email.subject.lower()
        subject_patterns = unified_intel.predictive_patterns['subject_patterns']
        
        for word in subject_lower.split():
            if len(word) > 3 and word in subject_patterns:
                word_labels = subject_patterns[word]
                most_common = max(word_labels.items(), key=lambda x: x[1])[0]
                if most_common not in suggested_labels:
                    suggested_labels.append(most_common)
                    reasoning.append(f"Subject keyword '{word}' suggests '{most_common}'")
                    confidence_score += 0.1
        
        # Auto-escalation check
        for rule in self.escalation_rules:
            if rule['condition'](contact_profile or sender_profile, email):
                escalation_recommended = True
                for label in rule['labels']:
                    if label not in suggested_labels:
                        suggested_labels.append(label)
                reasoning.append(f"Auto-escalation rule: {rule['name']}")
                confidence_score += 0.2
                break
        
        # Predict response time based on sender importance
        if contact_profile:
            if contact_profile.escalation_priority >= 4:
                predicted_response_time = "within 2 hours"
            elif contact_profile.escalation_priority >= 3:
                predicted_response_time = "within 24 hours"
            else:
                predicted_response_time = "within 3 days"
        else:
            predicted_response_time = "when convenient"
        
        # Find similar historical emails (mock implementation)
        similar_emails = self._find_similar_emails(email, unified_intel)
        
        # Normalize confidence score
        confidence_score = min(confidence_score, 1.0)
        
        return EmailPrediction(
            suggested_labels=suggested_labels[:4],  # Limit to top 4
            confidence_score=confidence_score,
            reasoning=reasoning,
            escalation_recommended=escalation_recommended,
            predicted_response_time=predicted_response_time,
            similar_historical_emails=similar_emails
        )

    def _find_similar_emails(self, email: Email, unified_intel: UnifiedIntelligence) -> List[str]:
        """Find historically similar emails (simplified implementation)."""
        # This would use more sophisticated similarity matching in production
        similar = []
        sender_patterns = unified_intel.predictive_patterns['sender_patterns']
        sender_key = email.sender.email.lower()
        
        if sender_key in sender_patterns:
            similar.append(f"Similar emails from {email.sender.email}")
        
        # Mock additional similarities
        subject_words = email.subject.lower().split()
        for word in subject_words:
            if len(word) > 4:
                similar.append(f"Emails containing '{word}'")
                break
        
        return similar[:3]

async def run_unified_ceo_intelligence(limit: int = 200, dry_run: bool = False):
    """Run the complete unified CEO intelligence system."""
    
    console.print(Panel.fit(
        "[bold cyan]🚀 Unified CEO Email Intelligence System[/bold cyan]\n"
        "[dim]Advanced AI-powered email management with relationship intelligence,[/dim]\n"
        "[dim]thread continuity, predictive labeling, and auto-escalation[/dim]",
        border_style="cyan"
    ))
    
    # Initialize system
    unified_system = UnifiedCEOIntelligence()
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
    
    # Get emails for analysis
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        
        # Get comprehensive dataset for intelligence building
        all_emails_orm = session.query(EmailORM).order_by(
            EmailORM.received_date.desc()
        ).limit(1500).all()  # Larger dataset for better intelligence
        
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
    
    # Initialize unified intelligence
    unified_intel = await unified_system.initialize_intelligence(all_emails)
    
    # Get emails to process (unprocessed by unified system)
    emails_to_process = [email for email in all_emails[:limit] 
                        if 'unified_ceo_processed' not in email.tags]
    
    console.print(f"\n📧 Processing [yellow]{len(emails_to_process)}[/yellow] emails with unified intelligence\n")
    
    # Get Gmail label map
    results = service.users().labels().list(userId='me').execute()
    label_map = {label['name']: label['id'] for label in results.get('labels', [])}
    
    # Statistics
    stats = defaultdict(int)
    predictions_made = []
    escalations_triggered = []
    
    # Process emails with unified intelligence
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Applying unified intelligence...", total=len(emails_to_process))
        
        for email in emails_to_process:
            try:
                # Get unified prediction
                prediction = await unified_system.predict_email_handling(email, unified_intel)
                predictions_made.append(prediction)
                
                if prediction.escalation_recommended:
                    escalations_triggered.append(email)
                
                # Apply labels based on prediction
                if prediction.suggested_labels and not dry_run and email.message_id:
                    try:
                        msg_id = email.message_id.strip('<>')
                        query = f'rfc822msgid:{msg_id}'
                        results = service.users().messages().list(userId='me', q=query).execute()
                        
                        if results.get('messages'):
                            gmail_msg_id = results['messages'][0]['id']
                            
                            labels_to_add = []
                            for label_name in prediction.suggested_labels:
                                full_label = f'EmailAgent/CEO/{label_name}'
                                if full_label in label_map:
                                    labels_to_add.append(label_map[full_label])
                            
                            if labels_to_add:
                                body = {'addLabelIds': labels_to_add}
                                service.users().messages().modify(
                                    userId='me', id=gmail_msg_id, body=body
                                ).execute()
                                stats['labeled'] += 1
                    except Exception:
                        stats['gmail_errors'] += 1
                
                # Display intelligent insights
                confidence_color = 'green' if prediction.confidence_score > 0.7 else 'yellow' if prediction.confidence_score > 0.4 else 'red'
                escalation_icon = '🚨' if prediction.escalation_recommended else '🧠'
                
                label_str = ', '.join(prediction.suggested_labels[:3])
                if len(prediction.suggested_labels) > 3:
                    label_str += f' +{len(prediction.suggested_labels)-3}'
                
                progress.console.print(
                    f"   {escalation_icon} [{confidence_color}]{prediction.confidence_score:.2f}[/{confidence_color}] "
                    f"{email.subject[:30]}... → [green]{label_str}[/green]"
                )
                
                # Show top reasoning
                if prediction.reasoning:
                    top_reason = prediction.reasoning[0]
                    progress.console.print(f"      [dim]└─ {top_reason}[/dim]")
                
                stats['processed'] += 1
                
                # Mark as processed
                if not dry_run:
                    email.tags.append('unified_ceo_processed')
                
            except Exception as e:
                stats['errors'] += 1
                console.print(f"[red]Error: {str(e)[:50]}[/red]")
            
            progress.advance(task)
    
    # Display comprehensive results
    console.print("\n[bold green]✅ Unified Intelligence Processing Complete![/bold green]\n")
    
    # Statistics
    console.print("[bold]📊 Unified Intelligence Results:[/bold]")
    console.print(f"  • Emails processed: {stats['processed']}")
    console.print(f"  • Predictions made: [cyan]{len(predictions_made)}[/cyan]")
    console.print(f"  • Auto-escalations: [red]{len(escalations_triggered)}[/red]")
    if not dry_run:
        console.print(f"  • Successfully labeled: [green]{stats['labeled']}[/green]")
    console.print(f"  • Errors: [red]{stats['errors']}[/red]")
    
    # Confidence distribution
    if predictions_made:
        high_confidence = len([p for p in predictions_made if p.confidence_score > 0.7])
        medium_confidence = len([p for p in predictions_made if 0.4 < p.confidence_score <= 0.7])
        low_confidence = len([p for p in predictions_made if p.confidence_score <= 0.4])
        
        console.print("\n[bold]🎯 Prediction Confidence:[/bold]")
        console.print(f"  • High confidence (>70%): [green]{high_confidence}[/green]")
        console.print(f"  • Medium confidence (40-70%): [yellow]{medium_confidence}[/yellow]")
        console.print(f"  • Low confidence (<40%): [red]{low_confidence}[/red]")
    
    # Escalations triggered
    if escalations_triggered:
        console.print("\n[bold red]🚨 Auto-Escalations Triggered:[/bold red]")
        for email in escalations_triggered[:5]:
            console.print(f"  • [red]{email.subject[:50]}...[/red] from {email.sender.email}")
    
    # Intelligence summary
    console.print(Panel(f"""[bold yellow]🧠 Unified Intelligence Summary:[/bold yellow]

[bold]Sender Intelligence:[/bold]
• {len(unified_intel.sender_intelligence['profiles'])} sender profiles analyzed
• Strategic importance scoring and reputation tracking

[bold]Relationship Intelligence:[/bold]
• {len(unified_intel.relationship_intelligence['contacts'])} contact relationships mapped
• Auto-escalation rules for VIP contacts

[bold]Thread Intelligence:[/bold]
• {len(unified_intel.thread_intelligence['threads'])} conversation threads tracked
• Context-aware labeling and continuity

[bold]Predictive Intelligence:[/bold]
• Historical pattern recognition for labeling
• Confidence-based decision making
• Response time predictions

[bold green]Next Steps:[/bold green]
1. Review auto-escalated emails immediately
2. Follow up on high-confidence predictions
3. Monitor system learning and accuracy
4. Refine escalation rules based on outcomes""", border_style="green"))

if __name__ == "__main__":
    import sys
    limit = 200
    dry_run = '--dry-run' in sys.argv
    
    # Parse command line arguments
    for i, arg in enumerate(sys.argv):
        if arg.isdigit():
            limit = int(arg)
    
    asyncio.run(run_unified_ceo_intelligence(limit, dry_run))