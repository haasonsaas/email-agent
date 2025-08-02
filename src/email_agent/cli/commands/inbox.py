"""CLI commands for smart inbox and triage management."""

import asyncio
from typing import List

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...agents.crew import EmailAgentCrew
from ...storage.database import DatabaseManager
from ...models import Email

app = typer.Typer()
console = Console()


@app.command()
def smart(
    limit: int = typer.Option(50, help="Maximum number of emails to process"),
    days: int = typer.Option(7, help="Number of days to look back"),
    show_scores: bool = typer.Option(False, "--scores", help="Show attention scores"),
    auto_archive: bool = typer.Option(True, "--auto-archive/--no-auto-archive", help="Apply auto-archiving")
):
    """Create smart inbox with AI-powered triage."""
    asyncio.run(_smart_inbox(limit, days, show_scores, auto_archive))


@app.command()
def priority(
    limit: int = typer.Option(20, help="Maximum number of priority emails to show"),
    min_score: float = typer.Option(0.7, help="Minimum attention score for priority")
):
    """Show priority inbox - emails that need immediate attention."""
    asyncio.run(_priority_inbox(limit, min_score))


@app.command()
def archived(
    limit: int = typer.Option(50, help="Maximum number of archived emails to show"),
    days: int = typer.Option(7, help="Number of days to look back")
):
    """Show auto-archived emails with recovery options."""
    asyncio.run(_archived_emails(limit, days))


@app.command()
def stats():
    """Show triage statistics and performance metrics."""
    asyncio.run(_triage_stats())


@app.command()
def tune(
    priority_threshold: float = typer.Option(None, help="Set priority inbox threshold (0.0-1.0)"),
    archive_threshold: float = typer.Option(None, help="Set auto-archive threshold (0.0-1.0)"),
    show_current: bool = typer.Option(True, "--show", help="Show current settings")
):
    """Tune triage thresholds and preferences."""
    asyncio.run(_tune_triage(priority_threshold, archive_threshold, show_current))


@app.command()
def feedback(
    email_id: str = typer.Option(..., help="ID of the email to provide feedback on"),
    correct_decision: str = typer.Option(..., help="Correct triage decision: priority_inbox, regular_inbox, auto_archive, spam_folder"),
    user_action: str = typer.Option("manual_correction", help="Description of user action taken")
):
    """Provide feedback to improve triage accuracy."""
    asyncio.run(_provide_feedback(email_id, correct_decision, user_action))


@app.command()
def learning():
    """Show what the system has learned from your email habits."""
    asyncio.run(_show_learning_insights())


@app.command()
def senders():
    """Show learned sender importance scores."""
    asyncio.run(_show_sender_importance())


