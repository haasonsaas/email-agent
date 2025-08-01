"""CEO-focused email management commands."""

import asyncio
import json
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from collections import defaultdict

from ...agents.ceo_assistant import CEOAssistantAgent
from ...agents.action_extractor import ActionExtractorAgent
from ...storage.database import DatabaseManager
from ...models import Email, EmailAddress, EmailCategory, EmailPriority
from ...connectors.gmail_service import GmailService

console = Console()


import typer

app = typer.Typer(help="CEO-focused email management commands")


@app.command()
def label(limit: int = typer.Option(500, "--limit", "-l", help="Number of emails to process"),
         dry_run: bool = typer.Option(False, "--dry-run", help="Analyze without applying labels")):
    """Apply CEO labels to emails in Gmail."""
    asyncio.run(_label_emails(limit, dry_run))


@app.command()
def analyze():
    """Analyze CEO-labeled emails and show insights."""
    asyncio.run(_analyze_labels())


@app.command()
def setup():
    """Create all CEO labels in Gmail."""
    asyncio.run(_setup_labels())


@app.command()
def pull(days: int = typer.Option(90, "--days", "-d", help="Days back to pull emails"),
         max_emails: int = typer.Option(1000, "--max-emails", "-m", help="Maximum emails to pull")):
    """Pull emails from Gmail for processing."""
    asyncio.run(_pull_emails(days, max_emails))


async def _setup_labels():
    """Create CEO label system in Gmail."""
    console.print(Panel.fit("[bold cyan]🏢 Setting up CEO Label System[/bold cyan]", border_style="cyan"))
    
    # CEO Label System
    CEO_LABELS = {
        # Strategic Labels
        'EmailAgent/CEO/Investors': {'color': '1c4587', 'desc': 'Investor communications'},
        'EmailAgent/CEO/Customers': {'color': '16a766', 'desc': 'Customer feedback'},
        'EmailAgent/CEO/Team': {'color': '8e63ce', 'desc': 'Team & HR matters'},
        'EmailAgent/CEO/Board': {'color': '434343', 'desc': 'Board communications'},
        'EmailAgent/CEO/Metrics': {'color': 'fad165', 'desc': 'KPIs & reports'},
        
        # Operational Labels
        'EmailAgent/CEO/Legal': {'color': '8e63ce', 'desc': 'Legal & compliance'},
        'EmailAgent/CEO/Finance': {'color': '16a766', 'desc': 'Financial operations'},
        'EmailAgent/CEO/Product': {'color': '1c4587', 'desc': 'Product decisions'},
        'EmailAgent/CEO/Vendors': {'color': 'fb4c2f', 'desc': 'Vendor relationships'},
        'EmailAgent/CEO/PR-Marketing': {'color': 'e07798', 'desc': 'External comms'},
        
        # Time-Sensitive Labels
        'EmailAgent/CEO/DecisionRequired': {'color': 'fb4c2f', 'desc': 'Needs CEO decision'},
        'EmailAgent/CEO/SignatureRequired': {'color': 'ffad47', 'desc': 'Needs signature'},
        'EmailAgent/CEO/WeeklyReview': {'color': 'ffad47', 'desc': 'Weekly planning'},
        'EmailAgent/CEO/Delegatable': {'color': '16a766', 'desc': 'Can be delegated'},
        
        # Relationship Labels
        'EmailAgent/CEO/KeyRelationships': {'color': '8e63ce', 'desc': 'Important contacts'},
        'EmailAgent/CEO/Networking': {'color': '1c4587', 'desc': 'Network building'},
        'EmailAgent/CEO/Advisors': {'color': '1c4587', 'desc': 'Advisor comms'},
        
        # Personal Efficiency
        'EmailAgent/CEO/QuickWins': {'color': '16a766', 'desc': 'Handle in <5 min'},
        'EmailAgent/CEO/DeepWork': {'color': '8e63ce', 'desc': 'Requires focus time'},
        'EmailAgent/CEO/ReadLater': {'color': '999999', 'desc': 'Non-urgent info'},
        
        # Additional Action Labels
        'EmailAgent/Actions/HighPriority': {'color': 'fb4c2f', 'desc': 'High priority'},
        'EmailAgent/Actions/MeetingRequest': {'color': '1c4587', 'desc': 'Meeting requests'},
        'EmailAgent/Actions/Deadline': {'color': 'ffad47', 'desc': 'Has deadline'},
        'EmailAgent/Actions/WaitingFor': {'color': 'fad165', 'desc': 'Waiting for response'},
        'EmailAgent/Actions/Commitment': {'color': '8e63ce', 'desc': 'Commitments made'},
        'EmailAgent/Receipts': {'color': '666666', 'desc': 'Receipts & transactions'},
        'EmailAgent/Processed': {'color': '16a766', 'desc': 'Processed by system'}
    }
    
    # Initialize Gmail service
    import keyring
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    
    creds_json = keyring.get_password("email_agent", "gmail_credentials_default")
    if not creds_json:
        console.print("[red]❌ No Gmail credentials found. Run 'email-agent config gmail' first.[/red]")
        return
    
    creds_data = json.loads(creds_json)
    creds = Credentials.from_authorized_user_info(creds_data, [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ])
    
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
    service = build('gmail', 'v1', credentials=creds)
    
    # Get existing labels
    results = service.users().labels().list(userId='me').execute()
    existing_labels = {label['name']: label['id'] for label in results.get('labels', [])}
    
    # Create labels
    created = 0
    existing = 0
    
    for label_name, config in CEO_LABELS.items():
        if label_name not in existing_labels:
            try:
                label_body = {
                    'name': label_name,
                    'labelListVisibility': 'labelShow',
                    'messageListVisibility': 'show',
                    'color': {
                        'backgroundColor': f"#{config['color']}",
                        'textColor': '#ffffff'
                    }
                }
                
                service.users().labels().create(userId='me', body=label_body).execute()
                console.print(f"✅ Created: {label_name}")
                created += 1
            except Exception as e:
                console.print(f"❌ Failed: {label_name} - {str(e)[:50]}")
        else:
            existing += 1
    
    console.print(f"\n[bold green]Summary:[/bold green]")
    console.print(f"  • Created: [green]{created}[/green] new labels")
    console.print(f"  • Existing: [yellow]{existing}[/yellow] labels already present")
    console.print(f"  • Total: [cyan]{len(CEO_LABELS)}[/cyan] labels available")


