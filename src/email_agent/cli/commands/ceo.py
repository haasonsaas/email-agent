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
from ...agents.enhanced_ceo_labeler import EnhancedCEOLabeler
from ...agents.relationship_intelligence import RelationshipIntelligence
from ...agents.thread_intelligence import ThreadIntelligence
from ...agents.collaborative_processor import CollaborativeEmailProcessor
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


@app.command()
def intelligence(limit: int = typer.Option(200, "--limit", "-l", help="Number of emails to analyze"),
               dry_run: bool = typer.Option(False, "--dry-run", help="Analyze without applying labels")):
    """Apply enhanced CEO intelligence with relationship and thread analysis."""
    asyncio.run(_apply_intelligence(limit, dry_run))


@app.command()
def relationships(limit: int = typer.Option(1000, "--limit", "-l", help="Number of emails to analyze")):
    """Analyze relationship intelligence and show strategic contacts."""
    asyncio.run(_analyze_relationships(limit))


@app.command()
def threads(limit: int = typer.Option(1000, "--limit", "-l", help="Number of emails to analyze")):
    """Analyze thread intelligence and show conversation patterns."""
    asyncio.run(_analyze_threads(limit))


@app.command()
def collaborative(limit: int = typer.Option(50, "--limit", "-l", help="Number of emails to process"),
                 dry_run: bool = typer.Option(False, "--dry-run", help="Analyze without applying labels"),
                 show_reasoning: bool = typer.Option(True, "--show-reasoning/--hide-reasoning", help="Show detailed agent reasoning")):
    """Process emails using collaborative multi-agent intelligence."""
    asyncio.run(_collaborative_processing(limit, dry_run, show_reasoning))


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


