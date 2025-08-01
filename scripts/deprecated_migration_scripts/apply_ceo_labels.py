#!/usr/bin/env python3
"""Apply CEO labels to emails using intelligent analysis."""

import asyncio
import json
from datetime import datetime
from email_agent.agents.ceo_assistant import CEOAssistantAgent
from email_agent.storage.database import DatabaseManager
from email_agent.models import Email, EmailAddress, EmailCategory, EmailPriority
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import keyring
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

console = Console()

async def apply_ceo_labels(limit: int = 30):
    """Apply CEO-focused labels to emails."""
    
    console.print(Panel.fit("[bold cyan]🎯 CEO Email Labeling System[/bold cyan]", border_style="cyan"))
    
    # Initialize components
    db = DatabaseManager()
    ceo_assistant = CEOAssistantAgent()
    
    # Get recent emails
    with db.get_session() as session:
        from email_agent.storage.models import EmailORM
        
        # Get emails not yet processed with CEO labels
        query = session.query(EmailORM).filter(
            ~EmailORM.tags.like('%ceo_processed%')
        ).order_by(EmailORM.received_date.desc()).limit(limit)
        
        emails_orm = query.all()
        
        console.print(f"\n📧 Found [yellow]{len(emails_orm)}[/yellow] emails to analyze for CEO")
        
        if not emails_orm:
            console.print("[green]✅ All emails already processed with CEO labels![/green]")
            return
        
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
                body_text=e.body_text or '',
                is_read=e.is_read,
                is_flagged=e.is_flagged,
                category=EmailCategory(e.category) if e.category else EmailCategory.PERSONAL,
                priority=EmailPriority(e.priority) if e.priority else EmailPriority.NORMAL,
                tags=tags
            )
            emails.append(email)
    
    # Load Gmail credentials
    console.print("\n🔐 Authenticating with Gmail...")
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
    
    # Get label IDs
    results = service.users().labels().list(userId='me').execute()
    label_map = {label['name']: label['id'] for label in results.get('labels', [])}
    
    ceo_labels = [l for l in label_map if l.startswith('EmailAgent/CEO/')]
    console.print(f"✅ Connected with [cyan]{len(ceo_labels)}[/cyan] CEO labels available")
    
    # Statistics
    stats = {
        'total': len(emails),
        'processed': 0,
        'labeled': 0,
        'decisions_required': 0,
        'investor_emails': 0,
        'customer_emails': 0,
        'quick_wins': 0,
        'deep_work': 0,
        'delegatable': 0,
        'errors': 0
    }
    
    # Process emails
    console.print(f"\n🧠 Analyzing emails with CEO perspective...\n")
    
    analyzed_emails = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Processing emails...", total=len(emails))
        
        for email in emails:
            progress.update(task, description=f"[cyan]Analyzing: {email.subject[:40]}...")
            
            try:
                # Analyze with CEO perspective
                analysis = await ceo_assistant.analyze_for_ceo(email)
                analyzed_emails.append({'email': email, 'analysis': analysis})
                
                if 'error' in analysis:
                    stats['errors'] += 1
                    progress.advance(task)
                    continue
                
                stats['processed'] += 1
                
                # Determine which labels to apply
                ceo_label_names = analysis.get('ceo_labels', [])
                labels_to_add = []
                
                for label_name in ceo_label_names:
                    full_label = f'EmailAgent/CEO/{label_name}'
                    if full_label in label_map:
                        labels_to_add.append(label_map[full_label])
                        
                        # Update stats
                        if label_name == 'DecisionRequired':
                            stats['decisions_required'] += 1
                        elif label_name == 'Investors':
                            stats['investor_emails'] += 1
                        elif label_name == 'Customers':
                            stats['customer_emails'] += 1
                        elif label_name == 'QuickWins':
                            stats['quick_wins'] += 1
                        elif label_name == 'DeepWork':
                            stats['deep_work'] += 1
                        elif label_name == 'Delegatable':
                            stats['delegatable'] += 1
                
                # Always add processed label
                if 'EmailAgent/Processed' in label_map:
                    labels_to_add.append(label_map['EmailAgent/Processed'])
                
                # Apply labels in Gmail
                if email.message_id and labels_to_add:
                    try:
                        msg_id = email.message_id.strip('<>')
                        query = f'rfc822msgid:{msg_id}'
                        results = service.users().messages().list(userId='me', q=query).execute()
                        
                        if results.get('messages'):
                            gmail_msg_id = results['messages'][0]['id']
                            
                            body = {'addLabelIds': labels_to_add}
                            service.users().messages().modify(
                                userId='me', id=gmail_msg_id, body=body
                            ).execute()
                            
                            stats['labeled'] += 1
                            
                            # Show applied labels
                            if ceo_label_names:
                                importance = analysis.get('strategic_importance', 'low')
                                color = 'red' if importance == 'critical' else 'yellow' if importance == 'high' else 'green'
                                progress.console.print(
                                    f"   ✅ {email.subject[:35]}... → [{color}]{', '.join(ceo_label_names[:3])}[/{color}]"
                                )
                    except Exception as e:
                        if "notFound" not in str(e):
                            progress.console.print(f"   ❌ Failed: {email.subject[:30]}... - {str(e)[:30]}")
                
                # Update database
                with db.get_session() as session:
                    from email_agent.storage.models import EmailORM
                    email_orm = session.query(EmailORM).filter_by(id=email.id).first()
                    if email_orm:
                        current_tags = json.loads(email_orm.tags) if isinstance(email_orm.tags, str) else (email_orm.tags or [])
                        if 'ceo_processed' not in current_tags:
                            current_tags.append('ceo_processed')
                        email_orm.tags = json.dumps(current_tags)
                        session.commit()
                
            except Exception as e:
                stats['errors'] += 1
                progress.console.print(f"   ❌ Error analyzing: {email.subject[:30]}... - {str(e)[:30]}")
            
            progress.advance(task)
    
    # Generate executive brief
    console.print("\n[bold]📋 Generating Executive Brief...[/bold]")
    brief = await ceo_assistant.generate_ceo_brief([item['email'] for item in analyzed_emails[:10]])
    
    # Display statistics
    console.print("\n[bold green]📊 CEO Labeling Complete![/bold green]\n")
    
    # Stats table
    table = Table(title="CEO Email Analysis Results", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan", width=25)
    table.add_column("Count", justify="right", style="magenta")
    table.add_column("Percentage", justify="right", style="green")
    
    table.add_row("Total Emails", str(stats['total']), "100%")
    table.add_row("Successfully Analyzed", str(stats['processed']), f"{stats['processed']/stats['total']*100:.1f}%")
    table.add_row("Labels Applied", str(stats['labeled']), f"{stats['labeled']/stats['total']*100:.1f}%")
    table.add_row("", "", "")
    table.add_row("🔴 Decisions Required", str(stats['decisions_required']), f"{stats['decisions_required']/stats['total']*100:.1f}%")
    table.add_row("💰 Investor Communications", str(stats['investor_emails']), f"{stats['investor_emails']/stats['total']*100:.1f}%")
    table.add_row("👥 Customer Related", str(stats['customer_emails']), f"{stats['customer_emails']/stats['total']*100:.1f}%")
    table.add_row("✅ Quick Wins (<5 min)", str(stats['quick_wins']), f"{stats['quick_wins']/stats['total']*100:.1f}%")
    table.add_row("🧠 Deep Work Required", str(stats['deep_work']), f"{stats['deep_work']/stats['total']*100:.1f}%")
    table.add_row("👥 Can Be Delegated", str(stats['delegatable']), f"{stats['delegatable']/stats['total']*100:.1f}%")
    
    if stats['errors'] > 0:
        table.add_row("", "", "")
        table.add_row("❌ Errors", str(stats['errors']), f"{stats['errors']/stats['total']*100:.1f}%", style="red")
    
    console.print(table)
    
    # Executive Brief
    if brief['critical_items']:
        console.print("\n[bold red]🚨 Critical Items Requiring Attention:[/bold red]")
        for item in brief['critical_items'][:3]:
            console.print(f"  • {item['subject'][:60]}... from {item['from']}")
            if item['insight']:
                console.print(f"    [dim]{item['insight']}[/dim]")
    
    if brief['decisions_needed']:
        console.print("\n[bold yellow]🤔 Decisions Required:[/bold yellow]")
        for decision in brief['decisions_needed'][:5]:
            console.print(f"  • {decision['decision']} ({decision['context'][:40]}...)")
    
    if brief['quick_wins']:
        console.print("\n[bold green]✅ Quick Wins (Handle Now):[/bold green]")
        for win in brief['quick_wins'][:5]:
            console.print(f"  • {win['task'][:50]}... (~{win['time']} min)")
    
    # Time blocking suggestions
    time_blocks = await ceo_assistant.suggest_time_blocks(
        [item['analysis'] for item in analyzed_emails]
    )
    
    console.print("\n[bold cyan]📅 Suggested Time Blocks:[/bold cyan]")
    console.print(f"  • Morning Focus: {len(time_blocks['morning_focus'])} deep work items")
    console.print(f"  • Quick Responses: {len(time_blocks['quick_responses'])} items (<5 min each)")
    console.print(f"  • Afternoon: {len(time_blocks['afternoon_meetings'])} relationship follow-ups")
    console.print(f"  • End of Day: {len(time_blocks['end_of_day_review'])} items to review")
    console.print(f"  • Weekly Planning: {len(time_blocks['weekly_planning'])} items for review")
    
    console.print("\n✨ Check Gmail to see your CEO-optimized email organization!")

if __name__ == "__main__":
    import sys
    limit = 30
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except:
            pass
    
    asyncio.run(apply_ceo_labels(limit=limit))