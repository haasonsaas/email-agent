#!/usr/bin/env python3
"""Thread continuity intelligence for CEO email management."""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from ..storage.database import DatabaseManager
from ..models import Email, EmailAddress, EmailCategory, EmailPriority
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

@dataclass
class ThreadProfile:
    """Comprehensive profile for email thread tracking."""
    thread_id: str
    participants: List[str]
    message_count: int
    first_message: datetime
    last_message: datetime
    thread_duration_days: int
    subject_evolution: List[str]
    key_topics: List[str]
    labels_applied: List[str]
    importance_level: str  # critical, high, medium, low
    thread_type: str  # decision, discussion, transactional, informational
    status: str  # active, dormant, resolved, escalated
    action_items: List[str]
    decisions_made: List[str]
    waiting_for: List[str]
    escalation_count: int
    response_pattern: str  # immediate, normal, slow, stalled

@dataclass
class ConversationContext:
    """Context for ongoing conversations across threads."""
    participants: Set[str]
    related_threads: List[str]
    conversation_topic: str
    business_context: str
    urgency_level: str
    stakeholder_involvement: List[str]
    timeline: List[dict]  # chronological events
    outcomes: List[str]

class ThreadIntelligence:
    """Advanced thread continuity and conversation tracking."""
    
    def __init__(self):
        self.console = Console()
        self.thread_profiles: Dict[str, ThreadProfile] = {}
        self.conversation_contexts: Dict[str, ConversationContext] = {}
        
        # Thread classification patterns
        self.thread_type_patterns = {
            'decision': [
                r'decision', r'approve', r'sign', r'authorize', r'choose',
                r'go/no-go', r'recommendation', r'proposal'
            ],
            'discussion': [
                r'discussion', r'thoughts', r'feedback', r'opinion',
                r'brainstorm', r'ideas', r'strategy'
            ],
            'transactional': [
                r'order', r'purchase', r'invoice', r'payment', r'receipt',
                r'transaction', r'confirmation'
            ],
            'escalation': [
                r'escalat', r'urgent', r'critical', r'emergency',
                r'immediate', r'asap', r'help'
            ]
        }
        
        # Status indicators
        self.status_patterns = {
            'resolved': [
                r'resolved', r'completed', r'done', r'finished',
                r'closed', r'solved', r'fixed'
            ],
            'escalated': [
                r'escalat', r'urgent', r'critical', r'emergency',
                r'priority', r'immediate'
            ],
            'stalled': [
                r'waiting', r'pending', r'blocked', r'delayed',
                r'hold', r'pause'
            ]
        }

    async def analyze_thread_patterns(self, emails: List[Email]) -> Dict[str, Any]:
        """Analyze email threads for continuity patterns."""
        console.print("🧵 Analyzing thread continuity patterns...")
        
        # Group emails by thread
        thread_groups = defaultdict(list)
        for email in emails:
            if email.thread_id:
                thread_groups[email.thread_id].append(email)
        
        console.print(f"  Found {len(thread_groups)} unique threads")
        
        # Analyze each thread
        for thread_id, thread_emails in thread_groups.items():
            await self._analyze_thread(thread_id, thread_emails)
        
        # Identify conversation contexts
        await self._identify_conversation_contexts()
        
        return {
            'total_threads': len(self.thread_profiles),
            'active_threads': len([t for t in self.thread_profiles.values() if t.status == 'active']),
            'critical_threads': len([t for t in self.thread_profiles.values() if t.importance_level == 'critical']),
            'stalled_threads': len([t for t in self.thread_profiles.values() if t.status == 'stalled']),
            'thread_insights': self._generate_thread_insights()
        }

    async def _analyze_thread(self, thread_id: str, emails: List[Email]) -> None:
        """Analyze a specific email thread."""
        if not emails:
            return
        
        # Sort emails by date
        emails.sort(key=lambda x: x.received_date or datetime.min)
        
        # Extract participants
        participants = set()
        for email in emails:
            participants.add(email.sender.email.lower())
            # Would add recipients if available
        
        # Analyze subject evolution
        subjects = [email.subject for email in emails]
        subject_evolution = self._analyze_subject_evolution(subjects)
        
        # Extract key topics from all emails
        combined_text = ' '.join([f"{email.subject} {email.body_text or ''}" for email in emails])
        key_topics = self._extract_key_topics(combined_text)
        
        # Determine thread type
        thread_type = self._classify_thread_type(combined_text)
        
        # Calculate importance level
        importance_level = self._calculate_thread_importance(emails, participants, thread_type)
        
        # Determine thread status
        status = self._determine_thread_status(emails, combined_text)
        
        # Extract action items and decisions
        action_items = self._extract_action_items(combined_text)
        decisions_made = self._extract_decisions(combined_text)
        waiting_for = self._extract_waiting_for(combined_text)
        
        # Analyze response patterns
        response_pattern = self._analyze_response_pattern(emails)
        
        # Count escalations
        escalation_count = self._count_escalations(combined_text)
        
        # Calculate thread duration
        first_date = emails[0].received_date or datetime.now()
        last_date = emails[-1].received_date or datetime.now()
        duration_days = (last_date - first_date).days
        
        # Identify applied labels from email tags
        labels_applied = set()
        for email in emails:
            if email.tags:
                labels_applied.update(email.tags)
        
        profile = ThreadProfile(
            thread_id=thread_id,
            participants=list(participants),
            message_count=len(emails),
            first_message=first_date,
            last_message=last_date,
            thread_duration_days=duration_days,
            subject_evolution=subject_evolution,
            key_topics=key_topics,
            labels_applied=list(labels_applied),
            importance_level=importance_level,
            thread_type=thread_type,
            status=status,
            action_items=action_items,
            decisions_made=decisions_made,
            waiting_for=waiting_for,
            escalation_count=escalation_count,
            response_pattern=response_pattern
        )
        
        self.thread_profiles[thread_id] = profile

    def _analyze_subject_evolution(self, subjects: List[str]) -> List[str]:
        """Analyze how email subjects evolve in a thread."""
        if not subjects:
            return []
        
        # Remove common prefixes (Re:, Fwd:, etc.)
        cleaned_subjects = []
        for subject in subjects:
            cleaned = re.sub(r'^(Re:|Fwd:|Fw:|\[.*?\])\s*', '', subject, flags=re.IGNORECASE)
            cleaned_subjects.append(cleaned.strip())
        
        # Find unique evolution points
        evolution = [cleaned_subjects[0]]
        for subject in cleaned_subjects[1:]:
            if subject != evolution[-1] and subject not in evolution:
                evolution.append(subject)
        
        return evolution

    def _extract_key_topics(self, text: str) -> List[str]:
        """Extract key topics from thread text."""
        # Remove common words and extract meaningful phrases
        text_lower = text.lower()
        
        # Business topic patterns
        topic_patterns = [
            r'\b(?:contract|agreement|deal|partnership)\b',
            r'\b(?:budget|funding|investment|revenue)\b',
            r'\b(?:product|feature|development|launch)\b',
            r'\b(?:customer|client|user|feedback)\b',
            r'\b(?:team|hiring|interview|candidate)\b',
            r'\b(?:meeting|call|presentation|demo)\b',
            r'\b(?:legal|compliance|regulation|policy)\b',
            r'\b(?:marketing|pr|media|press)\b'
        ]
        
        topics = []
        for pattern in topic_patterns:
            matches = re.findall(pattern, text_lower)
            topics.extend(matches)
        
        # Extract company/project names (capitalized words)
        capitalized_words = re.findall(r'\b[A-Z][a-zA-Z]{2,}\b', text)
        topics.extend([word for word in capitalized_words if len(word) > 3])
        
        # Return most common topics
        topic_counts = Counter(topics)
        return [topic for topic, count in topic_counts.most_common(10)]

    def _classify_thread_type(self, text: str) -> str:
        """Classify thread type based on content patterns."""
        text_lower = text.lower()
        
        for thread_type, patterns in self.thread_type_patterns.items():
            pattern_count = sum(1 for pattern in patterns if re.search(pattern, text_lower))
            if pattern_count >= 2:  # Need multiple indicators
                return thread_type
        
        return 'discussion'  # Default

    def _calculate_thread_importance(self, emails: List[Email], 
                                   participants: Set[str], thread_type: str) -> str:
        """Calculate thread importance level."""
        score = 0
        
        # Message count scoring
        if len(emails) >= 10:
            score += 20
        elif len(emails) >= 5:
            score += 15
        elif len(emails) >= 3:
            score += 10
        
        # Participant count scoring
        if len(participants) >= 5:
            score += 15
        elif len(participants) >= 3:
            score += 10
        
        # Thread type scoring
        type_scores = {
            'decision': 25, 'escalation': 30, 'discussion': 15, 'transactional': 5
        }
        score += type_scores.get(thread_type, 10)
        
        # VIP participant bonus (would check against relationship intelligence)
        vip_domains = ['haas.holdings', 'board.', 'investor.']
        for participant in participants:
            if any(domain in participant for domain in vip_domains):
                score += 20
                break
        
        # Recent activity bonus
        if emails:
            last_email = max(emails, key=lambda x: x.received_date or datetime.min)
            if last_email.received_date:
                days_ago = (datetime.now() - last_email.received_date).days
                if days_ago <= 1:
                    score += 15
                elif days_ago <= 7:
                    score += 10
        
        # Convert to importance level
        if score >= 70:
            return 'critical'
        elif score >= 50:
            return 'high'
        elif score >= 30:
            return 'medium'
        else:
            return 'low'

    def _determine_thread_status(self, emails: List[Email], text: str) -> str:
        """Determine current thread status."""
        text_lower = text.lower()
        
        # Check for status indicators
        for status, patterns in self.status_patterns.items():
            if any(re.search(pattern, text_lower) for pattern in patterns):
                return status
        
        # Time-based status determination
        if emails:
            last_email = max(emails, key=lambda x: x.received_date or datetime.min)
            if last_email.received_date:
                days_ago = (datetime.now() - last_email.received_date).days
                if days_ago <= 3:
                    return 'active'
                elif days_ago <= 14:
                    return 'dormant'
                else:
                    return 'stalled'
        
        return 'active'

    def _extract_action_items(self, text: str) -> List[str]:
        """Extract action items from thread text."""
        action_patterns = [
            r'action item[s]?:?\s*([^\n]+)',
            r'to do[s]?:?\s*([^\n]+)',
            r'need[s]? to\s+([^\n]+)',
            r'will\s+([^\n]+)',
            r'should\s+([^\n]+)'
        ]
        
        actions = []
        for pattern in action_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            actions.extend(matches)
        
        return [action.strip() for action in actions[:10]]  # Limit to 10

    def _extract_decisions(self, text: str) -> List[str]:
        """Extract decisions made from thread text."""
        decision_patterns = [
            r'decided to\s+([^\n]+)',
            r'decision:?\s*([^\n]+)',
            r'agreed to\s+([^\n]+)',
            r'approved\s+([^\n]+)',
            r'we will\s+([^\n]+)'
        ]
        
        decisions = []
        for pattern in decision_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            decisions.extend(matches)
        
        return [decision.strip() for decision in decisions[:5]]

    def _extract_waiting_for(self, text: str) -> List[str]:
        """Extract what the thread is waiting for."""
        waiting_patterns = [
            r'waiting for\s+([^\n]+)',
            r'pending\s+([^\n]+)',
            r'blocked by\s+([^\n]+)',
            r'need[s]?\s+([^\n]+)\s+from'
        ]
        
        waiting = []
        for pattern in waiting_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            waiting.extend(matches)
        
        return [item.strip() for item in waiting[:5]]

    def _analyze_response_pattern(self, emails: List[Email]) -> str:
        """Analyze response time patterns in thread."""
        if len(emails) < 2:
            return 'insufficient_data'
        
        # Calculate time gaps between emails
        gaps = []
        for i in range(1, len(emails)):
            if emails[i].received_date and emails[i-1].received_date:
                gap = (emails[i].received_date - emails[i-1].received_date).total_seconds() / 3600  # hours
                gaps.append(gap)
        
        if not gaps:
            return 'no_data'
        
        avg_gap = sum(gaps) / len(gaps)
        
        if avg_gap <= 2:
            return 'immediate'
        elif avg_gap <= 24:
            return 'fast'
        elif avg_gap <= 72:
            return 'normal'
        elif avg_gap <= 168:  # 1 week
            return 'slow'
        else:
            return 'stalled'

    def _count_escalations(self, text: str) -> int:
        """Count escalation indicators in thread."""
        escalation_words = ['urgent', 'critical', 'emergency', 'asap', 'immediate', 'escalat']
        count = 0
        text_lower = text.lower()
        
        for word in escalation_words:
            count += len(re.findall(rf'\b{word}\b', text_lower))
        
        return count

    async def _identify_conversation_contexts(self) -> None:
        """Identify broader conversation contexts across threads."""
        # Group threads by participant overlap and topic similarity
        conversation_groups = defaultdict(list)
        
        for thread_id, profile in self.thread_profiles.items():
            # Create a key based on main participants and topics
            participant_key = tuple(sorted(profile.participants[:3]))  # Top 3 participants
            topic_key = tuple(sorted(profile.key_topics[:3]))  # Top 3 topics
            
            key = (participant_key, topic_key)
            conversation_groups[key].append(profile)
        
        # Create conversation contexts for multi-thread conversations
        for group_key, thread_profiles in conversation_groups.items():
            if len(thread_profiles) > 1:  # Multiple related threads
                participants = set()
                all_topics = []
                related_threads = []
                
                for profile in thread_profiles:
                    participants.update(profile.participants)
                    all_topics.extend(profile.key_topics)
                    related_threads.append(profile.thread_id)
                
                # Determine main conversation topic
                topic_counts = Counter(all_topics)
                conversation_topic = topic_counts.most_common(1)[0][0] if topic_counts else 'Unknown'
                
                context = ConversationContext(
                    participants=participants,
                    related_threads=related_threads,
                    conversation_topic=conversation_topic,
                    business_context=self._infer_business_context(all_topics),
                    urgency_level=self._determine_conversation_urgency(thread_profiles),
                    stakeholder_involvement=list(participants),
                    timeline=[],  # Would build from thread chronology
                    outcomes=[]   # Would extract from thread outcomes
                )
                
                context_key = f"conv_{len(self.conversation_contexts)}"
                self.conversation_contexts[context_key] = context

    def _infer_business_context(self, topics: List[str]) -> str:
        """Infer business context from conversation topics."""
        context_indicators = {
            'strategic': ['strategy', 'vision', 'roadmap', 'planning', 'investment'],
            'operational': ['operations', 'process', 'workflow', 'execution', 'delivery'],
            'financial': ['budget', 'funding', 'revenue', 'cost', 'financial'],
            'legal': ['contract', 'legal', 'compliance', 'regulation', 'agreement'],
            'hr': ['team', 'hiring', 'employee', 'candidate', 'culture'],
            'customer': ['customer', 'client', 'user', 'feedback', 'support']
        }
        
        topic_str = ' '.join(topics).lower()
        
        for context, indicators in context_indicators.items():
            if any(indicator in topic_str for indicator in indicators):
                return context
        
        return 'general'

    def _determine_conversation_urgency(self, thread_profiles: List[ThreadProfile]) -> str:
        """Determine overall conversation urgency."""
        urgency_scores = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
        
        max_importance = max([urgency_scores.get(profile.importance_level, 1) 
                             for profile in thread_profiles])
        
        urgency_mapping = {4: 'critical', 3: 'high', 2: 'medium', 1: 'low'}
        return urgency_mapping[max_importance]

    def _generate_thread_insights(self) -> Dict[str, Any]:
        """Generate insights about thread patterns."""
        insights = {
            'high_priority_threads': [],
            'stalled_important_threads': [],
            'fast_moving_threads': [],
            'long_running_threads': [],
            'escalation_threads': [],
            'decision_threads': []
        }
        
        for profile in self.thread_profiles.values():
            # High priority threads
            if profile.importance_level in ['critical', 'high']:
                insights['high_priority_threads'].append(profile)
            
            # Stalled important threads
            if (profile.status == 'stalled' and 
                profile.importance_level in ['critical', 'high']):
                insights['stalled_important_threads'].append(profile)
            
            # Fast moving threads
            if profile.response_pattern in ['immediate', 'fast']:
                insights['fast_moving_threads'].append(profile)
            
            # Long running threads
            if profile.thread_duration_days > 30:
                insights['long_running_threads'].append(profile)
            
            # Escalation threads
            if profile.escalation_count > 0:
                insights['escalation_threads'].append(profile)
            
            # Decision threads
            if profile.thread_type == 'decision':
                insights['decision_threads'].append(profile)
        
        # Sort by relevance
        for key in insights:
            if key == 'stalled_important_threads':
                insights[key].sort(key=lambda x: x.importance_level == 'critical', reverse=True)
            elif key == 'escalation_threads':
                insights[key].sort(key=lambda x: x.escalation_count, reverse=True)
            else:
                insights[key].sort(key=lambda x: x.message_count, reverse=True)
        
        return insights

    def get_thread_recommendations(self, thread_id: str) -> List[str]:
        """Get specific recommendations for a thread."""
        profile = self.thread_profiles.get(thread_id)
        if not profile:
            return ["Thread not found in analysis"]
        
        recommendations = []
        
        # Status-based recommendations
        if profile.status == 'stalled' and profile.importance_level in ['critical', 'high']:
            recommendations.append("🚨 High-priority stalled thread - immediate intervention needed")
        
        if profile.status == 'active' and profile.response_pattern == 'slow':
            recommendations.append("⚠️ Active thread with slow responses - consider escalation")
        
        # Type-based recommendations
        if profile.thread_type == 'decision' and not profile.decisions_made:
            recommendations.append("🎯 Decision thread without clear outcome - needs resolution")
        
        # Content-based recommendations
        if profile.waiting_for:
            recommendations.append(f"⏳ Thread waiting for: {', '.join(profile.waiting_for)}")
        
        if profile.action_items:
            recommendations.append(f"📋 Has action items: {len(profile.action_items)} items identified")
        
        # Timing recommendations
        if profile.thread_duration_days > 60:
            recommendations.append("📅 Long-running thread - consider archiving or milestone review")
        
        return recommendations

