#!/usr/bin/env python3
"""Relationship intelligence system for CEO email management."""

import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from ..storage.database import DatabaseManager
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

@dataclass
class ContactProfile:
    """Comprehensive contact profile for relationship intelligence."""
    email: str
    name: Optional[str]
    company: Optional[str]
    role: Optional[str]
    relationship_type: str  # board, investor, customer, team, vendor, advisor, partner
    importance_level: str  # critical, high, medium, low
    first_contact: Optional[datetime]
    last_contact: Optional[datetime]
    total_interactions: int
    recent_interactions: int  # last 30 days
    response_pattern: str  # immediate, fast, slow, rare
    typical_subjects: List[str]
    decision_maker: bool
    escalation_priority: int  # 1-5, 5 being highest
    tags: List[str]
    notes: str

@dataclass
class RelationshipContext:
    """Context about ongoing relationships and conversations."""
    contact_email: str
    thread_topics: List[str]
    interaction_frequency: str  # daily, weekly, monthly, rare
    relationship_strength: str  # strong, moderate, weak, new
    business_context: str  # strategic, operational, transactional
    last_action_required: Optional[str]
    pending_items: List[str]

class RelationshipIntelligence:
    """Advanced relationship mapping and intelligence system."""
    
    def __init__(self):
        self.console = Console()
        self.contact_profiles: Dict[str, ContactProfile] = {}
        self.relationship_contexts: Dict[str, RelationshipContext] = {}
        
        # Initialize known strategic relationships
        self._initialize_strategic_contacts()
        
        # Relationship classification patterns
        self.role_patterns = {
            'board': [
                r'board', r'director', r'chairman', r'chair', r'board member',
                r'governance', r'board meeting', r'board deck'
            ],
            'investor': [
                r'investor', r'investment', r'venture', r'equity', r'fund',
                r'general partner', r'managing director', r'principal',
                r'due diligence', r'term sheet', r'funding'
            ],
            'customer': [
                r'customer', r'client', r'user', r'account', r'procurement',
                r'buyer', r'purchaser', r'enterprise'
            ],
            'advisor': [
                r'advisor', r'adviser', r'mentor', r'consultant',
                r'advisory', r'guidance'
            ],
            'vendor': [
                r'vendor', r'supplier', r'service provider', r'partner',
                r'account manager', r'sales', r'support'
            ],
            'team': [
                r'employee', r'team', r'staff', r'hire', r'candidate',
                r'manager', r'lead', r'developer', r'engineer'
            ]
        }
        
        # Company domain intelligence (from deep analysis)
        self.company_domains = {
            'haas.holdings': {'type': 'internal', 'importance': 'critical'},
            'rippling.com': {'type': 'vendor', 'importance': 'high'},
            'docusign.com': {'type': 'vendor', 'importance': 'high'},
            'github.com': {'type': 'vendor', 'importance': 'medium'},
            'amazonaws.com': {'type': 'vendor', 'importance': 'high'},
            'google.com': {'type': 'vendor', 'importance': 'medium'},
            'apple.com': {'type': 'vendor', 'importance': 'medium'}
        }

    def _initialize_strategic_contacts(self):
        """Initialize known strategic contacts (would typically come from CRM)."""
        # Example strategic contacts - in production, this would come from CRM/database
        strategic_contacts = [
            {
                'email': 'jonathan@haas.holdings',
                'name': 'Jonathan Haas',
                'company': 'Haas Holdings',
                'role': 'CEO/Founder',
                'relationship_type': 'internal',
                'importance_level': 'critical',
                'decision_maker': True,
                'escalation_priority': 5,
                'tags': ['founder', 'ceo', 'decision_maker']
            }
            # Would add board members, key investors, etc.
        ]
        
        for contact_data in strategic_contacts:
            profile = ContactProfile(
                email=contact_data['email'],
                name=contact_data.get('name'),
                company=contact_data.get('company'),
                role=contact_data.get('role'),
                relationship_type=contact_data['relationship_type'],
                importance_level=contact_data['importance_level'],
                first_contact=None,
                last_contact=None,
                total_interactions=0,
                recent_interactions=0,
                response_pattern='unknown',
                typical_subjects=[],
                decision_maker=contact_data.get('decision_maker', False),
                escalation_priority=contact_data.get('escalation_priority', 3),
                tags=contact_data.get('tags', []),
                notes=''
            )
            self.contact_profiles[contact_data['email'].lower()] = profile

    async def analyze_relationships(self, emails: List) -> Dict[str, any]:
        """Analyze email patterns to build relationship intelligence."""
        console.print("🔍 Analyzing relationship patterns...")
        
        # Track interaction patterns
        interaction_patterns = defaultdict(lambda: {
            'dates': [], 'subjects': [], 'response_times': [],
            'keywords': Counter(), 'conversation_threads': set()
        })
        
        # Analyze each email
        for email in emails:
            sender_key = email.sender.email.lower()
            interaction_patterns[sender_key]['dates'].append(email.received_date)
            interaction_patterns[sender_key]['subjects'].append(email.subject)
            interaction_patterns[sender_key]['conversation_threads'].add(email.thread_id)
            
            # Extract keywords from subject and body
            text = f"{email.subject} {email.body_text or ''}"
            keywords = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
            for keyword in keywords:
                interaction_patterns[sender_key]['keywords'][keyword] += 1
        
        # Build/update contact profiles
        for sender_email, patterns in interaction_patterns.items():
            await self._build_contact_profile(sender_email, patterns)
        
        # Analyze relationship contexts
        await self._analyze_relationship_contexts(interaction_patterns)
        
        return {
            'total_contacts': len(self.contact_profiles),
            'strategic_contacts': len([p for p in self.contact_profiles.values() 
                                     if p.importance_level in ['critical', 'high']]),
            'relationship_insights': self._generate_relationship_insights()
        }

    async def _build_contact_profile(self, sender_email: str, patterns: Dict) -> None:
        """Build or update a contact profile based on email patterns."""
        dates = [d for d in patterns['dates'] if d]
        
        # Get or create profile
        if sender_email in self.contact_profiles:
            profile = self.contact_profiles[sender_email]
        else:
            profile = ContactProfile(
                email=sender_email,
                name=self._extract_name_from_email(sender_email),
                company=self._infer_company_from_domain(sender_email),
                role=None,
                relationship_type='unknown',
                importance_level='low',
                first_contact=None,
                last_contact=None,
                total_interactions=0,
                recent_interactions=0,
                response_pattern='unknown',
                typical_subjects=[],
                decision_maker=False,
                escalation_priority=1,
                tags=[],
                notes=''
            )
        
        # Update interaction data
        profile.total_interactions = len(patterns['subjects'])
        if dates:
            profile.first_contact = min(dates)
            profile.last_contact = max(dates)
            
            # Count recent interactions (last 30 days)
            cutoff = datetime.now() - timedelta(days=30)
            profile.recent_interactions = len([d for d in dates if d > cutoff])
        
        # Infer relationship type and role
        combined_text = ' '.join(patterns['subjects']).lower()
        profile.relationship_type = self._classify_relationship_type(sender_email, combined_text)
        profile.role = self._infer_role(combined_text, profile.relationship_type)
        
        # Calculate importance level
        profile.importance_level = self._calculate_importance_level(profile)
        
        # Update typical subjects
        profile.typical_subjects = list(patterns['keywords'].most_common(5))
        
        # Set escalation priority
        profile.escalation_priority = self._calculate_escalation_priority(profile)
        
        # Add relationship-based tags
        profile.tags = self._generate_contact_tags(profile, combined_text)
        
        self.contact_profiles[sender_email] = profile

    def _extract_name_from_email(self, email: str) -> Optional[str]:
        """Extract likely name from email address."""
        local_part = email.split('@')[0]
        
        # Handle common patterns
        if '.' in local_part:
            parts = local_part.split('.')
            return ' '.join(part.capitalize() for part in parts if len(part) > 1)
        elif '_' in local_part:
            parts = local_part.split('_')
            return ' '.join(part.capitalize() for part in parts if len(part) > 1)
        else:
            return local_part.capitalize() if len(local_part) > 2 else None

    def _infer_company_from_domain(self, email: str) -> Optional[str]:
        """Infer company from email domain."""
        domain = email.split('@')[-1] if '@' in email else ''
        
        # Known company mappings
        company_mappings = {
            'haas.holdings': 'Haas Holdings',
            'rippling.com': 'Rippling',
            'docusign.com': 'DocuSign',
            'github.com': 'GitHub',
            'amazonaws.com': 'Amazon Web Services',
            'google.com': 'Google',
            'apple.com': 'Apple',
            'microsoft.com': 'Microsoft'
        }
        
        if domain in company_mappings:
            return company_mappings[domain]
        
        # Generic inference from domain
        if domain and not domain.endswith('.gmail.com'):
            # Remove common TLDs and format as company name
            company = domain.split('.')[0]
            return company.capitalize()
        
        return None

    def _classify_relationship_type(self, email: str, combined_text: str) -> str:
        """Classify relationship type based on email patterns."""
        domain = email.split('@')[-1] if '@' in email else ''
        
        # Check domain-based classification
        if domain in self.company_domains:
            return self.company_domains[domain]['type']
        
        # Pattern-based classification
        for rel_type, patterns in self.role_patterns.items():
            if any(re.search(pattern, combined_text, re.IGNORECASE) for pattern in patterns):
                return rel_type
        
        return 'unknown'

    def _infer_role(self, combined_text: str, relationship_type: str) -> Optional[str]:
        """Infer specific role based on text patterns."""
        role_indicators = {
            'ceo': ['ceo', 'chief executive', 'founder'],
            'cto': ['cto', 'chief technology', 'chief technical'],
            'cfo': ['cfo', 'chief financial'],
            'vp': ['vice president', 'vp ', 'v.p.'],
            'director': ['director', 'dir '],
            'manager': ['manager', 'mgr'],
            'analyst': ['analyst'],
            'engineer': ['engineer', 'developer'],
            'sales': ['sales', 'account manager', 'account executive']
        }
        
        for role, indicators in role_indicators.items():
            if any(indicator in combined_text for indicator in indicators):
                return role
        
        return None

    def _calculate_importance_level(self, profile: ContactProfile) -> str:
        """Calculate importance level based on multiple factors."""
        score = 0
        
        # Relationship type scoring
        type_scores = {
            'internal': 25, 'board': 25, 'investor': 20, 'customer': 15,
            'advisor': 10, 'team': 10, 'vendor': 5, 'unknown': 0
        }
        score += type_scores.get(profile.relationship_type, 0)
        
        # Interaction frequency scoring
        if profile.total_interactions >= 50:
            score += 20
        elif profile.total_interactions >= 20:
            score += 15
        elif profile.total_interactions >= 10:
            score += 10
        elif profile.total_interactions >= 5:
            score += 5
        
        # Recent activity scoring
        if profile.recent_interactions >= 10:
            score += 15
        elif profile.recent_interactions >= 5:
            score += 10
        elif profile.recent_interactions >= 2:
            score += 5
        
        # Decision maker bonus
        if profile.decision_maker:
            score += 15
        
        # Company domain bonus
        domain = profile.email.split('@')[-1]
        if domain in self.company_domains:
            domain_importance = self.company_domains[domain]['importance']
            if domain_importance == 'critical':
                score += 10
            elif domain_importance == 'high':
                score += 5
        
        # Convert to importance level
        if score >= 70:
            return 'critical'
        elif score >= 50:
            return 'high'
        elif score >= 30:
            return 'medium'
        else:
            return 'low'

    def _calculate_escalation_priority(self, profile: ContactProfile) -> int:
        """Calculate escalation priority (1-5, 5 being highest)."""
        if profile.importance_level == 'critical':
            return 5
        elif profile.importance_level == 'high':
            return 4
        elif profile.importance_level == 'medium':
            return 3
        elif profile.importance_level == 'low':
            return 2
        else:
            return 1

    def _generate_contact_tags(self, profile: ContactProfile, combined_text: str) -> List[str]:
        """Generate relevant tags for a contact."""
        tags = []
        
        # Relationship-based tags
        tags.append(profile.relationship_type)
        if profile.importance_level in ['critical', 'high']:
            tags.append('vip')
        if profile.decision_maker:
            tags.append('decision_maker')
        
        # Role-based tags
        if profile.role:
            tags.append(profile.role)
        
        # Content-based tags
        if 'urgent' in combined_text:
            tags.append('urgent_sender')
        if any(word in combined_text for word in ['meeting', 'schedule', 'calendar']):
            tags.append('meeting_heavy')
        if any(word in combined_text for word in ['contract', 'legal', 'agreement']):
            tags.append('legal_matters')
        
        return list(set(tags))  # Remove duplicates

    async def _analyze_relationship_contexts(self, interaction_patterns: Dict) -> None:
        """Analyze ongoing relationship contexts and conversation patterns."""
        for sender_email, patterns in interaction_patterns.items():
            profile = self.contact_profiles.get(sender_email)
            if not profile:
                continue
            
            # Analyze conversation frequency
            dates = [d for d in patterns['dates'] if d]
            if len(dates) >= 2:
                avg_gap = sum((dates[i] - dates[i-1]).days for i in range(1, len(dates))) / (len(dates) - 1)
                if avg_gap <= 7:
                    frequency = 'daily'
                elif avg_gap <= 30:
                    frequency = 'weekly'
                elif avg_gap <= 90:
                    frequency = 'monthly'
                else:
                    frequency = 'rare'
            else:
                frequency = 'new'
            
            # Determine relationship strength
            strength = 'new'
            if profile.total_interactions >= 20:
                strength = 'strong'
            elif profile.total_interactions >= 10:
                strength = 'moderate'
            elif profile.total_interactions >= 3:
                strength = 'weak'
            
            # Determine business context
            keywords = patterns['keywords']
            if any(word in keywords for word in ['contract', 'legal', 'compliance']):
                business_context = 'legal'
            elif any(word in keywords for word in ['investment', 'funding', 'board']):
                business_context = 'strategic'
            elif any(word in keywords for word in ['support', 'issue', 'problem']):
                business_context = 'support'
            elif any(word in keywords for word in ['sale', 'purchase', 'order']):
                business_context = 'transactional'
            else:
                business_context = 'operational'
            
            # Extract thread topics
            thread_topics = list(set([
                word for word, count in keywords.most_common(10)
                if len(word) > 4 and count > 1
            ]))
            
            context = RelationshipContext(
                contact_email=sender_email,
                thread_topics=thread_topics,
                interaction_frequency=frequency,
                relationship_strength=strength,
                business_context=business_context,
                last_action_required=None,  # Would analyze from email content
                pending_items=[]  # Would extract from email analysis
            )
            
            self.relationship_contexts[sender_email] = context

    def _generate_relationship_insights(self) -> Dict[str, any]:
        """Generate insights about relationship patterns."""
        insights = {
            'top_strategic_contacts': [],
            'frequent_communicators': [],
            'dormant_relationships': [],
            'new_relationships': [],
            'escalation_candidates': []
        }
        
        # Top strategic contacts
        strategic = [p for p in self.contact_profiles.values() 
                    if p.importance_level in ['critical', 'high']]
        insights['top_strategic_contacts'] = sorted(
            strategic, key=lambda x: x.escalation_priority, reverse=True
        )[:10]
        
        # Frequent communicators
        frequent = [p for p in self.contact_profiles.values() 
                   if p.recent_interactions >= 5]
        insights['frequent_communicators'] = sorted(
            frequent, key=lambda x: x.recent_interactions, reverse=True
        )[:10]
        
        # Dormant relationships (high importance but no recent contact)
        cutoff_date = datetime.now() - timedelta(days=60)
        dormant = [p for p in self.contact_profiles.values() 
                  if p.importance_level in ['critical', 'high'] 
                  and p.last_contact and p.last_contact < cutoff_date]
        insights['dormant_relationships'] = dormant
        
        # New relationships (first contact in last 30 days)
        recent_cutoff = datetime.now() - timedelta(days=30)
        new = [p for p in self.contact_profiles.values() 
               if p.first_contact and p.first_contact > recent_cutoff]
        insights['new_relationships'] = new
        
        # Escalation candidates (high activity + high importance)
        candidates = [p for p in self.contact_profiles.values() 
                     if p.escalation_priority >= 4 and p.recent_interactions >= 3]
        insights['escalation_candidates'] = candidates
        
        return insights

    def get_contact_intelligence(self, email_address: str) -> Optional[Dict[str, any]]:
        """Get comprehensive intelligence for a specific contact."""
        email_key = email_address.lower()
        
        profile = self.contact_profiles.get(email_key)
        context = self.relationship_contexts.get(email_key)
        
        if not profile:
            return None
        
        return {
            'profile': asdict(profile),
            'context': asdict(context) if context else None,
            'recommendations': self._get_contact_recommendations(profile, context)
        }

    def _get_contact_recommendations(self, profile: ContactProfile, 
                                   context: Optional[RelationshipContext]) -> List[str]:
        """Generate actionable recommendations for a contact."""
        recommendations = []
        
        # Priority-based recommendations
        if profile.escalation_priority >= 4:
            recommendations.append("🚨 High priority - handle immediately")
        
        # Relationship-based recommendations
        if profile.relationship_type == 'board':
            recommendations.append("📋 Board member - ensure full context and prepare thoroughly")
        elif profile.relationship_type == 'investor':
            recommendations.append("💰 Investor communication - be strategic and data-driven")
        elif profile.relationship_type == 'customer':
            recommendations.append("🤝 Customer success priority - ensure satisfaction")
        
        # Activity-based recommendations
        if profile.recent_interactions >= 5:
            recommendations.append("🔥 High activity contact - may need dedicated time block")
        
        # Context-based recommendations
        if context:
            if context.business_context == 'strategic':
                recommendations.append("🎯 Strategic matter - consider CEO-level attention")
            elif context.business_context == 'legal':
                recommendations.append("⚖️ Legal implications - involve legal team if needed")
        
        # Follow-up recommendations
        if profile.last_contact:
            days_since = (datetime.now() - profile.last_contact).days
            if days_since > 30 and profile.importance_level in ['critical', 'high']:
                recommendations.append("📅 Long overdue - consider proactive outreach")
        
        return recommendations

