#!/usr/bin/env python3
"""Generate CEO insights from processed emails."""

from email_agent.storage.database import DatabaseManager
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict

console = Console()

def generate_ceo_insights():
    """Generate actionable insights from CEO-labeled emails."""
    
    console.print(Panel.fit("[bold cyan]🎯 CEO Email Insights Dashboard[/bold cyan]", border_style="cyan"))
    
    db = DatabaseManager()
    
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        
        # Get all CEO-processed emails
        processed_emails = session.query(EmailORM).filter(
            EmailORM.tags.like('%ceo_processed%')
        ).all()
        
        console.print(f"\n📊 Analyzed [yellow]{len(processed_emails)}[/yellow] emails\n")
        
        # Extract insights
        decision_required = []
        investor_emails = []
        customer_emails = []
        team_emails = []
        quick_wins = []
        deep_work = []
        key_relationships = []
        
        sender_frequency = Counter()
        domain_frequency = Counter()
        
        for email in processed_emails:
            # Parse tags to find CEO labels
            tags = json.loads(email.tags) if email.tags else []
            
            # Check Gmail labels in connector_data
            connector_data = json.loads(email.connector_data) if email.connector_data else {}
            gmail_labels = connector_data.get('gmail_labels', [])
            
            # Count sender frequency
            sender_frequency[email.sender_email] += 1
            domain = email.sender_email.split('@')[-1] if '@' in email.sender_email else 'unknown'
            domain_frequency[domain] += 1
            
            # Look for CEO labels
            for label in gmail_labels:
                if 'DecisionRequired' in label:
                    decision_required.append({
                        'subject': email.subject,
                        'from': f"{email.sender_name or email.sender_email}",
                        'date': email.received_date
                    })
                elif 'Investors' in label:
                    investor_emails.append({
                        'subject': email.subject,
                        'from': f"{email.sender_name or email.sender_email}",
                        'date': email.received_date
                    })
                elif 'Customers' in label:
                    customer_emails.append({
                        'subject': email.subject,
                        'from': f"{email.sender_name or email.sender_email}",
                        'date': email.received_date
                    })
                elif 'Team' in label:
                    team_emails.append({
                        'subject': email.subject,
                        'from': f"{email.sender_name or email.sender_email}",
                        'date': email.received_date
                    })
                elif 'QuickWins' in label:
                    quick_wins.append({
                        'subject': email.subject,
                        'from': f"{email.sender_name or email.sender_email}",
                        'date': email.received_date
                    })
                elif 'DeepWork' in label:
                    deep_work.append({
                        'subject': email.subject,
                        'from': f"{email.sender_name or email.sender_email}",
                        'date': email.received_date
                    })
                elif 'KeyRelationships' in label:
                    key_relationships.append({
                        'subject': email.subject,
                        'from': f"{email.sender_name or email.sender_email}",
                        'date': email.received_date
                    })
    
    # Display insights
    if decision_required:
        console.print("[bold red]🔴 Decisions Required:[/bold red]")
        for item in decision_required[:5]:
            console.print(f"  • {item['subject'][:60]}...")
            console.print(f"    From: {item['from']} ({item['date'].strftime('%b %d')})")
        if len(decision_required) > 5:
            console.print(f"    ... and {len(decision_required) - 5} more")
        console.print()
    
    if investor_emails:
        console.print("[bold yellow]💰 Investor Communications:[/bold yellow]")
        for item in investor_emails[:5]:
            console.print(f"  • {item['subject'][:60]}...")
            console.print(f"    From: {item['from']} ({item['date'].strftime('%b %d')})")
        if len(investor_emails) > 5:
            console.print(f"    ... and {len(investor_emails) - 5} more")
        console.print()
    
    if quick_wins:
        console.print("[bold green]✅ Quick Wins (< 5 min):[/bold green]")
        for item in quick_wins[:10]:
            console.print(f"  • {item['subject'][:50]}... - {item['from']}")
        if len(quick_wins) > 10:
            console.print(f"    ... and {len(quick_wins) - 10} more")
        console.print()
    
    # Top senders
    console.print("[bold cyan]👥 Most Frequent Senders:[/bold cyan]")
    top_senders = sender_frequency.most_common(10)
    for sender, count in top_senders:
        console.print(f"  • {sender}: {count} emails")
    console.print()
    
    # Domain analysis
    console.print("[bold magenta]🌐 Top Email Domains:[/bold magenta]")
    top_domains = domain_frequency.most_common(10)
    for domain, count in top_domains:
        console.print(f"  • {domain}: {count} emails")
    console.print()
    
    # Summary stats
    summary = Panel(f"""[bold]📈 Summary Statistics[/bold]
    
Total Processed: {len(processed_emails)} emails
Decisions Required: {len(decision_required)}
Investor Emails: {len(investor_emails)}
Customer Emails: {len(customer_emails)}
Team/HR Emails: {len(team_emails)}
Quick Wins: {len(quick_wins)}
Deep Work Items: {len(deep_work)}
Key Relationships: {len(key_relationships)}

[bold yellow]💡 Recommendations:[/bold yellow]
1. Focus on {len(decision_required)} decisions that need your attention
2. You have {len(quick_wins)} quick tasks you can knock out in gaps
3. Schedule time for {len(deep_work)} deep work items
4. {len(key_relationships)} key relationship emails to maintain""", border_style="green")
    
    console.print(summary)

if __name__ == "__main__":
    generate_ceo_insights()