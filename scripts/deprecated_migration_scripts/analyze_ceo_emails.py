#!/usr/bin/env python3
"""Analyze CEO email patterns to design optimal labeling system."""

import asyncio
import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from email_agent.storage.database import DatabaseManager
from email_agent.models import Email, EmailAddress, EmailCategory, EmailPriority
from email_agent.agents.action_extractor import ActionExtractorAgent
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import re

console = Console()

async def analyze_ceo_email_patterns(limit: int = 100):
    """Analyze email patterns to design CEO-optimized labels."""
    
    console.print(Panel.fit("[bold cyan]🎯 CEO Email Pattern Analysis[/bold cyan]", border_style="cyan"))
    
    # Initialize components
    db = DatabaseManager()
    extractor = ActionExtractorAgent()
    
    # Get a diverse sample of emails
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        
        emails_orm = session.query(EmailORM).order_by(EmailORM.received_date.desc()).limit(limit).all()
        
        console.print(f"\n📊 Analyzing [yellow]{len(emails_orm)}[/yellow] emails to understand patterns...\n")
        
        # Convert to Email objects
        emails = []
        for e in emails_orm:
            tags = []
            if e.tags:
                try:
                    tags = json.loads(e.tags) if isinstance(e.tags, str) else e.tags
                except:
                    tags = []
            
            email = Email(
                id=e.id,
                message_id=e.message_id,
                thread_id=e.thread_id,
                subject=e.subject,
                sender=EmailAddress(email=e.sender_email, name=e.sender_name),
                recipients=[],
                date=e.date,
                received_date=e.received_date,
                body=e.body_text or e.subject or '',
                is_read=e.is_read,
                is_flagged=e.is_flagged,
                category=EmailCategory(e.category) if e.category else EmailCategory.PERSONAL,
                priority=EmailPriority(e.priority) if e.priority else EmailPriority.NORMAL,
                tags=tags
            )
            emails.append(email)
    
    # Pattern analysis
    patterns = {
        'domains': Counter(),
        'keywords': Counter(),
        'sender_types': defaultdict(list),
        'time_patterns': defaultdict(int),
        'subject_patterns': [],
        'investor_related': [],
        'customer_related': [],
        'team_related': [],
        'vendor_related': [],
        'legal_related': [],
        'financial_related': [],
        'product_related': [],
        'marketing_related': [],
        'networking_related': []
    }
    
    # Keywords to identify different email types
    investor_keywords = ['investor', 'investment', 'funding', 'term sheet', 'dd', 'due diligence', 'cap table', 'board', 'advisor', 'lp', 'vc', 'venture', 'pitch', 'deck']
    customer_keywords = ['customer', 'client', 'user', 'feedback', 'support', 'complaint', 'feature request', 'demo', 'trial', 'subscription', 'churn', 'onboarding']
    team_keywords = ['team', 'employee', 'hire', 'hiring', 'candidate', 'interview', 'performance', 'review', '1:1', 'standup', 'sprint', 'retro']
    vendor_keywords = ['vendor', 'supplier', 'contract', 'invoice', 'payment', 'service provider', 'sla', 'renewal']
    legal_keywords = ['legal', 'contract', 'agreement', 'nda', 'terms', 'compliance', 'gdpr', 'privacy', 'trademark', 'patent', 'lawsuit']
    financial_keywords = ['financial', 'revenue', 'burn rate', 'runway', 'metrics', 'mrr', 'arr', 'accounting', 'tax', 'audit', 'expense']
    product_keywords = ['product', 'feature', 'bug', 'release', 'roadmap', 'sprint', 'engineering', 'design', 'ux', 'api', 'integration']
    marketing_keywords = ['marketing', 'campaign', 'launch', 'pr', 'press', 'blog', 'content', 'seo', 'growth', 'acquisition', 'conversion']
    networking_keywords = ['coffee', 'lunch', 'dinner', 'meetup', 'conference', 'event', 'introduction', 'connect', 'catch up', 'networking']
    
    # Analyze each email
    for email in emails:
        # Domain analysis
        domain = email.sender.email.split('@')[-1] if '@' in email.sender.email else 'unknown'
        patterns['domains'][domain] += 1
        
        # Time pattern analysis
        if email.received_date:
            hour = email.received_date.hour
            if 6 <= hour < 9:
                patterns['time_patterns']['early_morning'] += 1
            elif 9 <= hour < 17:
                patterns['time_patterns']['business_hours'] += 1
            elif 17 <= hour < 20:
                patterns['time_patterns']['evening'] += 1
            else:
                patterns['time_patterns']['after_hours'] += 1
        
        # Content analysis
        body_text = getattr(email, 'body_text', getattr(email, 'body', ''))
        combined_text = f"{email.subject} {body_text}".lower()
        
        # Categorize by content
        if any(kw in combined_text for kw in investor_keywords):
            patterns['investor_related'].append(email.subject)
        if any(kw in combined_text for kw in customer_keywords):
            patterns['customer_related'].append(email.subject)
        if any(kw in combined_text for kw in team_keywords):
            patterns['team_related'].append(email.subject)
        if any(kw in combined_text for kw in vendor_keywords):
            patterns['vendor_related'].append(email.subject)
        if any(kw in combined_text for kw in legal_keywords):
            patterns['legal_related'].append(email.subject)
        if any(kw in combined_text for kw in financial_keywords):
            patterns['financial_related'].append(email.subject)
        if any(kw in combined_text for kw in product_keywords):
            patterns['product_related'].append(email.subject)
        if any(kw in combined_text for kw in marketing_keywords):
            patterns['marketing_related'].append(email.subject)
        if any(kw in combined_text for kw in networking_keywords):
            patterns['networking_related'].append(email.subject)
        
        # Extract key phrases
        words = combined_text.split()
        for i in range(len(words) - 1):
            bigram = f"{words[i]} {words[i+1]}"
            if len(bigram) > 5 and not any(char in bigram for char in '[](){}<>@#'):
                patterns['keywords'][bigram] += 1
    
    # Display analysis results
    console.print("\n[bold]📈 Email Pattern Analysis Results[/bold]\n")
    
    # Top domains
    console.print("[bold cyan]Top Email Domains:[/bold cyan]")
    domain_table = Table(show_header=True, header_style="bold")
    domain_table.add_column("Domain", style="cyan")
    domain_table.add_column("Count", justify="right")
    
    for domain, count in patterns['domains'].most_common(10):
        domain_table.add_row(domain, str(count))
    
    console.print(domain_table)
    
    # Category distribution
    console.print("\n[bold cyan]Email Categories Identified:[/bold cyan]")
    category_table = Table(show_header=True, header_style="bold")
    category_table.add_column("Category", style="yellow")
    category_table.add_column("Count", justify="right")
    category_table.add_column("Examples", style="dim")
    
    categories = [
        ("Investor Relations", patterns['investor_related']),
        ("Customer/User", patterns['customer_related']),
        ("Team/HR", patterns['team_related']),
        ("Vendor/Supplier", patterns['vendor_related']),
        ("Legal/Compliance", patterns['legal_related']),
        ("Financial/Metrics", patterns['financial_related']),
        ("Product/Engineering", patterns['product_related']),
        ("Marketing/Growth", patterns['marketing_related']),
        ("Networking/Events", patterns['networking_related'])
    ]
    
    for category, emails_list in categories:
        count = len(emails_list)
        if count > 0:
            example = emails_list[0][:40] + "..." if emails_list else ""
            category_table.add_row(category, str(count), example)
    
    console.print(category_table)
    
    # Time patterns
    console.print("\n[bold cyan]Email Time Patterns:[/bold cyan]")
    time_table = Table(show_header=True, header_style="bold")
    time_table.add_column("Time Period", style="green")
    time_table.add_column("Count", justify="right")
    
    for period, count in patterns['time_patterns'].items():
        time_table.add_row(period.replace('_', ' ').title(), str(count))
    
    console.print(time_table)
    
    # Recommended labels
    console.print("\n[bold green]🏷️  Recommended CEO Label System:[/bold green]\n")
    
    recommendations = Panel("""[bold yellow]Strategic Labels:[/bold yellow]
• EmailAgent/CEO/Investors - All investor communications, updates, pitches
• EmailAgent/CEO/Customers - Customer feedback, issues, success stories
• EmailAgent/CEO/Team - Team matters, hiring, performance, culture
• EmailAgent/CEO/Board - Board communications and materials
• EmailAgent/CEO/Metrics - KPIs, financial reports, data requests

[bold yellow]Operational Labels:[/bold yellow]
• EmailAgent/CEO/Legal - Contracts, compliance, legal matters
• EmailAgent/CEO/Finance - Financial ops, accounting, expenses
• EmailAgent/CEO/Product - Product decisions, roadmap, features
• EmailAgent/CEO/Vendors - Vendor relationships and contracts
• EmailAgent/CEO/PR-Marketing - Press, marketing, external comms

[bold yellow]Time-Sensitive Labels:[/bold yellow]
• EmailAgent/CEO/DecisionRequired - Needs CEO decision
• EmailAgent/CEO/SignatureRequired - Needs CEO signature
• EmailAgent/CEO/WeeklyReview - Review in weekly planning
• EmailAgent/CEO/Delegatable - Can be delegated to team

[bold yellow]Relationship Labels:[/bold yellow]
• EmailAgent/CEO/KeyRelationships - Important contacts to maintain
• EmailAgent/CEO/Networking - Networking and relationship building
• EmailAgent/CEO/Advisors - Advisor communications

[bold yellow]Personal Efficiency:[/bold yellow]
• EmailAgent/CEO/QuickWins - Can be handled in <5 minutes
• EmailAgent/CEO/DeepWork - Requires focused time block
• EmailAgent/CEO/ReadLater - Informational, non-urgent""", 
        border_style="green")
    
    console.print(recommendations)
    
    return patterns

if __name__ == "__main__":
    asyncio.run(analyze_ceo_email_patterns())