async def _label_emails(limit: int, dry_run: bool):
    """Apply CEO labels to emails."""
    console.print(f"[bold cyan]🏷️  {'Analyzing' if dry_run else 'Labeling'} up to {limit} emails[/bold cyan]\n")
    
    # Initialize
    db = DatabaseManager()
    ceo_assistant = CEOAssistantAgent()
    action_extractor = ActionExtractorAgent()
    
    # Gmail setup
    import keyring
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    
    creds_json = keyring.get_password("email_agent", "gmail_credentials_default")
    if not creds_json:
        console.print("[red]❌ No Gmail credentials found. Run 'email-agent config gmail' first.[/red]")
        return
    
    creds_data = json.loads(creds_json)
    gmail_service = GmailService(creds_data)
    await gmail_service.authenticate()
    
    # Also get raw service for labeling
    creds = Credentials.from_authorized_user_info(creds_data, [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.modify'
    ])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    service = build('gmail', 'v1', credentials=creds)
    
    # Get label map
    await gmail_service.create_action_labels()  # Ensure labels exist
    results = service.users().labels().list(userId='me').execute()
    label_map = {label['name']: label['id'] for label in results.get('labels', [])}
    
    # Get emails to process
    with db.get_session() as session:
        from ...storage.models import EmailORM
        
        emails_orm = session.query(EmailORM).filter(
            ~EmailORM.tags.like('%ceo_labeled%')
        ).limit(limit).all()
        
        console.print(f"📧 Found [yellow]{len(emails_orm)}[/yellow] emails to process\n")
        
        if not emails_orm:
            console.print("[green]✅ All emails already processed![/green]")
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
    
    # Statistics
    stats = defaultdict(int)
    label_counts = defaultdict(int)
    
    # Process emails
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Processing emails...", total=len(emails))
        
        # Process in batches
        batch_size = 5
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i+batch_size]
            
            # Analyze batch
            for email in batch:
                try:
                    # Get both CEO and action analysis
                    ceo_analysis = await ceo_assistant.analyze_for_ceo(email)
                    action_analysis = await action_extractor.extract_actions(email)
                    
                    all_labels = []
                    
                    # CEO labels
                    if 'error' not in ceo_analysis:
                        ceo_labels = ceo_analysis.get('ceo_labels', [])
                        all_labels.extend(ceo_labels)
                    
                    # Action labels based on receipt handling
                    if 'error' not in action_analysis:
                        if action_analysis.get('email_type') == 'receipt':
                            all_labels.append('Receipts')
                        else:
                            if action_analysis.get('response_urgency') == 'urgent':
                                all_labels.append('Actions/HighPriority')
                            if action_analysis.get('meeting_requests'):
                                all_labels.append('Actions/MeetingRequest')
                            if any(item.get('deadline') for item in action_analysis.get('action_items', [])):
                                all_labels.append('Actions/Deadline')
                    
                    # Apply labels if not dry run
                    if all_labels and not dry_run and email.message_id:
                        msg_id = email.message_id.strip('<>')
                        query = f'rfc822msgid:{msg_id}'
                        
                        try:
                            results = service.users().messages().list(userId='me', q=query).execute()
                            
                            if results.get('messages'):
                                gmail_msg_id = results['messages'][0]['id']
                                
                                # Build label list
                                labels_to_add = []
                                for label_name in all_labels:
                                    if '/' not in label_name:
                                        label_name = f'CEO/{label_name}'
                                    full_label = f'EmailAgent/{label_name}'
                                    if full_label in label_map:
                                        labels_to_add.append(label_map[full_label])
                                        
                                        # Track stats
                                        short_name = label_name.replace('CEO/', '').replace('Actions/', '')
                                        label_counts[short_name] += 1
                                
                                # Add processed label
                                if 'EmailAgent/Processed' in label_map:
                                    labels_to_add.append(label_map['EmailAgent/Processed'])
                                
                                # Apply labels
                                if labels_to_add:
                                    body = {'addLabelIds': labels_to_add}
                                    service.users().messages().modify(
                                        userId='me', id=gmail_msg_id, body=body
                                    ).execute()
                                    stats['labeled'] += 1
                        except:
                            stats['not_found'] += 1
                    
                    # Show progress
                    if all_labels:
                        label_str = ', '.join(l.replace('CEO/', '').replace('Actions/', '') for l in all_labels[:3])
                        if len(all_labels) > 3:
                            label_str += f' +{len(all_labels)-3}'
                        color = 'yellow' if dry_run else 'green'
                        progress.console.print(f"   {'🔍' if dry_run else '✅'} {email.subject[:40]}... → [{color}]{label_str}[/{color}]")
                    
                    # Mark as processed in database
                    if not dry_run:
                        with db.get_session() as session:
                            from ...storage.models import EmailORM
                            email_orm = session.query(EmailORM).filter_by(id=email.id).first()
                            if email_orm:
                                current_tags = json.loads(email_orm.tags) if isinstance(email_orm.tags, str) else (email_orm.tags or [])
                                if 'ceo_labeled' not in current_tags:
                                    current_tags.append('ceo_labeled')
                                email_orm.tags = json.dumps(current_tags)
                                session.commit()
                    
                    stats['processed'] += 1
                    
                except Exception as e:
                    stats['errors'] += 1
                    console.print(f"[red]Error: {str(e)[:50]}[/red]")
                
                progress.advance(task)
            
            # Small delay between batches
            await asyncio.sleep(0.1)
    
    # Display results
    console.print(f"\n[bold green]✅ {'Analysis' if dry_run else 'Labeling'} Complete![/bold green]\n")
    
    # Statistics
    console.print("[bold]📊 Results:[/bold]")
    console.print(f"  • Emails processed: {stats['processed']}")
    if not dry_run:
        console.print(f"  • Successfully labeled: [green]{stats['labeled']}[/green]")
        console.print(f"  • Not found in Gmail: [yellow]{stats['not_found']}[/yellow]")
    console.print(f"  • Errors: [red]{stats['errors']}[/red]")
    
    # Label distribution
    if label_counts:
        console.print("\n[bold]🏷️  Label Distribution:[/bold]")
        sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)
        for label, count in sorted_labels[:10]:
            bar = "█" * min(count // 2, 20)
            console.print(f"  {label:<20} {bar} {count}")


async def _analyze_labels():
    """Analyze CEO-labeled emails."""
    console.print(Panel.fit("[bold cyan]🎯 CEO Email Analysis[/bold cyan]", border_style="cyan"))
    
    # Gmail setup
    import keyring
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    
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
    
    # Get CEO labels
    results = service.users().labels().list(userId='me').execute()
    ceo_labels = {label['name']: label['id'] for label in results.get('labels', []) 
                  if label['name'].startswith('EmailAgent/')}
    
    # Analyze each label
    label_stats = {}
    sample_emails = defaultdict(list)
    
    for label_name, label_id in ceo_labels.items():
        try:
            results = service.users().messages().list(
                userId='me',
                labelIds=[label_id],
                maxResults=100
            ).execute()
            
            messages = results.get('messages', [])
            label_stats[label_name] = len(messages)
            
            # Get samples for important labels
            short_name = label_name.replace('EmailAgent/CEO/', '').replace('EmailAgent/Actions/', '').replace('EmailAgent/', '')
            important = ['DecisionRequired', 'Investors', 'Customers', 'QuickWins', 'HighPriority']
            
            if short_name in important and messages:
                for msg in messages[:3]:
                    try:
                        message = service.users().messages().get(
                            userId='me',
                            id=msg['id'],
                            format='metadata',
                            metadataHeaders=['Subject', 'From', 'Date']
                        ).execute()
                        
                        headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
                        sample_emails[short_name].append({
                            'subject': headers.get('Subject', 'No Subject'),
                            'from': headers.get('From', 'Unknown')
                        })
                    except:
                        pass
        except:
            pass
    
    # Display results
    table = Table(title="Email Label Distribution", show_header=True, header_style="bold cyan")
    table.add_column("Label", style="cyan", width=25)
    table.add_column("Count", justify="right", style="yellow")
    table.add_column("Visual", style="green")
    
    sorted_labels = sorted(label_stats.items(), key=lambda x: x[1], reverse=True)
    for label, count in sorted_labels:
        if count > 0:
            short_name = label.replace('EmailAgent/CEO/', '').replace('EmailAgent/Actions/', '').replace('EmailAgent/', '')
            bar = "█" * min(count // 3, 20)
            table.add_row(short_name, str(count), bar)
    
    console.print(table)
    
    # Show samples
    if sample_emails:
        console.print("\n[bold]📧 Sample Emails:[/bold]\n")
        
        for category, emails in sample_emails.items():
            console.print(f"[bold]{category}:[/bold]")
            for email in emails:
                console.print(f"  • {email['subject'][:50]}...")
                console.print(f"    From: {email['from'][:40]}...")
            console.print()
    
    # Summary
    total = sum(label_stats.values())
    console.print(Panel(f"""[bold]📈 Summary[/bold]
    
Total labeled emails: {total}

[bold green]💡 Next Actions:[/bold green]
1. Check DecisionRequired emails first
2. Review Investor communications  
3. Knock out QuickWins during breaks
4. Schedule time for DeepWork items""", border_style="green"))


async def _pull_emails(days: int, max_emails: int):
    """Pull emails from Gmail."""
    console.print(f"[bold cyan]📥 Pulling emails from last {days} days[/bold cyan]\n")
    
    from ...connectors.gmail import GmailConnector
    db = DatabaseManager()
    
    # Initialize Gmail connector
    import keyring
    creds_json = keyring.get_password("email_agent", "gmail_credentials_default")
    if not creds_json:
        console.print("[red]❌ No Gmail credentials found. Run 'email-agent config gmail' first.[/red]")
        return
    
    creds_data = json.loads(creds_json)
    
    # Note: This is a simplified version. In production, you'd want to implement
    # proper pagination and batch processing as shown in the original pull_gmail_directly.py
    console.print("This command is not yet fully implemented in the CLI.")
    console.print("Use 'email-agent pull sync' for now.")