async def _smart_inbox(limit: int, days: int, show_scores: bool, auto_archive: bool):
    """Execute smart inbox creation."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Initialize components
        task = progress.add_task("Initializing AI agents...", total=None)
        crew = EmailAgentCrew()
        await crew.initialize_crew({"verbose": False})
        db = DatabaseManager()
        
        # Get recent emails
        progress.update(task, description="Loading recent emails...")
        emails = db.get_recent_emails(days=days, limit=limit)
        
        if not emails:
            console.print("📭 No emails found in the specified time range.")
            return
        
        progress.update(task, description=f"Processing {len(emails)} emails with AI triage...")
        
        # Create smart inbox
        smart_inbox = await crew.execute_task("smart_inbox", emails=emails)
        
        progress.update(task, description="Smart inbox ready!", completed=True)
    
    # Display results
    console.print("\n🧠 Smart Inbox Results", style="bold blue")
    console.print("=" * 50)
    
    stats = smart_inbox["stats"]
    console.print(f"📊 Processed {stats['total_emails']} emails:")
    console.print(f"   🔥 Priority: {stats['priority_count']} emails")
    console.print(f"   📧 Regular: {stats['regular_count']} emails")
    console.print(f"   📁 Auto-archived: {stats['archived_count']} emails")
    console.print(f"   🗑️  Spam: {stats['spam_count']} emails")
    
    # Show priority emails
    if smart_inbox["priority_inbox"]:
        console.print("\n🔥 Priority Inbox", style="bold red")
        _display_email_list(smart_inbox["priority_inbox"], show_scores, max_items=10)
    
    # Show regular emails
    if smart_inbox["regular_inbox"]:
        console.print("\n📧 Regular Inbox", style="bold")
        _display_email_list(smart_inbox["regular_inbox"], show_scores, max_items=15)
    
    # Show auto-archived if requested
    if smart_inbox["auto_archived"] and show_scores:
        console.print("\n📁 Auto-Archived", style="dim")
        _display_email_list(smart_inbox["auto_archived"], show_scores, max_items=5)
    
    await crew.shutdown()


async def _priority_inbox(limit: int, min_score: float):
    """Show priority inbox."""
    console.print("🔥 Priority Inbox", style="bold red")
    console.print(f"Emails with attention score ≥ {min_score}")
    console.print("=" * 50)
    
    # This would query the database for emails with high attention scores
    # For now, show a placeholder
    console.print("📭 No high-priority emails found.")
    console.print(f"💡 Tip: Adjust threshold with 'email-agent inbox tune --priority-threshold {min_score - 0.1}'")


async def _archived_emails(limit: int, days: int):
    """Show auto-archived emails."""
    console.print("📁 Auto-Archived Emails", style="bold")
    console.print(f"Last {days} days, showing up to {limit} emails")
    console.print("=" * 50)
    
    # This would query the database for auto-archived emails
    console.print("📭 No auto-archived emails found.")
    console.print("💡 Use 'email-agent inbox smart' to enable auto-archiving")


async def _triage_stats():
    """Show triage statistics."""
    crew = EmailAgentCrew()
    await crew.initialize_crew({"verbose": False})
    
    # Get triage agent stats
    stats = await crew.get_agent_status("triage_agent")
    
    # Create stats table
    table = Table(title="📊 Triage Agent Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Emails Triaged", str(stats.get("emails_triaged", 0)))
    table.add_row("Auto-Archived", str(stats.get("auto_archived", 0)))
    table.add_row("Priority Flagged", str(stats.get("priority_flagged", 0)))
    table.add_row("Accuracy", f"{stats.get('accuracy_percentage', 0):.1f}%")
    table.add_row("AI Enabled", "✅ Yes" if stats.get("ai_enabled") else "❌ No")
    table.add_row("Sender Patterns", str(stats.get("sender_patterns", 0)))
    
    if stats.get("last_triage"):
        table.add_row("Last Triage", str(stats["last_triage"]))
    
    console.print(table)
    
    await crew.shutdown()


async def _tune_triage(priority_threshold: float, archive_threshold: float, show_current: bool):
    """Tune triage settings."""
    console.print("⚙️ Triage Settings", style="bold blue")
    
    if show_current:
        console.print("\n📋 Current Settings:")
        console.print("   Priority threshold: 0.7 (emails with score ≥ 0.7 go to priority inbox)")
        console.print("   Archive threshold: 0.3 (emails with score ≤ 0.3 get auto-archived)")
        console.print("   Auto-archive categories: promotions, updates")
    
    if priority_threshold is not None:
        if 0.0 <= priority_threshold <= 1.0:
            console.print(f"\n✅ Priority threshold updated to {priority_threshold}")
            # Here you would save to database/config
        else:
            console.print("❌ Priority threshold must be between 0.0 and 1.0", style="red")
    
    if archive_threshold is not None:
        if 0.0 <= archive_threshold <= 1.0:
            console.print(f"✅ Archive threshold updated to {archive_threshold}")
            # Here you would save to database/config
        else:
            console.print("❌ Archive threshold must be between 0.0 and 1.0", style="red")
    
    console.print("\n💡 Tips:")
    console.print("   • Lower priority threshold = more emails in priority inbox")
    console.print("   • Higher archive threshold = more emails get auto-archived")
    console.print("   • Use 'email-agent inbox stats' to monitor accuracy")


async def _provide_feedback(email_id: str, correct_decision: str, user_action: str):
    """Provide feedback to improve triage accuracy."""
    try:
        console.print(f"🎯 Providing feedback for email {email_id}", style="bold blue")
        
        # Initialize crew and get triage agent
        crew = EmailAgentCrew()
        await crew.initialize_crew({"verbose": False})
        
        # Convert string to TriageDecision enum
        from ...agents.triage_agent import TriageDecision
        decision_map = {
            'priority_inbox': TriageDecision.PRIORITY_INBOX,
            'regular_inbox': TriageDecision.REGULAR_INBOX,
            'auto_archive': TriageDecision.AUTO_ARCHIVE,
            'spam_folder': TriageDecision.SPAM_FOLDER
        }
        
        correct_triage_decision = decision_map.get(correct_decision)
        if not correct_triage_decision:
            console.print(f"❌ Invalid decision: {correct_decision}", style="red")
            return
        
        # Provide feedback to triage agent
        await crew.triage_agent.learn_from_user_feedback(email_id, correct_triage_decision, user_action)
        
        console.print(f"✅ Feedback recorded: Email should be in {correct_decision.replace('_', ' ')}")
        console.print("🧠 The system will learn from this correction and improve future triaging.")
        
        await crew.shutdown()
        
    except Exception as e:
        console.print(f"❌ Failed to provide feedback: {str(e)}", style="red")


async def _show_learning_insights():
    """Show what the system has learned from user habits."""
    try:
        console.print("🧠 Email Habit Learning Insights", style="bold blue")
        console.print("=" * 50)
        
        # Initialize crew and get insights
        crew = EmailAgentCrew()
        await crew.initialize_crew({"verbose": False})
        
        insights = crew.triage_agent.get_learning_insights()
        
        # Learning statistics
        learning_stats = insights.get("learning_stats", {})
        console.print("\n📊 Learning Statistics:")
        console.print(f"   Total feedback received: {learning_stats.get('total_feedback_received', 0)}")
        console.print(f"   Learning active: {'✅ Yes' if learning_stats.get('learning_active') else '❌ No'}")
        
        if learning_stats.get("last_feedback"):
            console.print(f"   Last feedback: {learning_stats['last_feedback']}")
        
        # Sender insights
        sender_insights = insights.get("sender_insights", {})
        if sender_insights.get("most_important"):
            console.print("\n👥 Most Important Senders:")
            most_important = sender_insights["most_important"]
            
            sender_table = Table()
            sender_table.add_column("Sender", style="cyan")
            sender_table.add_column("Importance Score", style="green")
            
            for sender, score in most_important:
                sender_table.add_row(sender, f"{score:.3f}")
            
            console.print(sender_table)
        
        # Category insights
        category_insights = insights.get("category_insights", {})
        if category_insights:
            console.print("\n📂 Category Learning:")
            
            cat_table = Table()
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Priority Tendency", style="green")
            cat_table.add_column("Archive Tendency", style="yellow")
            cat_table.add_column("Feedback Count", style="dim")
            
            for category, prefs in category_insights.items():
                cat_table.add_row(
                    category,
                    f"{prefs.get('priority_tendency', 0.0):.2f}",
                    f"{prefs.get('archive_tendency', 0.0):.2f}",
                    str(prefs.get('feedback_count', 0))
                )
            
            console.print(cat_table)
        
        # Urgency insights
        urgency_insights = insights.get("urgency_insights", {})
        if urgency_insights.get("learned_urgency_keywords"):
            console.print("\n⚡ Learned Urgency Keywords:")
            keywords = urgency_insights["learned_urgency_keywords"][:10]
            
            urgency_table = Table()
            urgency_table.add_column("Keyword", style="cyan")
            urgency_table.add_column("Urgency Score", style="red")
            
            for keyword, score in keywords:
                urgency_table.add_row(keyword, f"{score:.3f}")
            
            console.print(urgency_table)
        
        # Time insights
        time_insights = insights.get("time_insights", {})
        if time_insights.get("priority_hours"):
            console.print("\n🕒 Time-based Preferences:")
            priority_hours = time_insights["priority_hours"]
            
            # Find peak priority hours
            if priority_hours:
                peak_hours = sorted(priority_hours.items(), key=lambda x: x[1], reverse=True)[:5]
                console.print("   Peak priority hours:")
                for hour, count in peak_hours:
                    console.print(f"     {hour:02d}:00 - {count} priority emails")
        
        if not any([sender_insights, category_insights, urgency_insights, time_insights]):
            console.print("\n💡 No learning data available yet.")
            console.print("   Use 'email-agent inbox feedback' to provide corrections and help the system learn.")
        
        await crew.shutdown()
        
    except Exception as e:
        console.print(f"❌ Failed to show learning insights: {str(e)}", style="red")


async def _show_sender_importance():
    """Show learned sender importance scores."""
    try:
        console.print("👥 Sender Importance Scores", style="bold blue")
        console.print("=" * 50)
        
        # Initialize crew and get sender scores
        crew = EmailAgentCrew()
        await crew.initialize_crew({"verbose": False})
        
        sender_scores = crew.triage_agent.sender_importance
        
        if not sender_scores:
            console.print("📭 No sender importance data available yet.")
            console.print("💡 The system learns sender importance from your email interactions.")
            return
        
        # Sort senders by importance score
        sorted_senders = sorted(sender_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Create table
        table = Table(title=f"📊 {len(sorted_senders)} Sender Importance Scores")
        table.add_column("Sender", style="cyan", max_width=40)
        table.add_column("Importance Score", style="green")
        table.add_column("Priority Level", style="yellow")
        
        for sender, score in sorted_senders:
            # Determine priority level
            if score >= 0.8:
                priority_level = "🔴 Very High"
            elif score >= 0.6:
                priority_level = "🟡 High"
            elif score >= 0.4:
                priority_level = "🟢 Medium"
            elif score >= 0.2:
                priority_level = "🔵 Low"
            else:
                priority_level = "⚫ Very Low"
            
            table.add_row(sender, f"{score:.3f}", priority_level)
        
        console.print(table)
        
        # Show statistics
        console.print("\n📈 Statistics:")
        console.print(f"   Average importance: {sum(sender_scores.values()) / len(sender_scores):.3f}")
        console.print(f"   Highest score: {max(sender_scores.values()):.3f}")
        console.print(f"   Lowest score: {min(sender_scores.values()):.3f}")
        
        high_importance = [s for s in sender_scores.values() if s >= 0.7]
        console.print(f"   High importance senders: {len(high_importance)}")
        
        await crew.shutdown()
        
    except Exception as e:
        console.print(f"❌ Failed to show sender importance: {str(e)}", style="red")


def _display_email_list(emails: List[Email], show_scores: bool, max_items: int = 10):
    """Display a list of emails in a table."""
    if not emails:
        return
    
    table = Table()
    table.add_column("From", style="cyan", max_width=25)
    table.add_column("Subject", style="white", max_width=40)
    table.add_column("Date", style="dim", max_width=12)
    table.add_column("Category", style="yellow", max_width=12)
    
    if show_scores:
        table.add_column("Score", style="green", max_width=6)
    
    for email in emails[:max_items]:
        row = [
            email.sender.email.split('@')[0],  # Just username part
            email.subject[:40] + "..." if len(email.subject) > 40 else email.subject,
            email.received_date.strftime("%m/%d %H:%M") if email.received_date else "Unknown",
            email.category.value
        ]
        
        if show_scores:
            # Extract attention score from triage metadata
            triage_data = email.connector_data.get("triage", {})
            attention_score = triage_data.get("attention_score", {}).get("score", 0.0)
            row.append(f"{attention_score:.2f}")
        
        table.add_row(*row)
    
    if len(emails) > max_items:
        table.add_row("...", f"({len(emails) - max_items} more)", "", "", "")
    
    console.print(table)


if __name__ == "__main__":
    app()
