"""Main CLI interface for Email Agent."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..agents import EmailAgentCrew
from ..config import settings
from ..models import EmailCategory
from ..storage import DatabaseManager
from .commands import (
    brief,
    categories,
    ceo,
    config,
    drafts,
    inbox,
    init,
    pull,
    rules,
    status,
)

# Setup logging
logging.basicConfig(level=getattr(logging, settings.log_level.upper()))

# Create console for rich output
console = Console()

# Create main CLI app
app = typer.Typer(
    name="email-agent",
    help="CLI Email Agent for triaging and summarizing high-volume inboxes",
    add_completion=False,
    rich_markup_mode="rich",
)

# Add command groups
app.add_typer(init.app, name="init", help="Initialize and configure Email Agent")
app.add_typer(pull.app, name="pull", help="Pull and sync emails from connectors")
app.add_typer(brief.app, name="brief", help="Generate and view daily briefs")
app.add_typer(rules.app, name="rule", help="Manage categorization rules")
app.add_typer(categories.app, name="cat", help="View and manage email categories")
app.add_typer(config.app, name="config", help="Manage configuration and connectors")
app.add_typer(status.app, name="status", help="View system status and statistics")
app.add_typer(inbox.app, name="inbox", help="Smart inbox and AI triage management")
app.add_typer(
    drafts.app,
    name="drafts",
    help="AI-powered draft suggestions and writing style analysis",
)
app.add_typer(ceo.app, name="ceo", help="CEO-focused email management and labeling")


@app.command()
def version():
    """Show version information."""
    from .. import __version__

    console.print(f"Email Agent v{__version__}")
    raise typer.Exit(0)


@app.command()
def quick_start():
    """Quick start guide for new users."""
    console.print(
        Panel.fit(
            Text.from_markup(
                """
[bold cyan]Email Agent Quick Start[/bold cyan]

1. [bold]Initialize:[/bold] email-agent init
2. [bold]Add connector:[/bold] email-agent config add-connector gmail
3. [bold]Pull emails:[/bold] email-agent pull --since yesterday
4. [bold]View brief:[/bold] email-agent brief --today
5. [bold]Check status:[/bold] email-agent status