async def analyze_relationship_intelligence(limit: int = 1000):
    """Analyze relationships and generate intelligence report."""
    console.print(Panel.fit(
        "[bold cyan]🧠 Relationship Intelligence Analysis[/bold cyan]",
        border_style="cyan"
    ))
    
    # Initialize system
    ri = RelationshipIntelligence()
    db = DatabaseManager()
    
    # Get emails for analysis
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        from email_agent.models import Email, EmailAddress, EmailCategory, EmailPriority
        
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
    
    # Analyze relationships
    analysis_results = await ri.analyze_relationships(emails)
    
    # Display results
    console.print("\n[bold]📊 Relationship Analysis Results:[/bold]")
    console.print(f"  • Total contacts analyzed: {analysis_results['total_contacts']}")
    console.print(f"  • Strategic contacts identified: [yellow]{analysis_results['strategic_contacts']}[/yellow]")
    
    insights = analysis_results['relationship_insights']
    
    # Strategic contacts table
    if insights['top_strategic_contacts']:
        console.print("\n[bold]🎯 Top Strategic Contacts:[/bold]")
        strategic_table = Table(show_header=True, header_style="bold cyan")
        strategic_table.add_column("Contact", style="cyan", width=25)
        strategic_table.add_column("Company", style="yellow", width=20)
        strategic_table.add_column("Type", style="green")
        strategic_table.add_column("Priority", justify="center")
        strategic_table.add_column("Recent Activity", justify="center")
        
        for contact in insights['top_strategic_contacts'][:10]:
            strategic_table.add_row(
                contact.name or contact.email.split('@')[0],
                contact.company or 'Unknown',
                contact.relationship_type.title(),
                str(contact.escalation_priority),
                str(contact.recent_interactions)
            )
        
        console.print(strategic_table)
    
    # Escalation candidates
    if insights['escalation_candidates']:
        console.print("\n[bold red]🚨 Immediate Escalation Candidates:[/bold red]")
        for contact in insights['escalation_candidates'][:5]:
            console.print(f"  • [red]{contact.name or contact.email}[/red] ({contact.relationship_type}) - {contact.recent_interactions} recent emails")
    
    # Dormant relationships
    if insights['dormant_relationships']:
        console.print("\n[bold yellow]💤 Dormant Strategic Relationships:[/bold yellow]")
        for contact in insights['dormant_relationships'][:5]:
            days_since = (datetime.now() - contact.last_contact).days if contact.last_contact else 999
            console.print(f"  • [yellow]{contact.name or contact.email}[/yellow] ({contact.relationship_type}) - {days_since} days since last contact")
    
    # New relationships
    if insights['new_relationships']:
        console.print("\n[bold green]🆕 New Relationships (Last 30 Days):[/bold green]")
        for contact in insights['new_relationships'][:5]:
            console.print(f"  • [green]{contact.name or contact.email}[/green] ({contact.relationship_type}) - {contact.total_interactions} interactions")
    
    # Recommendations
    console.print(Panel("""[bold yellow]🧠 Relationship Intelligence Recommendations:[/bold yellow]

[bold]Immediate Actions:[/bold]
• Review escalation candidates for urgent attention
• Reach out to dormant strategic relationships  
• Set up structured follow-up for new high-value contacts
• Create dedicated time blocks for frequent strategic communicators

[bold]System Enhancements:[/bold]
• Auto-escalate emails from priority 5 contacts
• Set up alerts for dormant strategic relationships
• Create personalized response templates by relationship type
• Implement relationship scoring in email labeling

[bold]Strategic Insights:[/bold]
• Monitor new relationship development patterns
• Track response time expectations by contact type
• Analyze communication frequency for relationship health
• Use relationship context for smarter email prioritization""", border_style="green"))
    
    return ri

if __name__ == "__main__":
    import sys
    limit = 1000
    if len(sys.argv) > 1:
        limit = int(sys.argv[1])
    
    import asyncio
    asyncio.run(analyze_relationship_intelligence(limit))