async def analyze_thread_intelligence(limit: int = 1000):
    """Analyze thread patterns and generate intelligence report."""
    console.print(Panel.fit(
        "[bold cyan]🧵 Thread Continuity Intelligence Analysis[/bold cyan]",
        border_style="cyan"
    ))
    
    # Initialize system
    ti = ThreadIntelligence()
    db = DatabaseManager()
    
    # Get emails for analysis
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        
        emails_orm = session.query(EmailORM).order_by(
            EmailORM.received_date.desc()
        ).limit(limit).all()
        
        emails = []
        for e in emails_orm:
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
            emails.append(email)
    
    # Analyze thread patterns
    analysis_results = await ti.analyze_thread_patterns(emails)
    
    # Display results
    console.print(f"\n[bold]📊 Thread Analysis Results:[/bold]")
    console.print(f"  • Total threads: {analysis_results['total_threads']}")
    console.print(f"  • Active threads: [green]{analysis_results['active_threads']}[/green]")
    console.print(f"  • Critical threads: [red]{analysis_results['critical_threads']}[/red]")
    console.print(f"  • Stalled threads: [yellow]{analysis_results['stalled_threads']}[/yellow]")
    
    insights = analysis_results['thread_insights']
    
    # Critical threads requiring attention
    if insights['stalled_important_threads']:
        console.print("\n[bold red]🚨 Stalled Important Threads:[/bold red]")
        stalled_table = Table(show_header=True, header_style="bold red")
        stalled_table.add_column("Thread", style="red", width=40)
        stalled_table.add_column("Type", style="yellow")
        stalled_table.add_column("Days", justify="center")
        stalled_table.add_column("Messages", justify="center")
        stalled_table.add_column("Participants", justify="center")
        
        for thread in insights['stalled_important_threads'][:10]:
            subject = thread.subject_evolution[0] if thread.subject_evolution else "Unknown"
            stalled_table.add_row(
                subject[:35] + "..." if len(subject) > 35 else subject,
                thread.thread_type.title(),
                str(thread.thread_duration_days),
                str(thread.message_count),
                str(len(thread.participants))
            )
        
        console.print(stalled_table)
    
    # Decision threads
    if insights['decision_threads']:
        console.print("\n[bold yellow]🎯 Decision Threads:[/bold yellow]")
        for thread in insights['decision_threads'][:5]:
            subject = thread.subject_evolution[0] if thread.subject_evolution else "Unknown"
            status_icon = "✅" if thread.decisions_made else "❓"
            console.print(f"  {status_icon} {subject[:50]}... ({thread.message_count} messages)")
    
    # Fast-moving threads
    if insights['fast_moving_threads']:
        console.print("\n[bold green]⚡ Fast-Moving Threads:[/bold green]")
        for thread in insights['fast_moving_threads'][:5]:
            subject = thread.subject_evolution[0] if thread.subject_evolution else "Unknown"
            console.print(f"  • {subject[:50]}... ({thread.response_pattern} responses)")
    
    # Long-running threads
    if insights['long_running_threads']:
        console.print("\n[bold blue]📅 Long-Running Threads:[/bold blue]")
        for thread in insights['long_running_threads'][:5]:
            subject = thread.subject_evolution[0] if thread.subject_evolution else "Unknown"
            console.print(f"  • {subject[:50]}... ({thread.thread_duration_days} days, {thread.message_count} messages)")
    
    # Recommendations
    console.print(Panel("""[bold yellow]🧵 Thread Intelligence Recommendations:[/bold yellow]

[bold]Immediate Actions:[/bold]
• Review stalled important threads for intervention opportunities
• Follow up on decision threads without clear outcomes
• Monitor fast-moving threads for escalation needs
• Archive or milestone long-running resolved threads

[bold]Labeling Improvements:[/bold]
• Apply consistent labels across related thread messages
• Auto-escalate threads with multiple urgent indicators
• Create thread-specific labels for ongoing projects
• Use thread context for smarter response prioritization

[bold]Process Enhancements:[/bold]
• Set up thread status tracking and alerts
• Create templates for common thread types
• Implement thread summarization for long conversations
• Track decision outcomes and action item completion""", border_style="green"))
    
    return ti

if __name__ == "__main__":
    import sys
    limit = 1000
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    
    asyncio.run(analyze_thread_intelligence(limit))