[dim]For detailed help on any command, use: email-agent [command] --help[/dim]
"""
            ),
            title="Quick Start",
            border_style="cyan",
        )
    )


@app.command()
def dashboard_legacy():
    """Launch interactive dashboard (TUI) - legacy version."""
    try:
        from ..tui import EmailAgentTUI

        tui = EmailAgentTUI()
        tui.run()
    except ImportError:
        console.print(
            "[red]Dashboard requires additional dependencies. Run: pip install email-agent[tui][/red]"
        )
    except Exception as e:
        console.print(f"[red]Failed to launch dashboard: {str(e)}[/red]")


@app.command()
def sync(
    since: Optional[str] = typer.Option(
        None,
        "--since",
        help="Sync emails since this time (e.g., '2023-01-01', 'yesterday', '1 hour ago')",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be synced without actually doing it"
    ),
    brief: bool = typer.Option(
        True, "--brief/--no-brief", help="Generate daily brief after sync"
    ),
):
    """Full sync: pull emails, categorize, and generate brief."""

    async def run_sync():
        try:
            # Initialize components
            db = DatabaseManager()
            crew = EmailAgentCrew()

            # Get connector configs
            connector_configs = db.get_connector_configs()
            if not connector_configs:
                console.print(
                    "[red]No connectors configured. Run 'email-agent config add-connector' first.[/red]"
                )
                return

            # Parse since parameter
            since_datetime = None
            if since:
                since_datetime = parse_time_string(since)
            else:
                since_datetime = datetime.now() - timedelta(hours=24)

            console.print(f"[cyan]Starting sync since {since_datetime}[/cyan]")

            if dry_run:
                console.print("[yellow]DRY RUN - No changes will be made[/yellow]")
                # Show what would be synced
                for config in connector_configs:
                    console.print(f"  Would sync from: {config.name} ({config.type})")
                return

            # Initialize crew
            await crew.initialize_crew({})

            # Get rules for categorization
            rules = db.get_rules()

            # Execute full processing
            with console.status("[bold green]Processing emails..."):
                results = await crew.execute_task(
                    "full_processing",
                    connector_configs=connector_configs,
                    rules=rules,
                    since=since_datetime,
                    generate_brief=brief,
                )

            # Display results
            console.print("\n[bold green]Sync completed![/bold green]")
            console.print(f"  Emails collected: {results['emails_collected']}")
            console.print(f"  Emails categorized: {results['emails_categorized']}")
            console.print(f"  Emails saved to database: {results['emails_saved']}")

            if results.get("brief_generated"):
                console.print("  Daily brief: Generated")

            if results.get("errors"):
                console.print(f"[red]  Errors: {len(results['errors'])}[/red]")
                for error in results["errors"]:
                    console.print(f"    {error}")

            await crew.shutdown()

        except Exception as e:
            console.print(f"[red]Sync failed: {str(e)}[/red]")

    asyncio.run(run_sync())


@app.command()
def stats():
    """Show email statistics."""
    try:
        db = DatabaseManager()
        stats = db.get_email_stats()

        if not stats:
            console.print("[yellow]No email statistics available[/yellow]")
            return

        # Create statistics table
        table = Table(title="Email Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="magenta")

        table.add_row("Total Emails", str(stats["total"]))
        table.add_row("Unread Emails", str(stats["unread"]))
        table.add_row("Flagged Emails", str(stats["flagged"]))

        console.print(table)

        # Category breakdown
        if stats["categories"]:
            cat_table = Table(title="Category Breakdown")
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Count", style="magenta")

            for category, count in stats["categories"].items():
                cat_table.add_row(category.title(), str(count))

            console.print(cat_table)

    except Exception as e:
        console.print(f"[red]Failed to get statistics: {str(e)}[/red]")


def parse_time_string(time_str: str) -> datetime:
    """Parse human-readable time strings."""
    time_str = time_str.lower().strip()

    if time_str in ["today", "now"]:
        return datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_str == "yesterday":
        return datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)
    elif time_str.endswith("ago"):
        # Parse "X hours ago", "X days ago", etc.
        parts = time_str.replace("ago", "").strip().split()
        if len(parts) == 2:
            try:
                amount = int(parts[0])
                unit = parts[1].rstrip("s")  # Remove plural 's'

                if unit in ["hour", "hr", "h"]:
                    return datetime.now() - timedelta(hours=amount)
                elif unit in ["day", "d"]:
                    return datetime.now() - timedelta(days=amount)
                elif unit in ["week", "w"]:
                    return datetime.now() - timedelta(weeks=amount)
                elif unit in ["minute", "min", "m"]:
                    return datetime.now() - timedelta(minutes=amount)
            except ValueError:
                pass
    else:
        # Try to parse as ISO date
        try:
            return datetime.fromisoformat(time_str)
        except ValueError:
            pass

    # Default fallback
    return datetime.now() - timedelta(days=1)


@app.command()
def smart_inbox(
    limit: int = typer.Option(50, help="Maximum number of emails to process"),
    days: int = typer.Option(7, help="Number of days to look back"),
    show_scores: bool = typer.Option(False, "--scores", help="Show attention scores"),
):
    """Create smart inbox with AI-powered triage."""
    from .commands.inbox import _smart_inbox

    asyncio.run(_smart_inbox(limit, days, show_scores, True))


@app.command()
def priority_inbox(
    limit: int = typer.Option(20, help="Maximum number of priority emails to show"),
    min_score: float = typer.Option(0.7, help="Minimum attention score for priority"),
):
    """Show priority inbox - emails that need immediate attention."""
    from .commands.inbox import _priority_inbox

    asyncio.run(_priority_inbox(limit, min_score))


@app.command()
def triage_stats():
    """Show triage statistics and performance metrics."""
    from .commands.inbox import _triage_stats

    asyncio.run(_triage_stats())


@app.command()
def dashboard():
    """Launch the interactive TUI dashboard."""
    from ..tui.app import EmailAgentTUI

    try:
        app = EmailAgentTUI()
        app.run()
    except Exception as e:
        console.print(f"[red]Failed to launch dashboard: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command()
def auto_handle(
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show detailed processing information"
    ),
):
    """Intelligently handle emails using AI to prioritize, categorize, and archive."""

    async def run_auto_handler():
        from ..agents import EmailAgentCrew
        from ..models import Email, EmailAddress, EmailPriority

        db = DatabaseManager()
        crew = EmailAgentCrew()

        console.print("[bold cyan]🤖 AI Email Handler Starting...[/bold cyan]")

        # Initialize crew
        await crew.initialize_crew({})

        # Get unhandled emails
        with db.get_session() as session:
            from ..storage.models import EmailORM

            unread_emails = session.query(EmailORM).filter(not EmailORM.is_read).all()

            console.print(
                f"Found [yellow]{len(unread_emails)}[/yellow] unread emails to process"
            )

            if not unread_emails:
                console.print(
                    "[green]✅ All caught up! No emails need handling.[/green]"
                )
                return

            # Convert to models
            emails = []
            for e in unread_emails:
                email = Email(
                    id=e.id,
                    message_id=e.message_id,
                    thread_id=e.thread_id,
                    subject=e.subject,
                    sender=EmailAddress(email=e.sender_email, name=e.sender_name),
                    recipients=[],
                    date=e.date,
                    received_date=e.received_date,
                    body=e.body_text or "",
                    is_read=e.is_read,
                    is_flagged=e.is_flagged,
                    category=EmailCategory(e.category),
                    priority=EmailPriority(e.priority),
                    tags=e.tags or [],
                )
                emails.append(email)

        # Run AI triage
        console.print("\n[cyan]Running AI analysis...[/cyan]")
        triage_results = await crew.execute_task("triage_emails", emails=emails)

        # Show results
        priority_count = len(triage_results.get("priority_inbox", []))
        archive_count = len(triage_results.get("auto_archive", []))

        console.print("\n📊 [bold]AI Analysis Complete:[/bold]")
        console.print(f"  🔴 Priority/Urgent: [red]{priority_count}[/red] emails")
        console.print(f"  📦 Auto-archive: [green]{archive_count}[/green] emails")
        console.print(
            f"  📨 Regular inbox: {len(triage_results.get('regular_inbox', []))} emails"
        )

        if dry_run:
            console.print("\n[yellow]DRY RUN - No changes will be made[/yellow]")

            if priority_count > 0:
                console.print("\n[red]Would mark as URGENT:[/red]")
                for email in triage_results.get("priority_inbox", [])[:5]:
                    console.print(f"  • {email.get('subject', 'No subject')[:60]}...")

            if archive_count > 0:
                console.print("\n[green]Would auto-archive:[/green]")
                for email in triage_results.get("auto_archive", [])[:5]:
                    console.print(f"  • {email.get('subject', 'No subject')[:60]}...")
        else:
            # Apply changes
            with db.get_session() as session:
                changes_made = 0

                # Mark priority emails
                for email_data in triage_results.get("priority_inbox", []):
                    email_orm = (
                        session.query(EmailORM).filter_by(id=email_data["id"]).first()
                    )
                    if email_orm:
                        email_orm.priority = "urgent"
                        email_orm.is_flagged = True
                        changes_made += 1
                        if verbose:
                            console.print(f"  🔴 Flagged: {email_orm.subject[:50]}...")

                # Auto-archive low priority
                for email_data in triage_results.get("auto_archive", []):
                    email_orm = (
                        session.query(EmailORM).filter_by(id=email_data["id"]).first()
                    )
                    if email_orm:
                        email_orm.is_read = True
                        email_orm.tags = json.dumps(["auto_archived"])
                        changes_made += 1
                        if verbose:
                            console.print(f"  ✅ Archived: {email_orm.subject[:50]}...")

                session.commit()
                console.print(f"\n[green]✅ Applied {changes_made} changes[/green]")

        await crew.shutdown()
        console.print("\n[bold green]✨ Email handling complete![/bold green]")

    asyncio.run(run_auto_handler())


@app.command()
def smart_actions(
    limit: int = typer.Option(20, help="Maximum number of emails to process"),
    apply_labels: bool = typer.Option(
        True, "--apply-labels/--no-labels", help="Apply Gmail labels based on actions"
    ),
    generate_replies: bool = typer.Option(
        False, "--replies", help="Generate smart reply suggestions"
    ),
    create_events: bool = typer.Option(
        False, "--events", help="Create calendar events for meetings"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be done without making changes"
    ),
    skip_processed: bool = typer.Option(
        True, "--skip-processed/--all", help="Skip already processed emails"
    ),
    show_all: bool = typer.Option(
        False, "--show-all", help="Show all emails even if no actions found"
    ),
):
    """Extract actions from emails and leverage Gmail SDK features."""

    async def run_smart_actions():
        from ..agents.action_extractor import ActionExtractorAgent
        from ..connectors.gmail_service import GmailService
        from ..models import Email, EmailAddress, EmailPriority

        db = DatabaseManager()
        action_extractor = ActionExtractorAgent()

        console.print("[bold cyan]🔍 Smart Action Extraction Starting...[/bold cyan]")

        # Get recent unprocessed emails
        with db.get_session() as session:
            from ..storage.models import EmailORM

            recent_emails = (
                session.query(EmailORM)
                .filter(~EmailORM.tags.like("%action_processed%"))
                .order_by(EmailORM.received_date.desc())
                .limit(limit)
                .all()
            )

            console.print(
                f"Found [yellow]{len(recent_emails)}[/yellow] emails to analyze for actions"
            )

            if not recent_emails:
                console.print("[green]✅ No new emails to process for actions.[/green]")
                return

            # Convert to models
            emails = []
            for e in recent_emails:
                email = Email(
                    id=e.id,
                    message_id=e.message_id,
                    thread_id=e.thread_id,
                    subject=e.subject,
                    sender=EmailAddress(email=e.sender_email, name=e.sender_name),
                    recipients=[],
                    date=e.date,
                    received_date=e.received_date,
                    body=e.body_text or "",
                    is_read=e.is_read,
                    is_flagged=e.is_flagged,
                    category=(
                        EmailCategory(e.category)
                        if e.category
                        else EmailCategory.PERSONAL
                    ),
                    priority=(
                        EmailPriority(e.priority)
                        if e.priority
                        else EmailPriority.NORMAL
                    ),
                    tags=e.tags or [],
                )
                emails.append(email)

        # Extract actions from emails
        console.print("\n[cyan]Extracting actions from emails...[/cyan]")
        actions_results = await action_extractor.extract_batch_actions(emails)

        # Initialize Gmail service if credentials available
        gmail_service = None
        try:
            # Check for Gmail credentials
            import os

            if os.path.exists("credentials.json"):
                with open("credentials.json", "r") as f:
                    creds = json.load(f)
                gmail_service = GmailService(creds)
                if await gmail_service.authenticate():
                    console.print("[green]✅ Gmail service authenticated[/green]")
                    if apply_labels:
                        await gmail_service.create_action_labels()
                else:
                    gmail_service = None
        except Exception as e:
            console.print(f"[yellow]⚠️  Gmail service unavailable: {e}[/yellow]")

        # Process results
        total_actions = 0
        total_commitments = 0
        total_meetings = 0
        total_deadlines = 0

        for i, (email, actions) in enumerate(zip(emails, actions_results)):
            if "error" in actions:
                console.print(
                    f"[red]❌ Error processing {email.subject[:40]}...: {actions['error']}[/red]"
                )
                continue

            # Count actions
            actions_count = len(actions.get("action_items", []))
            commitments_count = len(actions.get("commitments_made", []))
            meetings_count = len(actions.get("meeting_requests", []))
            deadlines_count = sum(
                1 for item in actions.get("action_items", []) if item.get("deadline")
            )

            total_actions += actions_count
            total_commitments += commitments_count
            total_meetings += meetings_count
            total_deadlines += deadlines_count

            if actions_count > 0 or commitments_count > 0 or meetings_count > 0:
                console.print(f"\n📧 [bold]{email.subject[:50]}...[/bold]")
                console.print(f"   From: {email.sender.email}")

                if actions.get("needs_response"):
                    urgency = actions.get("response_urgency", "normal")
                    urgency_color = (
                        "red"
                        if urgency == "urgent"
                        else "yellow" if urgency == "normal" else "green"
                    )
                    console.print(
                        f"   📢 Needs response: [{urgency_color}]{urgency}[/{urgency_color}]"
                    )

                if actions_count > 0:
                    console.print(f"   📋 Actions: {actions_count}")
                    for action in actions.get("action_items", [])[:2]:
                        deadline_str = (
                            f" (Due: {action['deadline']})"
                            if action.get("deadline")
                            else ""
                        )
                        console.print(
                            f"     • {action['action'][:60]}...{deadline_str}"
                        )

                if commitments_count > 0:
                    console.print(f"   🤝 Commitments: {commitments_count}")
                    for commitment in actions.get("commitments_made", [])[:2]:
                        console.print(f"     • {commitment['commitment'][:60]}...")

                if meetings_count > 0:
                    console.print(f"   📅 Meetings: {meetings_count}")
                    for meeting in actions.get("meeting_requests", [])[:1]:
                        console.print(f"     • {meeting['type']} meeting")

                # Apply Gmail features if available and not dry run
                if gmail_service and not dry_run:
                    try:
                        if apply_labels:
                            await gmail_service.apply_action_labels(
                                email.message_id, actions
                            )
                            console.print("     🏷️  Gmail labels applied")

                        if generate_replies and actions.get("needs_response"):
                            reply = await gmail_service.generate_smart_reply(
                                email, actions
                            )
                            if reply:
                                console.print(
                                    f"     💬 Smart reply generated ({len(reply)} chars)"
                                )

                        if create_events and actions.get("meeting_requests"):
                            for meeting in actions.get("meeting_requests", []):
                                event_id = await gmail_service.create_calendar_event(
                                    meeting, email
                                )
                                if event_id:
                                    console.print("     📅 Calendar event created")

                    except Exception as e:
                        console.print(f"     [red]❌ Gmail feature error: {e}[/red]")

                # Mark as processed in database
                if not dry_run:
                    with db.get_session() as session:
                        email_orm = (
                            session.query(EmailORM).filter_by(id=email.id).first()
                        )
                        if email_orm:
                            current_tags = email_orm.tags or []
                            if isinstance(current_tags, str):
                                current_tags = json.loads(current_tags)
                            current_tags.append("action_processed")
                            email_orm.tags = json.dumps(current_tags)
                            session.commit()

        # Show summary
        console.print("\n📊 [bold]Action Extraction Summary:[/bold]")
        console.print(f"  📋 Total action items: [cyan]{total_actions}[/cyan]")
        console.print(f"  🤝 Total commitments: [cyan]{total_commitments}[/cyan]")
        console.print(f"  📅 Meeting requests: [cyan]{total_meetings}[/cyan]")
        console.print(f"  ⏰ Items with deadlines: [cyan]{total_deadlines}[/cyan]")

        if dry_run:
            console.print("\n[yellow]DRY RUN - No changes were made[/yellow]")
        else:
            console.print(
                f"\n[green]✅ Processed {len(emails)} emails for actions[/green]"
            )

        # Generate action summary
        summary = await action_extractor.generate_action_summary(actions_results)

        if summary["deadlines_today"] > 0:
            console.print(
                f"\n[red]⚠️  {summary['deadlines_today']} items due TODAY![/red]"
            )

        if summary["deadlines_this_week"] > 0:
            console.print(
                f"[yellow]📅 {summary['deadlines_this_week']} items due this week[/yellow]"
            )

    asyncio.run(run_smart_actions())


@app.command()
def thread_summary(
    thread_id: Optional[str] = typer.Option(
        None, help="Specific thread ID to summarize"
    ),
    limit: int = typer.Option(10, help="Maximum number of threads to summarize"),
    days: int = typer.Option(7, help="Number of days to look back for threads"),
    insights: bool = typer.Option(
        False, "--insights", help="Generate deeper insights for threads"
    ),
    overview: bool = typer.Option(
        False, "--overview", help="Generate overview of all thread summaries"
    ),
):
    """Summarize email threads with AI-powered insights."""

    async def run_thread_summary(
        thread_id=thread_id,
        limit=limit,
        days=days,
        insights=insights,
        overview=overview,
    ):
        from ..agents.thread_summarizer import ThreadSummarizerAgent
        from ..models import Email, EmailAddress, EmailPriority

        db = DatabaseManager()
        summarizer = ThreadSummarizerAgent()

        console.print("[bold cyan]🧵 Thread Summarization Starting...[/bold cyan]")

        # Get threads from database
        with db.get_session() as session:
            from ..storage.models import EmailORM

            if thread_id:
                # Summarize specific thread
                thread_emails = (
                    session.query(EmailORM)
                    .filter(EmailORM.thread_id == thread_id)
                    .order_by(EmailORM.date)
                    .all()
                )

                if not thread_emails:
                    console.print(
                        f"[red]❌ No emails found for thread ID: {thread_id}[/red]"
                    )
                    return

                thread_groups = [thread_emails]
                console.print(
                    f"Found thread with [yellow]{len(thread_emails)}[/yellow] emails"
                )

            else:
                # Get recent threads
                cutoff_date = datetime.now() - timedelta(days=days)
                recent_emails = (
                    session.query(EmailORM)
                    .filter(
                        EmailORM.received_date >= cutoff_date,
                        EmailORM.thread_id.isnot(None),
                    )
                    .order_by(EmailORM.received_date.desc())
                    .all()
                )

                # Group by thread_id
                thread_groups_dict = {}
                for email in recent_emails:
                    if email.thread_id not in thread_groups_dict:
                        thread_groups_dict[email.thread_id] = []
                    thread_groups_dict[email.thread_id].append(email)

                # Filter threads with multiple emails and sort by latest activity
                thread_groups = []
                for thread_id, emails in thread_groups_dict.items():
                    if len(emails) > 1:  # Only multi-email threads
                        emails.sort(key=lambda e: e.date)
                        thread_groups.append(emails)

                # Sort by latest activity and limit
                thread_groups.sort(
                    key=lambda emails: max(e.received_date for e in emails),
                    reverse=True,
                )
                thread_groups = thread_groups[:limit]

                console.print(
                    f"Found [yellow]{len(thread_groups)}[/yellow] multi-email threads to summarize"
                )

                if not thread_groups:
                    console.print(
                        "[green]✅ No multi-email threads found to summarize.[/green]"
                    )
                    return

            # Convert to Email models
            email_thread_groups = []
            for thread_emails in thread_groups:
                emails = []
                for e in thread_emails:
                    email = Email(
                        id=e.id,
                        message_id=e.message_id,
                        thread_id=e.thread_id,
                        subject=e.subject,
                        sender=EmailAddress(email=e.sender_email, name=e.sender_name),
                        recipients=[],
                        date=e.date,
                        received_date=e.received_date,
                        body=e.body_text or "",
                        is_read=e.is_read,
                        is_flagged=e.is_flagged,
                        category=(
                            EmailCategory(e.category)
                            if e.category
                            else EmailCategory.PERSONAL
                        ),
                        priority=(
                            EmailPriority(e.priority)
                            if e.priority
                            else EmailPriority.NORMAL
                        ),
                        tags=e.tags or [],
                    )
                    emails.append(email)
                email_thread_groups.append(emails)

        # Summarize threads
        console.print("\n[cyan]Summarizing threads...[/cyan]")
        summaries = await summarizer.summarize_multiple_threads(email_thread_groups)

        # Display results
        for i, (emails, summary) in enumerate(zip(email_thread_groups, summaries)):
            if "error" in summary:
                console.print(
                    f"[red]❌ Error summarizing thread {i+1}: {summary['error']}[/red]"
                )
                continue

            console.print(
                f"\n🧵 [bold]Thread {i+1}:[/bold] {emails[0].subject[:60]}..."
            )
            console.print(f"   📧 Emails: {summary['email_count']}")
            console.print(
                f"   📅 Date Range: {summary['date_range']['start'][:10]} to {summary['date_range']['end'][:10]}"
            )
            console.print(f"   📊 Status: {summary.get('thread_status', 'unknown')}")
            console.print(f"   🔥 Priority: {summary.get('priority_level', 'unknown')}")
            console.print(f"   😊 Sentiment: {summary.get('sentiment', 'unknown')}")

            console.print("\n   📝 [bold]Summary:[/bold]")
            console.print(f"   {summary.get('thread_summary', 'No summary available')}")

            if summary.get("action_items"):
                console.print(
                    f"\n   📋 [bold]Action Items ({len(summary['action_items'])}):[/bold]"
                )
                for action in summary["action_items"][:3]:
                    deadline_str = (
                        f" (Due: {action.get('deadline', 'No deadline')})"
                        if action.get("deadline")
                        else ""
                    )
                    owner_str = (
                        f" [{action.get('owner', 'Unassigned')}]"
                        if action.get("owner")
                        else ""
                    )
                    console.print(
                        f"     • {action.get('action', 'No action')}{owner_str}{deadline_str}"
                    )

            if summary.get("key_decisions"):
                console.print("\n   💡 [bold]Key Decisions:[/bold]")
                for decision in summary["key_decisions"][:2]:
                    console.print(f"     • {decision}")

            if summary.get("next_steps"):
                console.print("\n   ➡️  [bold]Next Steps:[/bold]")
                for step in summary["next_steps"][:2]:
                    console.print(f"     • {step}")

            if summary.get("requires_attention"):
                console.print("   [red]⚠️  Requires Attention![/red]")

            # Generate insights if requested
            if insights:
                console.print("\n   [cyan]Generating insights...[/cyan]")
                thread_insights = await summarizer.get_thread_insights(summary)

                if "error" not in thread_insights:
                    if thread_insights.get("escalation_needed"):
                        console.print("   [red]🚨 Escalation recommended![/red]")

                    console.print(
                        f"   📈 Efficiency Score: {thread_insights.get('efficiency_score', 'N/A')}/10"
                    )
                    console.print(
                        f"   🤝 Collaboration Score: {thread_insights.get('collaboration_score', 'N/A')}/10"
                    )

                    if thread_insights.get("recommendations"):
                        console.print("   💭 [bold]Recommendations:[/bold]")
                        for rec in thread_insights["recommendations"][:2]:
                            console.print(f"     • {rec}")

        # Generate overview if requested
        if overview and len(summaries) > 1:
            console.print("\n[cyan]Generating threads overview...[/cyan]")
            threads_overview = await summarizer.generate_threads_overview(summaries)

            if "error" not in threads_overview:
                console.print("\n📊 [bold]Threads Overview:[/bold]")
                stats = threads_overview["summary_stats"]
                console.print(
                    f"  📧 Total threads: {threads_overview['total_threads']}"
                )
                console.print(f"  🔴 Urgent: {stats['urgent_threads']}")
                console.print(f"  ⏳ Unresolved: {stats['unresolved_threads']}")
                console.print(f"  ⚠️  Need attention: {stats['requires_attention']}")
                console.print(f"  📋 Total actions: {stats['total_action_items']}")
                console.print(f"  ⏰ Overdue actions: {stats['overdue_actions']}")

                if threads_overview.get("thread_types"):
                    console.print("\n📈 [bold]Thread Types:[/bold]")
                    for t_type, count in threads_overview["thread_types"].items():
                        console.print(f"  {t_type}: {count}")

                if threads_overview.get("recommendations"):
                    console.print("\n💡 [bold]Recommendations:[/bold]")
                    for rec in threads_overview["recommendations"][:3]:
                        console.print(f"  • {rec}")

        console.print(
            f"\n[green]✅ Summarized {len([s for s in summaries if 'error' not in s])} threads successfully[/green]"
        )

    asyncio.run(run_thread_summary())


@app.command()
def feedback(
    email_id: str = typer.Argument(help="Email ID to provide feedback on"),
    agent_type: str = typer.Option(
        "categorizer", help="Agent type (categorizer, prioritizer, action_extractor)"
    ),
    decision_type: str = typer.Option(
        "category", help="Decision type (category, priority, actions)"
    ),
    feedback_text: str = typer.Option(
        "", "--feedback", help="Your feedback on the AI decision"
    ),
    correct_decision: str = typer.Option(
        "", "--correct", help="What the correct decision should have been"
    ),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactive feedback mode"
    ),
):
    """Provide feedback on AI decisions to improve the system."""

    async def run_feedback():
        import json

        from ..agents.learning_system import LearningFeedbackSystem
        from ..storage.models import EmailORM

        db = DatabaseManager()
        learning_system = LearningFeedbackSystem()

        console.print("[bold cyan]📚 Learning Feedback System[/bold cyan]")

        # Get email details
        with db.get_session() as session:
            email_orm = session.query(EmailORM).filter_by(id=email_id).first()

            if not email_orm:
                console.print(f"[red]❌ Email not found: {email_id}[/red]")
                return

            console.print(f"\n📧 [bold]Email:[/bold] {email_orm.subject[:60]}...")
            console.print(f"   From: {email_orm.sender_email}")
            console.print(f"   Date: {email_orm.date}")
            console.print(f"   Current category: {email_orm.category}")
            console.print(f"   Current priority: {email_orm.priority}")

        if interactive:
            # Interactive feedback mode
            console.print("\n[cyan]Interactive Feedback Mode[/cyan]")

            # Use variables from outer scope
            nonlocal agent_type, decision_type
            agent_type = typer.prompt("Agent type", default=agent_type)
            decision_type = typer.prompt("Decision type", default=decision_type)

            console.print(f"\nWhat was wrong with the AI's {decision_type} decision?")
            feedback_text = typer.prompt("Your feedback")

            if typer.confirm("Do you want to specify the correct decision?"):
                correct_decision = typer.prompt("Correct decision")

            confidence = typer.prompt(
                "How confident are you in this feedback? (0.0-1.0)",
                default="0.8",
                type=float,
            )
        else:
            confidence = 0.8
            if not feedback_text:
                console.print("[red]❌ Feedback text is required[/red]")
                return

        # Prepare context
        context_data = {
            "email_subject": email_orm.subject,
            "sender_email": email_orm.sender_email,
            "sender_name": email_orm.sender_name,
            "email_category": email_orm.category,
            "email_priority": email_orm.priority,
            "email_body_length": len(email_orm.body_text or ""),
            "tags": json.loads(email_orm.tags) if email_orm.tags else [],
        }

        # Record feedback
        success = await learning_system.record_feedback(
            email_id=email_id,
            agent_type=agent_type,
            decision_type=decision_type,
            original_decision=getattr(email_orm, decision_type, "unknown"),
            user_feedback=feedback_text,
            correct_decision=correct_decision or None,
            confidence_score=confidence,
            context_data=context_data,
        )

        if success:
            console.print("\n[green]✅ Feedback recorded successfully![/green]")
            console.print(
                "The system will learn from this feedback to make better decisions."
            )
        else:
            console.print("\n[red]❌ Failed to record feedback[/red]")

    asyncio.run(run_feedback())


@app.command()
def learning_stats():
    """Show learning system statistics and effectiveness."""

    async def run_learning_stats():
        from ..agents.learning_system import LearningFeedbackSystem

        learning_system = LearningFeedbackSystem()

        console.print("[bold cyan]📊 Learning System Statistics[/bold cyan]")

        stats = await learning_system.get_learning_stats()

        if "error" in stats:
            console.print(f"[red]❌ Error getting stats: {stats['error']}[/red]")
            return

        # Overview
        console.print("\n📈 [bold]Overview:[/bold]")
        console.print(f"  Total feedback records: {stats['total_feedback_records']}")
        console.print(f"  Learned patterns: {stats['total_learned_patterns']}")
        console.print(f"  User preferences: {stats['total_user_preferences']}")
        console.print(f"  Recent feedback (7 days): {stats['recent_feedback_7days']}")

        # Learning effectiveness
        effectiveness = stats.get("learning_effectiveness", 0) * 100
        effectiveness_color = (
            "green" if effectiveness > 70 else "yellow" if effectiveness > 50 else "red"
        )
        console.print(
            f"  Learning effectiveness: [{effectiveness_color}]{effectiveness:.1f}%[/{effectiveness_color}]"
        )

        # Feedback by agent
        if stats["feedback_by_agent"]:
            console.print("\n🤖 [bold]Feedback by Agent:[/bold]")
            for agent, count in stats["feedback_by_agent"].items():
                console.print(f"  {agent}: {count} feedback records")

        # Pattern stats
        if stats["pattern_stats"]:
            console.print("\n🎯 [bold]Learning Patterns:[/bold]")
            for pattern_type, pattern_info in stats["pattern_stats"].items():
                success_rate = pattern_info["avg_success_rate"] * 100
                color = (
                    "green"
                    if success_rate > 70
                    else "yellow" if success_rate > 50 else "red"
                )
                console.print(
                    f"  {pattern_type}: {pattern_info['count']} patterns, [{color}]{success_rate:.1f}% success[/{color}]"
                )

        console.print(
            f"\n[dim]Stats generated: {stats['stats_generated_at'][:19]}[/dim]"
        )

    asyncio.run(run_learning_stats())


@app.command()
def export_learning(
    output_file: str = typer.Option("learning_data.json", help="Output file path")
):
    """Export learning data for analysis or backup."""

    async def run_export():
        from ..agents.learning_system import LearningFeedbackSystem

        learning_system = LearningFeedbackSystem()

        console.print(f"[cyan]Exporting learning data to {output_file}...[/cyan]")

        success = await learning_system.export_learning_data(output_file)

        if success:
            console.print(
                f"[green]✅ Learning data exported successfully to {output_file}[/green]"
            )
        else:
            console.print("[red]❌ Failed to export learning data[/red]")

    asyncio.run(run_export())


@app.command()
def commitments(
    show_overdue: bool = typer.Option(
        False, "--overdue", help="Show only overdue items"
    ),
    days_ahead: int = typer.Option(
        30, help="Number of days ahead to look for commitments"
    ),
    report: bool = typer.Option(
        False, "--report", help="Generate comprehensive commitment report"
    ),
):
    """View and manage commitments and waiting items."""

    async def run_commitments():
        from ..agents.commitment_tracker import CommitmentTrackerAgent

        tracker = CommitmentTrackerAgent()

        console.print("[bold cyan]📅 Commitment Tracker[/bold cyan]")

        if report:
            # Generate comprehensive report
            console.print("\n[cyan]Generating commitment report...[/cyan]")

            report_data = await tracker.generate_commitment_report(
                days_ahead=days_ahead
            )

            if "error" in report_data:
                console.print(
                    f"[red]❌ Error generating report: {report_data['error']}[/red]"
                )
                return

            # Display summary
            summary = report_data["summary"]
            console.print("\n📊 [bold]Summary:[/bold]")
            console.print(
                f"  Pending commitments: [cyan]{summary['total_pending_commitments']}[/cyan]"
            )
            console.print(
                f"  Urgent (≤3 days): [red]{summary['urgent_commitments']}[/red]"
            )
            console.print(
                f"  Overdue commitments: [red]{summary['overdue_commitments']}[/red]"
            )
            console.print(
                f"  Overdue waiting items: [yellow]{summary['overdue_waiting_items']}[/yellow]"
            )
            console.print(f"  Due today: [red]{summary['due_today']}[/red]")
            console.print(
                f"  Due this week: [yellow]{summary['due_this_week']}[/yellow]"
            )

            # AI Insights
            if report_data.get("ai_insights"):
                insights = report_data["ai_insights"]
                workload_color = {
                    "light": "green",
                    "moderate": "yellow",
                    "heavy": "orange",
                    "overwhelming": "red",
                }.get(insights.get("workload_assessment", "moderate"), "yellow")

                console.print("\n🧠 [bold]AI Insights:[/bold]")
                console.print(
                    f"  Workload: [{workload_color}]{insights.get('workload_assessment', 'moderate')}[/{workload_color}]"
                )
                console.print(
                    f"  Time management score: {insights.get('time_management_score', 'N/A')}/10"
                )

                if insights.get("priority_recommendations"):
                    console.print("\n💡 [bold]Priority Recommendations:[/bold]")
                    for rec in insights["priority_recommendations"][:3]:
                        console.print(f"  • {rec}")

            # Due today
            if report_data["timeframe_breakdown"]["due_today"]:
                console.print("\n🔴 [bold]Due Today:[/bold]")
                for item in report_data["timeframe_breakdown"]["due_today"]:
                    console.print(f"  • {item['description'][:70]}...")
                    console.print(f"    To: {item.get('committed_to', 'Unknown')}")

            # Due this week
            if report_data["timeframe_breakdown"]["due_this_week"]:
                console.print("\n🟡 [bold]Due This Week:[/bold]")
                for item in report_data["timeframe_breakdown"]["due_this_week"][:5]:
                    days_str = (
                        f"({item['days_remaining']} days)"
                        if item["days_remaining"]
                        else ""
                    )
                    console.print(f"  • {item['description'][:70]}... {days_str}")

            # Overdue items
            overdue_items = report_data["overdue_items"]
            if overdue_items["overdue_commitments"]:
                console.print("\n❌ [bold]Overdue Commitments:[/bold]")
                for item in overdue_items["overdue_commitments"][:5]:
                    console.print(
                        f"  • {item['description'][:60]}... ({item['days_overdue']} days overdue)"
                    )
                    console.print(f"    To: {item.get('committed_to', 'Unknown')}")

            if overdue_items["overdue_waiting"]:
                console.print("\n⏰ [bold]Overdue Waiting Items:[/bold]")
                for item in overdue_items["overdue_waiting"][:5]:
                    console.print(
                        f"  • {item['description'][:60]}... ({item['days_overdue']} days overdue)"
                    )
                    console.print(f"    From: {item.get('waiting_from', 'Unknown')}")

        elif show_overdue:
            # Show only overdue items
            overdue_items = await tracker.get_overdue_items()

            if (
                not overdue_items["overdue_commitments"]
                and not overdue_items["overdue_waiting"]
            ):
                console.print(
                    "[green]✅ No overdue items! You're all caught up.[/green]"
                )
                return

            if overdue_items["overdue_commitments"]:
                console.print(
                    f"\n❌ [bold]Overdue Commitments ({len(overdue_items['overdue_commitments'])}):[/bold]"
                )
                for item in overdue_items["overdue_commitments"]:
                    console.print(f"  • {item['description'][:70]}...")
                    console.print(
                        f"    To: {item.get('committed_to', 'Unknown')} | {item['days_overdue']} days overdue"
                    )

            if overdue_items["overdue_waiting"]:
                console.print(
                    f"\n⏰ [bold]Overdue Waiting Items ({len(overdue_items['overdue_waiting'])}):[/bold]"
                )
                for item in overdue_items["overdue_waiting"]:
                    console.print(f"  • {item['description'][:70]}...")
                    console.print(
                        f"    From: {item.get('waiting_from', 'Unknown')} | {item['days_overdue']} days overdue"
                    )

        else:
            # Show pending commitments
            pending = await tracker.get_pending_commitments(days_ahead=days_ahead)

            if not pending:
                console.print("[green]✅ No pending commitments found.[/green]")
                return

            console.print(f"\n📋 [bold]Pending Commitments ({len(pending)}):[/bold]")

            for commitment in pending[:15]:  # Limit display
                desc = (
                    commitment["description"][:70] + "..."
                    if len(commitment["description"]) > 70
                    else commitment["description"]
                )

                # Color code by urgency
                days_remaining = commitment.get("days_remaining")
                if days_remaining is not None:
                    if days_remaining <= 0:
                        urgency_color = "red"
                        urgency_text = "OVERDUE"
                    elif days_remaining <= 3:
                        urgency_color = "red"
                        urgency_text = f"{days_remaining} days"
                    elif days_remaining <= 7:
                        urgency_color = "yellow"
                        urgency_text = f"{days_remaining} days"
                    else:
                        urgency_color = "green"
                        urgency_text = f"{days_remaining} days"
                else:
                    urgency_color = "dim"
                    urgency_text = "No deadline"

                console.print(f"  • {desc}")
                console.print(
                    f"    To: {commitment.get('committed_to', 'Unknown')} | [{urgency_color}]{urgency_text}[/{urgency_color}] | {commitment['status']}"
                )

        # Show statistics
        stats = await tracker.get_commitment_stats()
        if "error" not in stats:
            console.print("\n📈 [bold]Statistics:[/bold]")
            console.print(
                f"  Total tracked: {stats['total_commitments']} commitments, {stats['total_waiting_items']} waiting items"
            )
            console.print(f"  Completion rate: {stats['completion_rate']:.1f}%")
            console.print(
                f"  Recent activity: {stats['recent_commitments_7days']} new commitments (7 days)"
            )

    asyncio.run(run_commitments())


@app.command()
def mark_complete(
    commitment_id: int = typer.Argument(help="Commitment ID to mark as complete"),
    notes: str = typer.Option("", help="Optional completion notes"),
):
    """Mark a commitment as completed."""

    async def run_mark_complete():
        from ..agents.commitment_tracker import CommitmentTrackerAgent

        tracker = CommitmentTrackerAgent()

        console.print(
            f"[cyan]Marking commitment {commitment_id} as completed...[/cyan]"
        )

        success = await tracker.update_commitment_status(
            commitment_id=commitment_id, status="completed", notes=notes or None
        )

        if success:
            console.print(
                f"[green]✅ Commitment {commitment_id} marked as completed![/green]"
            )
            if notes:
                console.print(f"   Notes: {notes}")
        else:
            console.print(f"[red]❌ Failed to update commitment {commitment_id}[/red]")

    asyncio.run(run_mark_complete())


def run_tui():
    """Run the TUI application (for testing)."""
    from ..tui.app import EmailAgentTUI

    app = EmailAgentTUI()
    app.run()


if __name__ == "__main__":
    app()