async def _apply_intelligence(limit: int, dry_run: bool):
    """Apply enhanced CEO intelligence with relationship and thread analysis."""
    console.print(Panel.fit(
        "[bold cyan]🧠 Enhanced CEO Intelligence System[/bold cyan]\n"
        "[dim]Advanced email analysis with relationship intelligence[/dim]",
        border_style="cyan"
    ))
    
    # Initialize intelligence systems
    enhanced_labeler = EnhancedCEOLabeler()
    db = DatabaseManager()
    
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
    
    # Get emails for analysis
    with db.get_session() as session:
        from ...storage.models import EmailORM
        
        # Get larger dataset for intelligence building
        all_emails_orm = session.query(EmailORM).order_by(
            EmailORM.received_date.desc()
        ).limit(1000).all()
        
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
    
    # Build intelligence profiles
    await enhanced_labeler.build_sender_profiles(all_emails)
    
    # Get emails to process
    emails_to_process = [email for email in all_emails[:limit] 
                        if 'enhanced_ceo_labeled' not in email.tags]
    
    console.print(f"\n📧 Processing [yellow]{len(emails_to_process)}[/yellow] emails with enhanced intelligence\n")
    
    # Get Gmail label map
    results = service.users().labels().list(userId='me').execute()
    label_map = {label['name']: label['id'] for label in results.get('labels', [])}
    
    # Statistics
    stats = defaultdict(int)
    label_counts = defaultdict(int)
    
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
                labels, reason = await enhanced_labeler.get_enhanced_labels(email)
                
                if reason == "promotional/spam":
                    stats['spam_filtered'] += 1
                    progress.console.print(f"   🚫 [dim]{email.subject[:40]}... (filtered: promotional)[/dim]")
                elif reason == "analysis_error":
                    stats['errors'] += 1
                elif labels:
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
                    sender_profile = enhanced_labeler.sender_profiles.get(email.sender.email.lower())
                    importance = sender_profile.strategic_importance if sender_profile else 'unknown'
                    color = {'critical': 'red', 'high': 'yellow', 'medium': 'cyan', 'low': 'dim'}.get(importance, 'white')
                    label_str = ', '.join(labels)
                    progress.console.print(f"   {'🔍' if dry_run else '🧠'} [{color}]{importance.upper()}[/{color}] {email.subject[:35]}... → [green]{label_str}[/green]")
                    
                    stats['processed'] += 1
                else:
                    stats['skipped'] += 1
                
            except Exception as e:
                stats['errors'] += 1
                console.print(f"[red]Error: {str(e)[:50]}[/red]")
            
            progress.advance(task)
    
    # Display results
    console.print(f"\n[bold green]✅ Enhanced Intelligence Processing Complete![/bold green]\n")
    
    console.print("[bold]📊 Enhanced Results:[/bold]")
    console.print(f"  • Processed with intelligence: {stats['processed']}")
    console.print(f"  • Spam/promotional filtered: [yellow]{stats['spam_filtered']}[/yellow]")
    if not dry_run:
        console.print(f"  • Successfully labeled: [green]{stats['labeled']}[/green]")
    console.print(f"  • Errors: [red]{stats['errors']}[/red]")
    
    if label_counts:
        console.print("\n[bold]🏷️  Intelligent Label Distribution:[/bold]")
        sorted_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)
        for label, count in sorted_labels[:10]:
            bar = "█" * min(count // 2, 20)
            console.print(f"  {label:<20} {bar} {count}")


async def _analyze_relationships(limit: int):
    """Analyze relationship intelligence."""
    console.print(Panel.fit(
        "[bold cyan]🤝 Relationship Intelligence Analysis[/bold cyan]",
        border_style="cyan"
    ))
    
    # Initialize relationship intelligence
    relationship_intel = RelationshipIntelligence()
    db = DatabaseManager()
    
    # Get emails for analysis
    with db.get_session() as session:
        from ...storage.models import EmailORM
        
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
    analysis_results = await relationship_intel.analyze_relationships(emails)
    
    # Display results
    console.print(f"\n[bold]📊 Relationship Analysis Results:[/bold]")
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


async def _analyze_threads(limit: int):
    """Analyze thread intelligence."""
    console.print(Panel.fit(
        "[bold cyan]🧵 Thread Intelligence Analysis[/bold cyan]",
        border_style="cyan"
    ))
    
    # Initialize thread intelligence
    thread_intel = ThreadIntelligence()
    db = DatabaseManager()
    
    # Get emails for analysis
    with db.get_session() as session:
        from ...storage.models import EmailORM
        
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
    analysis_results = await thread_intel.analyze_thread_patterns(emails)
    
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
        
        for thread in insights['stalled_important_threads'][:10]:
            subject = thread.subject_evolution[0] if thread.subject_evolution else "Unknown"
            stalled_table.add_row(
                subject[:35] + "..." if len(subject) > 35 else subject,
                thread.thread_type.title(),
                str(thread.thread_duration_days),
                str(thread.message_count)
            )
        
        console.print(stalled_table)


async def _collaborative_processing(limit: int, dry_run: bool, show_reasoning: bool):
    """Process emails using collaborative multi-agent intelligence."""
    console.print(Panel.fit(
        "[bold cyan]🤝 Collaborative Multi-Agent Email Processing[/bold cyan]", 
        border_style="cyan"
    ))
    
    # Initialize collaborative processor
    console.print("\n[bold]Initializing Collaborative Intelligence...[/bold]")
    processor = CollaborativeEmailProcessor()
    
    # Get Gmail service
    try:
        # For now, use the enhanced CEO labeler's Gmail connection approach
        import keyring
        creds_json = keyring.get_password("email_agent", "gmail_credentials_default")
        if not creds_json:
            console.print("[red]❌ No Gmail credentials found. Run 'email-agent config gmail' first.[/red]")
            return
        
        credentials = json.loads(creds_json)
        gmail_service = GmailService(credentials)
        
        # Get emails from Gmail using database (like other CEO commands)
        with console.status("[bold blue]📧 Fetching emails from database..."):
            db = DatabaseManager()
            from ...storage.models import EmailORM
            
            with db.get_session() as session:
                emails_orm = session.query(EmailORM).order_by(EmailORM.date.desc()).limit(limit).all()
                
                emails = []
                for e in emails_orm:
                    email = Email(
                        id=str(e.id),
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
                        category=EmailCategory(e.category) if e.category else EmailCategory.PRIMARY,
                        priority=EmailPriority(e.priority) if e.priority else EmailPriority.NORMAL,
                        tags=json.loads(e.tags) if e.tags else []
                    )
                    emails.append(email)
        
        if not emails:
            console.print("[yellow]No emails found to process[/yellow]")
            return
        
        console.print(f"[green]✅ Retrieved {len(emails)} emails for collaborative processing[/green]")
        
        # Show processor status
        if show_reasoning:
            status = await processor.get_processor_status()
            console.print(f"\n[dim]Processor: {status['processor_type']} with {status['active_agents']} active agents[/dim]")
        
        # Process emails collaboratively
        results = []
        labels_to_apply = defaultdict(list)
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("🤝 Collaborative processing...", total=len(emails))
            
            for email in emails:
                # Get collaborative decision
                decision = await processor.process_email_collaboratively(email)
                results.append(decision)
                
                # Collect labels for application
                if decision.agreed_labels and not dry_run:
                    labels_to_apply[email.id] = decision.agreed_labels
                
                # Show detailed reasoning for high-priority emails
                if show_reasoning and (decision.final_priority > 0.7 or decision.should_escalate):
                    await _display_collaborative_decision(email, decision)
                
                progress.advance(task)
        
        # Display summary statistics
        await _display_collaborative_summary(results, dry_run)
        
        # Apply labels if not dry run
        if not dry_run and labels_to_apply:
            console.print(f"\n[bold]📋 Applying Labels to {len(labels_to_apply)} emails...[/bold]")
            
            applied_count = 0
            for email_id, labels in labels_to_apply.items():
                try:
                    success = gmail_service.apply_labels(email_id, labels)
                    if success:
                        applied_count += 1
                except Exception as e:
                    console.print(f"[red]Failed to apply labels to {email_id}: {e}[/red]")
            
            console.print(f"[green]✅ Successfully applied labels to {applied_count} emails[/green]")
        
        elif dry_run:
            console.print(f"\n[yellow]🧪 Dry run complete - no labels were applied[/yellow]")
        
    except Exception as e:
        console.print(f"[red]❌ Collaborative processing failed: {e}[/red]")


async def _display_collaborative_decision(email: Email, decision):
    """Display detailed collaborative decision for high-priority emails."""
    
    # Create decision summary
    priority_color = "red" if decision.final_priority > 0.8 else "yellow"
    urgency_icon = "🚨" if decision.should_escalate else "⚡" if decision.final_urgency == "high" else "📋"
    
    decision_text = f"""[bold]{urgency_icon} {email.subject[:60]}...[/bold]
[dim]From: {email.sender.name or email.sender.email}[/dim]

[bold]Collaborative Decision:[/bold]
Priority: [{priority_color}]{decision.final_priority:.2f}[/{priority_color}] | Urgency: {decision.final_urgency.upper()}
Confidence: {decision.consensus_confidence:.1%} | Escalate: {"YES" if decision.should_escalate else "No"}
Labels: {', '.join(decision.agreed_labels) if decision.agreed_labels else 'None'}"""
    
    if decision.conflicts_resolved:
        decision_text += f"\n[red]Conflicts resolved: {len(decision.conflicts_resolved)}[/red]"
    
    console.print(Panel(decision_text, border_style="blue", width=80))
    
    # Show agent reasoning if requested
    if decision.agent_assessments:
        console.print("[dim]Agent Assessments:[/dim]")
        for assessment in decision.agent_assessments:
            if assessment.confidence.value >= 0.6:  # Only show confident assessments
                confidence_color = "green" if assessment.confidence.value > 0.8 else "yellow"
                console.print(f"  [{confidence_color}]{assessment.agent_name}[/{confidence_color}]: {assessment.reasoning}")
    
    console.print()


async def _display_collaborative_summary(results: list, dry_run: bool):
    """Display summary of collaborative processing results."""
    
    if not results:
        return
    
    console.print(f"\n[bold]📊 Collaborative Processing Summary ({len(results)} emails):[/bold]")
    
    # Priority distribution
    critical_count = sum(1 for r in results if r.final_priority > 0.8)
    high_count = sum(1 for r in results if 0.6 < r.final_priority <= 0.8)
    medium_count = sum(1 for r in results if 0.4 < r.final_priority <= 0.6)
    low_count = sum(1 for r in results if r.final_priority <= 0.4)
    
    # Confidence distribution
    high_confidence = sum(1 for r in results if r.consensus_confidence > 0.7)
    medium_confidence = sum(1 for r in results if 0.5 < r.consensus_confidence <= 0.7)
    low_confidence = sum(1 for r in results if r.consensus_confidence <= 0.5)
    
    # Escalations and conflicts
    escalations = sum(1 for r in results if r.should_escalate)
    conflicts = sum(len(r.conflicts_resolved) for r in results)
    
    # Create summary table
    summary_table = Table(title="Processing Results")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="magenta")
    summary_table.add_column("Percentage", style="yellow")
    
    total = len(results)
    summary_table.add_row("Critical Priority", str(critical_count), f"{critical_count/total:.1%}")
    summary_table.add_row("High Priority", str(high_count), f"{high_count/total:.1%}")
    summary_table.add_row("Medium Priority", str(medium_count), f"{medium_count/total:.1%}")
    summary_table.add_row("Low Priority", str(low_count), f"{low_count/total:.1%}")
    summary_table.add_row("", "", "")
    summary_table.add_row("High Confidence", str(high_confidence), f"{high_confidence/total:.1%}")
    summary_table.add_row("Medium Confidence", str(medium_confidence), f"{medium_confidence/total:.1%}")
    summary_table.add_row("Low Confidence", str(low_confidence), f"{low_confidence/total:.1%}")
    summary_table.add_row("", "", "")
    summary_table.add_row("Escalations", str(escalations), f"{escalations/total:.1%}")
    summary_table.add_row("Conflicts Resolved", str(conflicts), f"{conflicts/total:.1f} avg")
    
    console.print(summary_table)
    
    # Most common labels
    all_labels = []
    for result in results:
        all_labels.extend(result.agreed_labels)
    
    if all_labels:
        from collections import Counter
        label_counts = Counter(all_labels)
        
        console.print(f"\n[bold]🏷️  Most Applied Labels:[/bold]")
        for label, count in label_counts.most_common(10):
            console.print(f"  • {label}: {count} emails")
    
    # Show action summary
    action_mode = "would be taken" if dry_run else "taken"
    console.print(f"\n[bold green]✅ Collaborative decisions {action_mode} for {len(results)} emails[/bold green]")
    
    if escalations > 0:
        console.print(f"[bold red]🚨 {escalations} emails flagged for immediate escalation[/bold red]")
    
    if conflicts > 0:
        console.print(f"[yellow]⚖️  {conflicts} agent conflicts successfully resolved[/yellow]")