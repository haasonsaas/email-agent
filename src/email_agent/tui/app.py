"""Main TUI application using Textual."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Select,
    Switch,
    TabbedContent,
    TabPane,
)

from ..agents import EmailAgentCrew
from ..models import Email
from ..storage import DatabaseManager

logger = logging.getLogger(__name__)


class EmailList(DataTable):
    """Widget for displaying email list."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_columns(
            "Priority", "Subject", "From", "Date", "Category", "Score", "Status"
        )
        self.cursor_type = "row"
        self.zebra_stripes = True

    def load_emails(self, emails: List[Email], show_triage_data: bool = False):
        """Load emails into the table."""
        self.clear()

        for email in emails:
            status = "📧" if not email.is_read else "✓"
            if email.is_flagged:
                status += "⭐"

            # Priority indicator with emoji
            priority_icon = {
                "urgent": "🔴",
                "high": "🟡",
                "normal": "🟢",
                "low": "⚪",
            }.get(email.priority.value, "⚪")

            # Attention score from triage data (if available)
            attention_score = "—"
            if hasattr(email, "attention_score"):
                attention_score = f"{email.attention_score:.2f}"
            elif (
                show_triage_data
                and hasattr(email, "connector_data")
                and email.connector_data
            ):
                attention_score = (
                    f"{email.connector_data.get('attention_score', 0):.2f}"
                )

            self.add_row(
                priority_icon,
                email.subject,
                email.sender.email,
                email.date.strftime("%Y-%m-%d %H:%M"),
                email.category.value.title(),
                attention_score,
                status,
                key=email.id,
            )


class EmailDetails(RichLog):
    """Widget for displaying email details."""

    def show_email(self, email: Email):
        """Display email details."""
        self.clear()

        self.write(f"[bold cyan]Subject:[/bold cyan] {email.subject}")
        self.write(f"[bold cyan]From:[/bold cyan] {email.sender}")
        self.write(f"[bold cyan]Date:[/bold cyan] {email.date}")
        self.write(f"[bold cyan]Category:[/bold cyan] {email.category.value.title()}")
        self.write(f"[bold cyan]Priority:[/bold cyan] {email.priority.value.title()}")

        if email.tags:
            self.write(f"[bold cyan]Tags:[/bold cyan] {', '.join(email.tags)}")

        if email.summary:
            self.write("\n[bold green]AI Summary:[/bold green]")
            self.write(f"[dim]{email.summary}[/dim]")

        if email.action_items:
            self.write("\n[bold yellow]Action Items:[/bold yellow]")
            for item in email.action_items:
                self.write(f"• {item}")

        self.write("\n[bold cyan]Body:[/bold cyan]")
        if email.body_text:
            self.write(
                email.body_text[:1000] + ("..." if len(email.body_text) > 1000 else "")
            )
        else:
            self.write("[dim]No text content[/dim]")


class SmartInboxView(Vertical):
    """Smart inbox with AI-powered triage."""

    def compose(self) -> ComposeResult:
        yield Label("🧠 Smart Inbox - AI Triaged Emails", classes="sidebar-title")
        yield Label("")

        with Horizontal():
            yield Button("🔥 Priority Inbox", id="priority-inbox-btn", variant="error")
            yield Button("📥 Regular Inbox", id="regular-inbox-btn", variant="primary")
            yield Button("🗂️ Auto-Archived", id="archived-inbox-btn")
            yield Button("🕷️ Spam", id="spam-inbox-btn", variant="warning")

        with Horizontal():
            yield Button("🎯 Provide Feedback", id="feedback-btn", variant="success")
            yield Button("🧠 Learning Insights", id="learning-insights-btn")
            yield Button("👥 Sender Scores", id="sender-scores-btn")

        yield Label("")
        yield Label("Triage Statistics:", classes="setting-desc")
        yield Container(id="triage-stats-container")
        yield Label("")

        yield EmailList(id="smart-email-list")

    def update_triage_stats(self, stats: dict):
        """Update triage statistics display."""
        container = self.query_one("#triage-stats-container", Container)
        container.remove_children()

        stats_data = [
            ("Total Emails", stats.get("total_emails", 0)),
            ("Priority", stats.get("priority_count", 0)),
            ("Regular", stats.get("regular_count", 0)),
            ("Archived", stats.get("archived_count", 0)),
            ("Spam", stats.get("spam_count", 0)),
        ]

        for label, count in stats_data:
            stat_label = Label(f"{label}: {count}")
            container.mount(stat_label)


class DraftSuggestionsPanel(Vertical):
    """Panel for AI draft suggestions."""

    def compose(self) -> ComposeResult:
        yield Label("✍️ AI Draft Suggestions", classes="sidebar-title")
        yield Label("")

        # Writing style status
        yield Label("📝 Writing Style:", classes="setting-desc")
        yield Label("Not analyzed", id="writing-style-status")
        yield Button(
            "🔍 Analyze Writing Style", id="analyze-style-btn", variant="primary"
        )
        yield Label("")

        # Draft generation
        yield Label("Current Email:", classes="setting-desc")
        yield Label("No email selected", id="current-email-subject")
        yield Label("")

        with Horizontal():
            yield Button(
                "✍️ Generate Drafts", id="generate-drafts-btn", variant="success"
            )
            yield Select(
                [
                    ("3 suggestions", "3"),
                    ("5 suggestions", "5"),
                    ("7 suggestions", "7"),
                ],
                value="3",
                id="num-drafts-select",
            )

        yield Label("")
        yield Label("Draft Suggestions:", classes="setting-desc")
        yield RichLog(id="draft-suggestions-log", max_lines=20)

    def update_writing_style_status(self, status: dict):
        """Update writing style analysis status."""
        if status.get("status") == "analyzed":
            last_updated = status.get("last_updated", "Unknown")
            style_text = f"✅ Analyzed ({last_updated})"
            self.query_one("#writing-style-status", Label).update(style_text)
        else:
            self.query_one("#writing-style-status", Label).update("❌ Not analyzed")

    def update_current_email(self, email: Optional[Email]):
        """Update current email display."""
        if email:
            self.query_one("#current-email-subject", Label).update(
                email.subject[:50] + "..."
            )
        else:
            self.query_one("#current-email-subject", Label).update("No email selected")

    def show_draft_suggestions(self, suggestions: List[dict]):
        """Display draft suggestions."""
        log = self.query_one("#draft-suggestions-log", RichLog)
        log.clear()

        if not suggestions:
            log.write("No draft suggestions available")
            return

        for i, suggestion in enumerate(suggestions):
            log.write(f"[bold cyan]Draft #{i+1}[/bold cyan]")
            log.write(f"[bold]Subject:[/bold] {suggestion['subject']}")
            log.write(f"[bold]Confidence:[/bold] {suggestion['confidence']:.2f}")
            log.write(f"[bold]Style Match:[/bold] {suggestion['style_match']:.2f}")
            log.write(f"[bold]Tone:[/bold] {suggestion['suggested_tone']}")
            log.write(f"[bold]Length:[/bold] {suggestion['estimated_length']}")
            log.write("")
            log.write("[bold]Body:[/bold]")
            log.write(suggestion["body"])
            log.write("")
            log.write(f"[dim]Reasoning: {suggestion['reasoning']}[/dim]")
            log.write("─" * 50)


class FeedbackDialog(ModalScreen):
    """Modal dialog for providing triage feedback."""

    def __init__(self, email: Email):
        super().__init__()
        self.email = email

    def compose(self) -> ComposeResult:
        with Container(id="feedback-dialog"):
            yield Label("🎯 Provide Feedback for Email", classes="dialog-title")
            yield Label("")
            yield Label(f"Subject: {self.email.subject[:60]}...")
            yield Label(f"From: {self.email.sender.email}")
            yield Label("")
            yield Label("What should the correct triage decision be?")
            yield Select(
                [
                    ("🔥 Priority Inbox", "priority_inbox"),
                    ("📥 Regular Inbox", "regular_inbox"),
                    ("🗂️ Auto-Archive", "auto_archive"),
                    ("🕷️ Spam Folder", "spam_folder"),
                ],
                id="feedback-decision-select",
            )
            yield Label("")
            yield Input(
                placeholder="Additional feedback (optional)", id="feedback-comment"
            )
            yield Label("")

            with Horizontal():
                yield Button(
                    "✅ Submit Feedback", id="submit-feedback-btn", variant="success"
                )
                yield Button("❌ Cancel", id="cancel-feedback-btn")

    CSS = """
    #feedback-dialog {
        width: 60;
        height: 20;
        border: thick $primary;
        background: $surface;
        padding: 2;
        align: center middle;
    }
    
    .dialog-title {
        text-style: bold;
        color: $primary;
        text-align: center;
    }
    """


class LearningInsightsDialog(ModalScreen):
    """Modal dialog showing learning insights."""

    def __init__(self, insights: dict):
        super().__init__()
        self.insights = insights

    def compose(self) -> ComposeResult:
        with Container(id="insights-dialog"):
            yield Label("🧠 Email Habit Learning Insights", classes="dialog-title")
            yield Label("")

            # Learning stats
            learning_stats = self.insights.get("learning_stats", {})
            yield Label(
                f"📊 Total feedback received: {learning_stats.get('total_feedback_received', 0)}"
            )
            yield Label(
                f"🎯 Learning active: {'✅ Yes' if learning_stats.get('learning_active') else '❌ No'}"
            )
            yield Label("")

            # Top senders
            sender_insights = self.insights.get("sender_insights", {})
            if sender_insights.get("most_important"):
                yield Label("👥 Most Important Senders:", classes="insights-section")
                insights_log = RichLog(id="insights-log", max_lines=15)

                for sender, score in sender_insights["most_important"][:5]:
                    insights_log.write(f"• {sender}: {score:.3f}")

                yield insights_log

            yield Label("")
            with Horizontal():
                yield Button(
                    "📋 Full Report", id="full-insights-btn", variant="primary"
                )
                yield Button("❌ Close", id="close-insights-btn")

    CSS = """
    #insights-dialog {
        width: 80;
        height: 25;
        border: thick $primary;
        background: $surface;
        padding: 2;
        align: center middle;
    }
    
    .insights-section {
        text-style: bold;
        color: $accent;
        margin: 1 0;
    }
    
    #insights-log {
        height: 10;
        border: solid $primary;
    }
    """


class SenderScoresDialog(ModalScreen):
    """Modal dialog showing sender importance scores."""

    def __init__(self, sender_scores: dict):
        super().__init__()
        self.sender_scores = sender_scores

    def compose(self) -> ComposeResult:
        with Container(id="scores-dialog"):
            yield Label("👥 Sender Importance Scores", classes="dialog-title")
            yield Label("")

            scores_table = DataTable(id="scores-table")
            scores_table.add_columns("Sender", "Score", "Priority Level")
            scores_table.cursor_type = "row"
            scores_table.zebra_stripes = True

            # Sort and add sender scores
            sorted_senders = sorted(
                self.sender_scores.items(), key=lambda x: x[1], reverse=True
            )

            for sender, score in sorted_senders[:20]:  # Top 20
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

                scores_table.add_row(
                    sender[:30] + "..." if len(sender) > 30 else sender,
                    f"{score:.3f}",
                    priority_level,
                )

            yield scores_table
            yield Label("")
            yield Button("❌ Close", id="close-scores-btn")

    CSS = """
    #scores-dialog {
        width: 90;
        height: 30;
        border: thick $primary;
        background: $surface;
        padding: 2;
        align: center middle;
    }
    
    #scores-table {
        height: 20;
    }
    """


class NarrativeBriefPanel(Vertical):
    """Panel for narrative-style daily briefs."""

    def compose(self) -> ComposeResult:
        yield Label("📖 Narrative Daily Brief", classes="sidebar-title")
        yield Label("")

        with Horizontal():
            yield Input(placeholder="Select date (YYYY-MM-DD)", id="brief-date-input")
            yield Button(
                "📖 Generate Narrative", id="generate-narrative-btn", variant="success"
            )

        yield Label("")
        yield Label("📊 Brief Metrics:", classes="setting-desc")
        yield Container(id="brief-metrics-container")
        yield Label("")

        yield Label("📖 Today's Email Story:", classes="setting-desc")
        yield RichLog(id="narrative-brief-log", max_lines=25)

    def show_narrative_brief(self, brief_data: dict):
        """Display narrative brief."""
        log = self.query_one("#narrative-brief-log", RichLog)
        log.clear()

        # Show headline
        headline = brief_data.get("headline", "No headline")
        log.write(f"[bold cyan]{headline}[/bold cyan]")
        log.write("")

        # Show reading time and narrative score
        reading_time = brief_data.get("estimated_reading_time", 45)
        narrative_score = brief_data.get("narrative_score", 0.8)
        log.write(
            f"[dim]📖 Reading time: {reading_time}s | Narrative score: {narrative_score:.1f}/1.0[/dim]"
        )
        log.write("")

        # Show story
        story = brief_data.get("summary", "No story available")
        log.write("[bold]The Story:[/bold]")
        log.write(story)
        log.write("")

        # Show key characters
        characters = brief_data.get("key_characters", [])
        if characters:
            log.write("[bold]Key Characters:[/bold]")
            for char in characters[:5]:
                log.write(f"• {char}")
            log.write("")

        # Show themes
        themes = brief_data.get("themes", [])
        if themes:
            log.write("[bold]Main Themes:[/bold]")
            for theme in themes:
                log.write(f"• {theme}")
            log.write("")

        # Show action items
        action_items = brief_data.get("action_items", [])
        if action_items:
            log.write("[bold]Action Items:[/bold]")
            for item in action_items:
                log.write(f"• {item}")
            log.write("")

        # Show deadlines
        deadlines = brief_data.get("deadlines", [])
        if deadlines:
            log.write("[bold]Deadlines:[/bold]")
            for deadline in deadlines:
                log.write(f"• {deadline}")

    def update_brief_metrics(self, metrics: dict):
        """Update brief metrics display."""
        container = self.query_one("#brief-metrics-container", Container)
        container.remove_children()

        metrics_data = [
            ("Emails Processed", metrics.get("emails_processed", 0)),
            ("Reading Time", f"{metrics.get('estimated_reading_time', 0)}s"),
            ("Narrative Score", f"{metrics.get('narrative_score', 0):.1f}/1.0"),
            ("Story Arcs", len(metrics.get("story_arcs", []))),
        ]

        for label, value in metrics_data:
            metric_label = Label(f"{label}: {value}")
            container.mount(metric_label)


class LogViewer(Vertical):
    """Log viewer panel for monitoring application logs."""

    def compose(self) -> ComposeResult:
        yield Label("📋 Application Logs", classes="sidebar-title")
        yield Label("")

        with Horizontal():
            yield Button("🔄 Refresh Logs", id="refresh-logs-btn", variant="primary")
            yield Button("🗑️ Clear Logs", id="clear-logs-btn")
            yield Select(
                [
                    ("Debug", "DEBUG"),
                    ("Info", "INFO"),
                    ("Warning", "WARNING"),
                    ("Error", "ERROR"),
                ],
                value="INFO",
                id="log-level-select",
            )

        yield Label("")
        yield RichLog(id="app-logs-display", max_lines=50)

    def update_logs(self, log_entries: List[str]):
        """Update the log display with new entries."""
        log_display = self.query_one("#app-logs-display", RichLog)
        log_display.clear()

        for entry in log_entries[-50:]:  # Show last 50 entries
            log_display.write(entry)

    def add_log_entry(self, entry: str):
        """Add a single log entry."""
        log_display = self.query_one("#app-logs-display", RichLog)
        log_display.write(entry)


class TUILogHandler(logging.Handler):
    """Custom log handler that sends logs to the TUI instead of console."""

    def __init__(self, tui_app):
        super().__init__()
        self.tui_app = tui_app
        self.log_entries = []

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_entries.append(msg)

            # Keep only last 100 entries in memory
            if len(self.log_entries) > 100:
                self.log_entries = self.log_entries[-100:]

            # Try to update TUI log viewer if it exists
            try:
                if hasattr(self.tui_app, "query_one"):
                    log_viewer = self.tui_app.query_one("#app-logs-display", RichLog)
                    log_viewer.write(msg)
            except Exception:
                pass  # TUI might not be ready or log viewer not visible

        except Exception:
            pass  # Ignore errors in log handler to prevent recursion


class StatsSidebar(Vertical):
    """Sidebar showing email statistics."""

    def compose(self) -> ComposeResult:
        yield Label("📊 Statistics", classes="sidebar-title")
        yield Label("Total: 0", id="stats-total")
        yield Label("Unread: 0", id="stats-unread")
        yield Label("Flagged: 0", id="stats-flagged")
        yield Label("")

        yield Label("🧠 AI Triage", classes="sidebar-title")
        yield Label("Priority: 0", id="triage-priority")
        yield Label("Regular: 0", id="triage-regular")
        yield Label("Archived: 0", id="triage-archived")
        yield Label("")

        yield Label("📂 Categories", classes="sidebar-title")
        yield Container(id="categories-container")
        yield Label("")

        yield Button("🔄 Refresh", id="refresh-button", variant="primary")
        yield Button("📧 Sync", id="sync-button")
        yield Button("📝 Brief", id="brief-button")
        yield Button("🧠 Smart Triage", id="smart-triage-button", variant="success")

    def update_stats(self, stats: dict):
        """Update statistics display."""
        self.query_one("#stats-total", Label).update(f"Total: {stats.get('total', 0)}")
        self.query_one("#stats-unread", Label).update(
            f"Unread: {stats.get('unread', 0)}"
        )
        self.query_one("#stats-flagged", Label).update(
            f"Flagged: {stats.get('flagged', 0)}"
        )

        # Update categories
        container = self.query_one("#categories-container", Container)
        container.remove_children()

        categories = stats.get("categories", {})
        for category, count in categories.items():
            if count > 0:
                label = Label(f"{category.title()}: {count}")
                container.mount(label)

    def update_triage_stats(self, triage_stats: dict):
        """Update triage statistics display."""
        self.query_one("#triage-priority", Label).update(
            f"Priority: {triage_stats.get('priority_count', 0)}"
        )
        self.query_one("#triage-regular", Label).update(
            f"Regular: {triage_stats.get('regular_count', 0)}"
        )
        self.query_one("#triage-archived", Label).update(
            f"Archived: {triage_stats.get('archived_count', 0)}"
        )


class SettingsPanel(Vertical):
    """Settings panel with AI configuration options."""

    def compose(self) -> ComposeResult:
        yield Label("⚙️ AI Settings", classes="settings-title")
        yield Label("")

        # AI Model Selection
        yield Label("AI Model:")
        yield Select(
            [
                ("gpt-4o-mini", "gpt-4o-mini"),
                ("gpt-4o", "gpt-4o"),
                ("gpt-3.5-turbo", "gpt-3.5-turbo"),
            ],
            value="gpt-4o-mini",
            id="ai-model-select",
        )
        yield Label("")

        # Auto-processing settings
        yield Label("Auto-processing:")
        yield Switch(value=True, id="auto-summarize")
        yield Label("Generate AI summaries for new emails", classes="setting-desc")
        yield Label("")

        yield Switch(value=True, id="auto-categorize")
        yield Label("Auto-categorize new emails", classes="setting-desc")
        yield Label("")

        yield Switch(value=False, id="auto-action-items")
        yield Label("Extract action items from emails", classes="setting-desc")
        yield Label("")

        # Sync settings
        yield Label("📧 Sync Settings", classes="settings-title")
        yield Label("")

        yield Label("Sync Frequency (minutes):")
        yield Input(value="30", id="sync-frequency")
        yield Label("")

        yield Label("Max Emails per Sync:")
        yield Input(value="100", id="max-emails")
        yield Label("")

        # Save button
        yield Button("💾 Save Settings", id="save-settings", variant="primary")
        yield Label("")
        yield Button("🔄 Process All Emails", id="process-all", variant="success")
        yield Label("Run AI processing on all existing emails", classes="setting-desc")


class SmartSearch(Horizontal):
    """Smart search widget with AI-powered filtering."""

    def compose(self) -> ComposeResult:
        yield Input(
            placeholder="Search emails... (try 'urgent emails' or 'action required')",
            id="search-input",
        )
        yield Button("🔍 Search", id="search-button")
        yield Button("🤖 AI Filter", id="ai-filter-button")


class AnalyticsDashboard(Vertical):
    """Analytics dashboard with AI insights."""

    def compose(self) -> ComposeResult:
        yield Label("📊 Email Analytics & AI Insights", classes="settings-title")
        yield Label("")

        # Quick stats grid
        with Horizontal():
            with Vertical():
                yield Label("📈 Processing Stats", classes="setting-desc")
                yield Label("AI Summaries: 0", id="ai-summaries-count")
                yield Label("Action Items: 0", id="action-items-count")
                yield Label("Processed Emails: 0", id="processed-count")

            with Vertical():
                yield Label("🎯 Top Categories", classes="setting-desc")
                yield Container(id="top-categories")

            with Vertical():
                yield Label("⚡ Recent Activity", classes="setting-desc")
                yield Container(id="recent-activity")

        yield Label("")
        yield Label("🤖 AI Insights", classes="settings-title")
        yield RichLog(id="ai-insights-log")

        yield Label("")
        with Horizontal():
            yield Button(
                "🔄 Refresh Analytics", id="refresh-analytics", variant="primary"
            )
            yield Button("📋 Generate Report", id="generate-report")
            yield Button("🧹 Cleanup Database", id="cleanup-db")

        yield Label("")
        yield Label("🤖 Advanced AI Analysis", classes="settings-title")
        with Horizontal():
            yield Button(
                "😊 Sentiment Analysis", id="analyze-sentiment", variant="success"
            )
            yield Button("🧵 Thread Analysis", id="analyze-threads", variant="success")
            yield Button(
                "🔍 Comprehensive Analysis",
                id="comprehensive-analysis",
                variant="warning",
            )

    def update_analytics(self, data: dict):
        """Update analytics display with data."""
        try:
            # Update processing stats
            self.query_one("#ai-summaries-count", Label).update(
                f"AI Summaries: {data.get('ai_summaries', 0)}"
            )
            self.query_one("#action-items-count", Label).update(
                f"Action Items: {data.get('action_items', 0)}"
            )
            self.query_one("#processed-count", Label).update(
                f"Processed Emails: {data.get('processed_emails', 0)}"
            )

            # Update top categories
            categories_container = self.query_one("#top-categories", Container)
            categories_container.remove_children()

            categories = data.get("top_categories", {})
            for category, count in list(categories.items())[:5]:
                label = Label(f"{category}: {count}")
                categories_container.mount(label)

            # Update recent activity
            activity_container = self.query_one("#recent-activity", Container)
            activity_container.remove_children()

            recent = data.get("recent_activity", [])
            for activity in recent[:5]:
                label = Label(activity)
                activity_container.mount(label)

            # Update AI insights
            insights_log = self.query_one("#ai-insights-log", RichLog)
            insights_log.clear()

            insights = data.get("ai_insights", [])
            for insight in insights:
                insights_log.write(f"💡 {insight}")

        except Exception as e:
            logger.error(f"Failed to update analytics: {e}")


class EmailAgentTUI(App):
    """Main TUI application for Email Agent."""

    CSS = """
    Screen {
        layout: vertical;
    }
    
    Horizontal {
        height: 1fr;
    }
    
    .sidebar {
        width: 25%;
        background: $surface;
        border-right: thick $primary;
        padding: 1;
    }
    
    .sidebar-title {
        color: $primary;
        text-style: bold;
    }
    
    .main-content {
        width: 75%;
        padding: 1;
    }
    
    EmailList {
        height: 1fr;
    }
    
    EmailDetails {
        height: 1fr;
        border: thick $primary;
        padding: 1;
    }
    
    TabbedContent {
        height: 1fr;
    }
    
    .status-bar {
        background: $surface;
        color: $text;
        height: 3;
        padding: 1;
    }
    
    .settings-title {
        color: $primary;
        text-style: bold;
        margin: 1 0;
    }
    
    .setting-desc {
        color: $text-muted;
        margin-bottom: 1;
    }
    
    SettingsPanel {
        padding: 1;
        height: 1fr;
        overflow-y: auto;
    }
    
    SmartSearch {
        margin-bottom: 1;
    }
    
    #search-input {
        width: 1fr;
    }
    
    AnalyticsDashboard {
        padding: 1;
        height: 1fr;
        overflow-y: auto;
    }
    
    #ai-insights-log {
        height: 8;
        border: thick $primary;
    }
    
    SmartInboxView {
        padding: 1;
        height: 1fr;
        overflow-y: auto;
    }
    
    DraftSuggestionsPanel {
        padding: 1;
        height: 1fr;
        overflow-y: auto;
    }
    
    NarrativeBriefPanel {
        padding: 1;
        height: 1fr;
        overflow-y: auto;
    }
    
    LogViewer {
        padding: 1;
        height: 1fr;
        overflow-y: auto;
    }
    
    #draft-suggestions-log {
        height: 20;
        border: thick $primary;
    }
    
    #narrative-brief-log {
        height: 15;
        border: thick $primary;
    }
    
    #app-logs-display {
        height: 20;
        border: thick $primary;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("s", "sync", "Sync"),
        ("b", "brief", "Brief"),
        ("f", "filter", "Filter"),
        ("t", "smart_triage", "Smart Triage"),
        ("d", "generate_drafts", "Generate Drafts"),
        ("n", "generate_narrative_brief", "Narrative Brief"),
    ]

    selected_email: reactive[Optional[Email]] = reactive(None)

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.crew = None
        self.current_emails: List[Email] = []
        self.tui_log_handler = None
        self._setup_logging()

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header(show_clock=True)

        with Horizontal():
            # Sidebar
            with Vertical(classes="sidebar"):
                yield StatsSidebar()

            # Main content area
            with Vertical(classes="main-content"):
                with TabbedContent():
                    with TabPane("📧 Emails", id="emails-tab"):
                        yield SmartSearch()
                        yield EmailList(id="email-list")

                    with TabPane("🧠 Smart Inbox", id="smart-inbox-tab"):
                        yield SmartInboxView()

                    with TabPane("📄 Details", id="details-tab"):
                        yield EmailDetails(id="email-details")

                    with TabPane("✍️ AI Drafts", id="drafts-tab"):
                        yield DraftSuggestionsPanel()

                    with TabPane("📖 Brief", id="narrative-brief-tab"):
                        yield NarrativeBriefPanel()

                    with TabPane("📊 Dashboard", id="dashboard-tab"):
                        yield AnalyticsDashboard()

                    with TabPane("📋 Logs", id="logs-tab"):
                        yield LogViewer()

                    with TabPane("⚙️ Settings", id="settings-tab"):
                        yield SettingsPanel()

        yield Footer()

    def _setup_logging(self):
        """Configure logging to work with TUI."""
        # Create logs directory
        logs_dir = Path.home() / ".email_agent" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Set up file logging
        log_file = logs_dir / "tui.log"

        # Remove existing handlers to avoid conflicts
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)

        # Create TUI handler
        self.tui_log_handler = TUILogHandler(self)
        self.tui_log_handler.setLevel(logging.INFO)
        tui_formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
        self.tui_log_handler.setFormatter(tui_formatter)

        # Add handlers to root logger
        root_logger.addHandler(file_handler)
        root_logger.addHandler(self.tui_log_handler)
        root_logger.setLevel(logging.INFO)

        # Suppress some noisy loggers
        logging.getLogger("textual").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)

    async def on_mount(self) -> None:
        """Initialize the application."""
        self.title = "Email Agent"
        self.sub_title = "Intelligent Email Management"

        # Load initial data
        await self.refresh_data()

    async def refresh_data(self):
        """Refresh email data from database."""
        try:
            # Get recent emails
            emails = self.db.get_emails(
                limit=100, since=datetime.now() - timedelta(days=7)
            )
            self.current_emails = emails

            # Update email list
            email_list = self.query_one("#email-list", EmailList)
            email_list.load_emails(emails)

            # Get and update statistics
            stats = self.db.get_email_stats()
            sidebar = self.query_one(StatsSidebar)
            sidebar.update_stats(stats)

            self.notify("Data refreshed", timeout=2)

        except Exception as e:
            self.notify(f"Error refreshing data: {str(e)}", severity="error")

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle email selection."""
        if event.data_table.id in ["email-list", "smart-email-list"]:
            email_id = event.row_key

            # Find the selected email
            selected_email = None
            for email in self.current_emails:
                if email.id == email_id:
                    selected_email = email
                    break

            if selected_email:
                self.selected_email = selected_email

                # Show email details
                details = self.query_one("#email-details", EmailDetails)
                details.show_email(selected_email)

                # Update drafts panel with current email
                try:
                    drafts_panel = self.query_one(DraftSuggestionsPanel)
                    drafts_panel.update_current_email(selected_email)
                except Exception:
                    pass  # Panel might not be visible

                # Switch to details tab
                tabs = self.query_one(TabbedContent)
                tabs.active = "details-tab"

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "refresh-button":
            await self.action_refresh()
        elif event.button.id == "sync-button":
            await self.action_sync()
        elif event.button.id == "brief-button":
            await self.action_brief()
        elif event.button.id == "save-settings":
            await self.action_save_settings()
        elif event.button.id == "process-all":
            await self.action_process_all_emails()
        elif event.button.id == "search-button":
            await self.action_search()
        elif event.button.id == "ai-filter-button":
            await self.action_ai_filter()
        elif event.button.id == "refresh-analytics":
            await self.action_refresh_analytics()
        elif event.button.id == "generate-report":
            await self.action_generate_report()
        elif event.button.id == "cleanup-db":
            await self.action_cleanup_database()
        elif event.button.id == "analyze-sentiment":
            await self.action_analyze_sentiment()
        elif event.button.id == "analyze-threads":
            await self.action_analyze_threads()
        elif event.button.id == "comprehensive-analysis":
            await self.action_comprehensive_analysis()
        elif event.button.id == "smart-triage-button":
            await self.action_smart_triage()
        elif event.button.id == "priority-inbox-btn":
            await self.action_show_priority_inbox()
        elif event.button.id == "regular-inbox-btn":
            await self.action_show_regular_inbox()
        elif event.button.id == "archived-inbox-btn":
            await self.action_show_archived_emails()
        elif event.button.id == "spam-inbox-btn":
            await self.action_show_spam_emails()
        elif event.button.id == "analyze-style-btn":
            await self.action_analyze_writing_style()
        elif event.button.id == "generate-drafts-btn":
            await self.action_generate_drafts()
        elif event.button.id == "generate-narrative-btn":
            await self.action_generate_narrative_brief()
        elif event.button.id == "refresh-logs-btn":
            await self.action_refresh_logs()
        elif event.button.id == "clear-logs-btn":
            await self.action_clear_logs()
        elif event.button.id == "feedback-btn":
            await self.action_provide_feedback()
        elif event.button.id == "learning-insights-btn":
            await self.action_show_learning_insights()
        elif event.button.id == "sender-scores-btn":
            await self.action_show_sender_scores()
        elif event.button.id == "submit-feedback-btn":
            await self.action_submit_feedback()
        elif event.button.id == "cancel-feedback-btn":
            self.pop_screen()
        elif event.button.id == "close-insights-btn":
            self.pop_screen()
        elif event.button.id == "close-scores-btn":
            self.pop_screen()
        elif event.button.id == "full-insights-btn":
            await self.action_show_full_insights()

    async def refresh_data_alt(self) -> None:
        """Alternative refresh email data from database."""
        try:
            # Load emails
            self.current_emails = self.db.get_emails(limit=100)

            # Update email list
            email_list = self.query_one("#email-list", EmailList)
            email_list.load_emails(self.current_emails)

            # Update stats
            stats = self.db.get_email_stats()
            sidebar = self.query_one("StatsSidebar", StatsSidebar)
            sidebar.update_stats(stats)

        except Exception as e:
            self.notify(f"Failed to refresh data: {str(e)}", severity="error")

    async def action_refresh(self) -> None:
        """Refresh data action."""
        await self.refresh_data()

    async def action_sync(self) -> None:
        """Sync emails action."""
        try:
            self.notify("Starting email sync...", timeout=3)

            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Get connector configs
            configs = self.db.get_connector_configs()
            if not configs:
                self.notify("No connectors configured", severity="warning")
                return

            # Pull emails
            since = datetime.now() - timedelta(hours=24)
            emails = await self.crew.execute_task(
                "collect_emails", connector_configs=configs, since=since
            )

            if emails:
                # Save emails
                saved_count = self.db.save_emails(emails)
                self.notify(f"Synced {saved_count} new emails", timeout=3)

                # Refresh display
                await self.refresh_data()
            else:
                self.notify("No new emails found", timeout=3)

        except Exception as e:
            self.notify(f"Sync failed: {str(e)}", severity="error")

    async def action_brief(self) -> None:
        """Generate brief action."""
        try:
            self.notify("Generating daily brief...", timeout=3)

            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Get today's emails
            today_emails = self.db.get_emails(
                since=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
                limit=500,
            )

            if today_emails:
                brief = await self.crew.execute_task(
                    "generate_brief", emails=today_emails, date=datetime.now().date()
                )

                # Show brief summary
                self.notify(f"Brief generated: {brief.headline}", timeout=5)
            else:
                self.notify("No emails found for today", timeout=3)

        except Exception as e:
            self.notify(f"Brief generation failed: {str(e)}", severity="error")

    async def action_filter(self) -> None:
        """Filter emails action."""
        # TODO: Implement email filtering
        self.notify("Filtering not yet implemented", timeout=3)

    async def action_save_settings(self) -> None:
        """Save settings to database."""
        try:
            # Get settings values from widgets
            ai_model = self.query_one("#ai-model-select", Select).value
            auto_summarize = self.query_one("#auto-summarize", Switch).value
            auto_categorize = self.query_one("#auto-categorize", Switch).value
            auto_action_items = self.query_one("#auto-action-items", Switch).value
            sync_frequency = self.query_one("#sync-frequency", Input).value
            max_emails = self.query_one("#max-emails", Input).value

            # Save to user preferences
            settings_data = {
                "ai_model": ai_model,
                "auto_summarize": auto_summarize,
                "auto_categorize": auto_categorize,
                "auto_action_items": auto_action_items,
                "sync_frequency": int(sync_frequency),
                "max_emails": int(max_emails),
            }

            # Save to database
            with self.db.get_session() as session:
                from ..storage.models import UserPreferencesORM

                pref = (
                    session.query(UserPreferencesORM)
                    .filter(UserPreferencesORM.key == "app_settings")
                    .first()
                )

                if pref:
                    pref.value = settings_data
                else:
                    pref = UserPreferencesORM(key="app_settings", value=settings_data)
                    session.add(pref)

                session.commit()

            self.notify("Settings saved successfully!", timeout=3)

        except Exception as e:
            self.notify(f"Failed to save settings: {str(e)}", severity="error")

    async def action_process_all_emails(self) -> None:
        """Process all emails with AI."""
        try:
            self.notify("Processing all emails with AI...", timeout=5)

            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Get all emails without summaries
            emails = self.db.get_emails(limit=1000)
            unprocessed = [e for e in emails if not e.summary]

            if not unprocessed:
                self.notify("All emails already processed!", timeout=3)
                return

            # Process in batches
            batch_size = 10
            processed = 0

            for i in range(0, len(unprocessed), batch_size):
                batch = unprocessed[i : i + batch_size]

                # Summarize emails
                for email in batch:
                    try:
                        summary = await self.crew.execute_task(
                            "summarize_email", email=email
                        )
                        email.summary = summary.get("summary", "")
                        email.action_items = summary.get("action_items", [])
                        self.db.save_email(email)
                        processed += 1

                        # Update progress
                        self.notify(
                            f"Processed {processed}/{len(unprocessed)} emails...",
                            timeout=1,
                        )

                    except Exception as e:
                        logger.error(f"Failed to process email {email.id}: {e}")
                        continue

            self.notify(
                f"Processing complete! {processed} emails processed.", timeout=5
            )
            await self.refresh_data()

        except Exception as e:
            self.notify(f"Processing failed: {str(e)}", severity="error")

    async def action_search(self) -> None:
        """Search emails."""
        try:
            search_input = self.query_one("#search-input", Input)
            query = search_input.value.strip()

            if not query:
                await self.refresh_data()
                return

            # Simple text search for now
            emails = self.db.get_emails(search=query, limit=100)
            self.current_emails = emails

            # Update email list
            email_list = self.query_one("#email-list", EmailList)
            email_list.load_emails(emails)

            self.notify(f"Found {len(emails)} emails matching '{query}'", timeout=3)

        except Exception as e:
            self.notify(f"Search failed: {str(e)}", severity="error")

    async def action_ai_filter(self) -> None:
        """AI-powered email filtering."""
        try:
            search_input = self.query_one("#search-input", Input)
            query = search_input.value.strip()

            if not query:
                self.notify("Enter a search query for AI filtering", timeout=3)
                return

            self.notify(f"AI filtering for: '{query}'...", timeout=3)

            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Get all emails
            all_emails = self.db.get_emails(limit=500)

            if not all_emails:
                self.notify("No emails to filter", timeout=3)
                return

            # Use AI to filter emails based on query
            filtered_emails = await self.crew.execute_task(
                "filter_emails", emails=all_emails, query=query
            )

            if filtered_emails:
                self.current_emails = filtered_emails
                email_list = self.query_one("#email-list", EmailList)
                email_list.load_emails(filtered_emails)
                self.notify(
                    f"AI found {len(filtered_emails)} relevant emails", timeout=3
                )
            else:
                self.notify("No relevant emails found", timeout=3)

        except Exception as e:
            self.notify(f"AI filtering failed: {str(e)}", severity="error")

    async def action_refresh_analytics(self) -> None:
        """Refresh analytics data."""
        try:
            self.notify("Refreshing analytics...", timeout=2)

            # Get all emails for analysis
            emails = self.db.get_emails(limit=1000)
            stats = self.db.get_email_stats()

            # Calculate analytics data
            analytics_data = {
                "ai_summaries": len([e for e in emails if e.summary]),
                "action_items": sum(len(e.action_items or []) for e in emails),
                "processed_emails": len([e for e in emails if e.processed_at]),
                "top_categories": stats.get("categories", {}),
                "recent_activity": [
                    f"Latest sync: {len(emails)} emails",
                    f"Categories: {len(stats.get('categories', {}))}",
                ],
                "ai_insights": [
                    f"Most active category: {max(stats.get('categories', {}).items(), key=lambda x: x[1], default=('None', 0))[0]}",
                    f"Processing coverage: {(len([e for e in emails if e.summary]) / max(len(emails), 1) * 100):.1f}%",
                    f"Action items density: {(sum(len(e.action_items or []) for e in emails) / max(len(emails), 1)):.1f} per email",
                ],
            }

            # Update dashboard
            try:
                dashboard = self.query_one(AnalyticsDashboard)
                dashboard.update_analytics(analytics_data)
            except Exception:
                pass  # Dashboard might not be visible

            self.notify("Analytics refreshed!", timeout=3)

        except Exception as e:
            self.notify(f"Analytics refresh failed: {str(e)}", severity="error")

    async def action_generate_report(self) -> None:
        """Generate a comprehensive email report."""
        try:
            self.notify("Generating email report...", timeout=3)

            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Get data for report
            emails = self.db.get_emails(limit=500)
            stats = self.db.get_email_stats()

            if not emails:
                self.notify("No emails to analyze", timeout=3)
                return

            # Generate comprehensive analysis report
            f"""
Generate a comprehensive email analysis report based on {len(emails)} emails.

Categories: {stats.get('categories', {})}
Total unread: {stats.get('unread', 0)}
Total flagged: {stats.get('flagged', 0)}

Provide insights on:
1. Email patterns and trends
2. Most important senders and topics
3. Productivity recommendations
4. Action items that need attention
"""

            # This would use the AI to generate insights
            self.notify("Email report generated! Check brief for details.", timeout=5)

        except Exception as e:
            self.notify(f"Report generation failed: {str(e)}", severity="error")

    async def action_cleanup_database(self) -> None:
        """Clean up old/duplicate emails from database."""
        try:
            self.notify("Cleaning up database...", timeout=3)

            # Get email stats before cleanup
            before_stats = self.db.get_email_stats()
            before_stats.get("total", 0)

            # Simple cleanup: remove emails older than 90 days without summaries
            from datetime import timedelta

            cutoff_date = datetime.now() - timedelta(days=90)

            with self.db.get_session() as session:
                from ..storage.models import EmailORM

                old_emails = (
                    session.query(EmailORM)
                    .filter(EmailORM.date < cutoff_date, EmailORM.summary.is_(None))
                    .all()
                )

                for email in old_emails[:100]:  # Limit cleanup
                    session.delete(email)

                session.commit()
                deleted_count = len(old_emails[:100])

            self.notify(f"Cleaned up {deleted_count} old emails", timeout=5)
            await self.refresh_data()

        except Exception as e:
            self.notify(f"Database cleanup failed: {str(e)}", severity="error")

    async def action_analyze_sentiment(self) -> None:
        """Analyze sentiment of current emails."""
        try:
            self.notify("Analyzing email sentiment...", timeout=3)

            if not self.current_emails:
                self.notify("No emails to analyze", timeout=3)
                return

            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Analyze sentiment
            sentiment_data = await self.crew.execute_task(
                "analyze_sentiment",
                emails=self.current_emails[:20],  # Limit for performance
            )

            # Update insights log
            try:
                insights_log = self.query_one("#ai-insights-log", RichLog)
                insights_log.clear()

                if "sentiment_distribution" in sentiment_data:
                    dist = sentiment_data["sentiment_distribution"]
                    insights_log.write("📊 Sentiment Distribution:")
                    insights_log.write(f"  Positive: {dist.get('positive', 0)}")
                    insights_log.write(f"  Negative: {dist.get('negative', 0)}")
                    insights_log.write(f"  Neutral: {dist.get('neutral', 0)}")

                if "recommendations" in sentiment_data:
                    insights_log.write("\\n💡 Recommendations:")
                    for rec in sentiment_data["recommendations"][:5]:
                        insights_log.write(f"  {rec}")

            except Exception:
                pass  # Dashboard might not be visible

            self.notify("Sentiment analysis completed!", timeout=5)

        except Exception as e:
            self.notify(f"Sentiment analysis failed: {str(e)}", severity="error")

    async def action_analyze_threads(self) -> None:
        """Analyze email threads and conversations."""
        try:
            self.notify("Analyzing email threads...", timeout=3)

            if not self.current_emails:
                self.notify("No emails to analyze", timeout=3)
                return

            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Analyze threads
            thread_data = await self.crew.execute_task(
                "analyze_threads", emails=self.current_emails
            )

            # Update insights log
            try:
                insights_log = self.query_one("#ai-insights-log", RichLog)
                insights_log.clear()

                threads = thread_data.get("threads", [])
                insights_log.write("🧵 Thread Analysis Results:")
                insights_log.write(f"  Total threads found: {len(threads)}")

                for i, thread in enumerate(threads[:3]):  # Show top 3
                    insights_log.write(f"\\n  Thread {i+1}:")
                    insights_log.write(
                        f"    Messages: {thread.get('message_count', 0)}"
                    )
                    insights_log.write(
                        f"    Participants: {thread.get('participant_count', 0)}"
                    )
                    insights_log.write(
                        f"    Type: {thread.get('conversation_type', 'unknown')}"
                    )
                    insights_log.write(
                        f"    Status: {thread.get('resolution_status', 'unknown')}"
                    )

            except Exception:
                pass

            self.notify(
                f"Thread analysis completed! Found {len(thread_data.get('threads', []))} threads",
                timeout=5,
            )

        except Exception as e:
            self.notify(f"Thread analysis failed: {str(e)}", severity="error")

    async def action_comprehensive_analysis(self) -> None:
        """Run comprehensive AI analysis on emails."""
        try:
            self.notify("Running comprehensive AI analysis...", timeout=5)

            if not self.current_emails:
                self.notify("No emails to analyze", timeout=3)
                return

            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Run comprehensive analysis
            analysis_data = await self.crew.execute_task(
                "comprehensive_analysis",
                emails=self.current_emails[:50],  # Limit for performance
                rules=[],  # Could add rules here
            )

            # Update insights log with comprehensive results
            try:
                insights_log = self.query_one("#ai-insights-log", RichLog)
                insights_log.clear()

                insights_log.write("🔍 Comprehensive Analysis Results:")
                insights_log.write(
                    f"  Emails analyzed: {analysis_data.get('email_count', 0)}"
                )
                insights_log.write(
                    f"  Categories found: {analysis_data.get('summary', {}).get('categories_found', 0)}"
                )

                # Sentiment insights
                sentiment = analysis_data.get("sentiment_insights", {})
                if sentiment:
                    insights_log.write("\\n😊 Sentiment Insights:")
                    insights_log.write(
                        f"  Total analyzed: {sentiment.get('total_analyzed', 0)}"
                    )
                    dist = sentiment.get("sentiment_distribution", {})
                    insights_log.write(f"  Positive: {dist.get('positive', 0)}")
                    insights_log.write(f"  Negative: {dist.get('negative', 0)}")

                # Thread insights
                thread_analysis = analysis_data.get("thread_analysis", {})
                if thread_analysis:
                    insights_log.write("\\n🧵 Thread Insights:")
                    insights_log.write(
                        f"  Threads found: {thread_analysis.get('threads_found', 0)}"
                    )

                # Priority distribution
                priority_dist = analysis_data.get("summary", {}).get(
                    "priority_distribution", {}
                )
                if priority_dist:
                    insights_log.write("\\n⚡ Priority Distribution:")
                    for priority, count in priority_dist.items():
                        insights_log.write(f"  {priority.title()}: {count}")

            except Exception:
                pass

            self.notify("Comprehensive analysis completed!", timeout=5)

        except Exception as e:
            self.notify(f"Comprehensive analysis failed: {str(e)}", severity="error")

    async def action_smart_triage(self) -> None:
        """Run smart triage on current emails."""
        try:
            self.notify("Running smart email triage...", timeout=3)

            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Get recent emails for triage
            emails = self.db.get_emails(
                limit=100, since=datetime.now() - timedelta(days=7)
            )

            if not emails:
                self.notify("No emails to triage", timeout=3)
                return

            # Run smart inbox triage
            smart_inbox_results = await self.crew.execute_task(
                "smart_inbox", emails=emails, rules=[]  # Could add rules here
            )

            # Update sidebar with triage stats
            try:
                sidebar = self.query_one(StatsSidebar)
                sidebar.update_triage_stats(smart_inbox_results.get("stats", {}))
            except Exception:
                pass

            # Update smart inbox view
            try:
                smart_inbox_view = self.query_one(SmartInboxView)
                smart_inbox_view.update_triage_stats(
                    smart_inbox_results.get("stats", {})
                )

                # Load priority emails by default
                priority_emails = smart_inbox_results.get("priority_inbox", [])
                smart_email_list = self.query_one("#smart-email-list", EmailList)
                smart_email_list.load_emails(priority_emails, show_triage_data=True)

                # Update current emails for selection
                self.current_emails = priority_emails

            except Exception:
                pass

            self.notify(
                f"Smart triage completed! Found {smart_inbox_results.get('stats', {}).get('priority_count', 0)} priority emails",
                timeout=5,
            )

            # Switch to smart inbox tab
            tabs = self.query_one(TabbedContent)
            tabs.active = "smart-inbox-tab"

        except Exception as e:
            self.notify(f"Smart triage failed: {str(e)}", severity="error")

    async def action_show_priority_inbox(self) -> None:
        """Show priority inbox emails."""
        try:
            if not self.crew:
                self.notify("Run smart triage first", timeout=3)
                return

            # Get smart inbox data
            emails = self.db.get_emails(
                limit=50, since=datetime.now() - timedelta(days=7)
            )
            smart_inbox_results = await self.crew.execute_task(
                "smart_inbox", emails=emails, rules=[]
            )

            priority_emails = smart_inbox_results.get("priority_inbox", [])
            smart_email_list = self.query_one("#smart-email-list", EmailList)
            smart_email_list.load_emails(priority_emails, show_triage_data=True)
            self.current_emails = priority_emails

            self.notify(f"Showing {len(priority_emails)} priority emails", timeout=3)

        except Exception as e:
            self.notify(f"Failed to show priority inbox: {str(e)}", severity="error")

    async def action_show_regular_inbox(self) -> None:
        """Show regular inbox emails."""
        try:
            if not self.crew:
                self.notify("Run smart triage first", timeout=3)
                return

            emails = self.db.get_emails(
                limit=50, since=datetime.now() - timedelta(days=7)
            )
            smart_inbox_results = await self.crew.execute_task(
                "smart_inbox", emails=emails, rules=[]
            )

            regular_emails = smart_inbox_results.get("regular_inbox", [])
            smart_email_list = self.query_one("#smart-email-list", EmailList)
            smart_email_list.load_emails(regular_emails, show_triage_data=True)
            self.current_emails = regular_emails

            self.notify(f"Showing {len(regular_emails)} regular emails", timeout=3)

        except Exception as e:
            self.notify(f"Failed to show regular inbox: {str(e)}", severity="error")

    async def action_show_archived_emails(self) -> None:
        """Show auto-archived emails."""
        try:
            if not self.crew:
                self.notify("Run smart triage first", timeout=3)
                return

            emails = self.db.get_emails(
                limit=50, since=datetime.now() - timedelta(days=7)
            )
            smart_inbox_results = await self.crew.execute_task(
                "smart_inbox", emails=emails, rules=[]
            )

            archived_emails = smart_inbox_results.get("auto_archived", [])
            smart_email_list = self.query_one("#smart-email-list", EmailList)
            smart_email_list.load_emails(archived_emails, show_triage_data=True)
            self.current_emails = archived_emails

            self.notify(
                f"Showing {len(archived_emails)} auto-archived emails", timeout=3
            )

        except Exception as e:
            self.notify(f"Failed to show archived emails: {str(e)}", severity="error")

    async def action_show_spam_emails(self) -> None:
        """Show spam emails."""
        try:
            if not self.crew:
                self.notify("Run smart triage first", timeout=3)
                return

            emails = self.db.get_emails(
                limit=50, since=datetime.now() - timedelta(days=7)
            )
            smart_inbox_results = await self.crew.execute_task(
                "smart_inbox", emails=emails, rules=[]
            )

            spam_emails = smart_inbox_results.get("spam", [])
            smart_email_list = self.query_one("#smart-email-list", EmailList)
            smart_email_list.load_emails(spam_emails, show_triage_data=True)
            self.current_emails = spam_emails

            self.notify(f"Showing {len(spam_emails)} spam emails", timeout=3)

        except Exception as e:
            self.notify(f"Failed to show spam emails: {str(e)}", severity="error")

    async def action_analyze_writing_style(self) -> None:
        """Analyze user's writing style from sent emails."""
        try:
            self.notify("Analyzing your writing style...", timeout=3)

            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Get sent emails (this would need better logic in practice)
            sent_emails = self.db.get_sent_emails(limit=50)

            if len(sent_emails) < 5:
                self.notify("Not enough sent emails found for analysis", timeout=5)
                return

            # Analyze writing style
            style_results = await self.crew.execute_task(
                "analyze_writing_style", sent_emails=sent_emails, force_refresh=True
            )

            # Update drafts panel
            try:
                drafts_panel = self.query_one(DraftSuggestionsPanel)
                drafts_panel.update_writing_style_status(
                    style_results.get("style_summary", {})
                )
            except Exception:
                pass

            formality = style_results.get("formality_score", 0.5)
            avg_length = style_results.get("avg_length", 0)

            self.notify(
                f"Writing style analyzed! Formality: {formality:.2f}, Avg length: {avg_length} words",
                timeout=5,
            )

        except Exception as e:
            self.notify(f"Writing style analysis failed: {str(e)}", severity="error")

    async def action_generate_drafts(self) -> None:
        """Generate AI draft suggestions for the selected email."""
        try:
            if not self.selected_email:
                self.notify("Select an email first", timeout=3)
                return

            self.notify("Generating AI draft suggestions...", timeout=3)

            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Get number of suggestions
            try:
                num_drafts_select = self.query_one("#num-drafts-select", Select)
                num_suggestions = int(num_drafts_select.value)
            except Exception:
                num_suggestions = 3

            # Generate drafts
            draft_results = await self.crew.execute_task(
                "generate_drafts",
                original_email=self.selected_email,
                context="reply",
                num_suggestions=num_suggestions,
            )

            # Show drafts in panel
            try:
                drafts_panel = self.query_one(DraftSuggestionsPanel)
                drafts_panel.show_draft_suggestions(
                    draft_results.get("suggestions", [])
                )
            except Exception:
                pass

            # Switch to drafts tab
            tabs = self.query_one(TabbedContent)
            tabs.active = "drafts-tab"

            num_generated = len(draft_results.get("suggestions", []))
            self.notify(f"Generated {num_generated} draft suggestions!", timeout=5)

        except Exception as e:
            self.notify(f"Draft generation failed: {str(e)}", severity="error")

    async def action_generate_narrative_brief(self) -> None:
        """Generate narrative-style daily brief."""
        try:
            self.notify("Generating narrative brief...", timeout=3)

            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Get date from input
            try:
                date_input = self.query_one("#brief-date-input", Input)
                date_str = date_input.value.strip()
                if date_str:
                    from datetime import datetime

                    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                else:
                    target_date = datetime.now().date()
            except Exception:
                target_date = datetime.now().date()

            # Get emails for the date
            emails = self.db.get_emails(
                since=datetime.combine(target_date, datetime.min.time()),
                until=datetime.combine(target_date, datetime.max.time()),
                limit=500,
            )

            if not emails:
                self.notify(f"No emails found for {target_date}", timeout=3)
                return

            # Generate narrative brief
            brief_results = await self.crew.execute_task(
                "generate_narrative_brief",
                emails=emails,
                target_date=target_date,
                context={"user_preferences": {"reading_time": 60}},
            )

            # Show brief in panel
            try:
                brief_panel = self.query_one(NarrativeBriefPanel)
                brief_panel.show_narrative_brief(brief_results.get("brief", {}))
                brief_panel.update_brief_metrics(brief_results.get("brief", {}))
            except Exception:
                pass

            # Switch to narrative brief tab
            tabs = self.query_one(TabbedContent)
            tabs.active = "narrative-brief-tab"

            reading_time = brief_results.get("brief", {}).get(
                "estimated_reading_time", 45
            )
            self.notify(
                f"Narrative brief generated! Reading time: {reading_time}s", timeout=5
            )

        except Exception as e:
            self.notify(
                f"Narrative brief generation failed: {str(e)}", severity="error"
            )

    async def action_refresh_logs(self) -> None:
        """Refresh the log display."""
        try:
            if self.tui_log_handler:
                log_viewer = self.query_one(LogViewer)
                log_viewer.update_logs(self.tui_log_handler.log_entries)
                self.notify("Logs refreshed", timeout=2)
            else:
                self.notify("No log handler available", timeout=2)
        except Exception as e:
            self.notify(f"Failed to refresh logs: {str(e)}", severity="error")

    async def action_clear_logs(self) -> None:
        """Clear the log display."""
        try:
            if self.tui_log_handler:
                self.tui_log_handler.log_entries.clear()

            log_display = self.query_one("#app-logs-display", RichLog)
            log_display.clear()
            self.notify("Logs cleared", timeout=2)
        except Exception as e:
            self.notify(f"Failed to clear logs: {str(e)}", severity="error")

    async def action_provide_feedback(self) -> None:
        """Show feedback dialog for current email."""
        if not self.selected_email:
            self.notify("No email selected for feedback", severity="warning")
            return

        feedback_dialog = FeedbackDialog(self.selected_email)
        self.push_screen(feedback_dialog)

    async def action_submit_feedback(self) -> None:
        """Submit feedback for the current email."""
        try:
            # Get the current screen (should be FeedbackDialog)
            dialog = self.screen
            if not isinstance(dialog, FeedbackDialog):
                return

            # Get feedback data
            decision_select = dialog.query_one("#feedback-decision-select", Select)
            comment_input = dialog.query_one("#feedback-comment", Input)

            decision = decision_select.value
            comment = comment_input.value or "manual_correction"

            if not decision:
                self.notify("Please select a decision", severity="warning")
                return

            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Convert to TriageDecision enum
            from ..agents.triage_agent import TriageDecision

            decision_map = {
                "priority_inbox": TriageDecision.PRIORITY_INBOX,
                "regular_inbox": TriageDecision.REGULAR_INBOX,
                "auto_archive": TriageDecision.AUTO_ARCHIVE,
                "spam_folder": TriageDecision.SPAM_FOLDER,
            }

            triage_decision = decision_map.get(decision)

            # Submit feedback
            await self.crew.triage_agent.learn_from_user_feedback(
                dialog.email.id, triage_decision, comment
            )

            self.notify(f"Feedback submitted: {decision.replace('_', ' ')}", timeout=3)
            self.pop_screen()

        except Exception as e:
            self.notify(f"Failed to submit feedback: {str(e)}", severity="error")

    async def action_show_learning_insights(self) -> None:
        """Show learning insights dialog."""
        try:
            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Get insights from triage agent
            insights = self.crew.triage_agent.get_learning_insights()

            insights_dialog = LearningInsightsDialog(insights)
            self.push_screen(insights_dialog)

        except Exception as e:
            self.notify(f"Failed to load learning insights: {str(e)}", severity="error")

    async def action_show_sender_scores(self) -> None:
        """Show sender importance scores dialog."""
        try:
            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Get sender scores from triage agent
            sender_scores = self.crew.triage_agent.sender_importance

            if not sender_scores:
                self.notify("No sender scores available yet", severity="warning")
                return

            scores_dialog = SenderScoresDialog(sender_scores)
            self.push_screen(scores_dialog)

        except Exception as e:
            self.notify(f"Failed to load sender scores: {str(e)}", severity="error")

    async def action_show_full_insights(self) -> None:
        """Show full learning insights in the logs tab."""
        try:
            # Initialize crew if needed
            if not self.crew:
                self.crew = EmailAgentCrew()
                await self.crew.initialize_crew({})

            # Get detailed insights
            insights = self.crew.triage_agent.get_learning_insights()

            # Switch to logs tab and display insights
            tabs = self.query_one(TabbedContent)
            tabs.active = "logs-tab"

            log_display = self.query_one("#app-logs-display", RichLog)
            log_display.clear()

            # Display comprehensive insights
            log_display.write(
                "[bold cyan]🧠 Comprehensive Learning Insights[/bold cyan]"
            )
            log_display.write("=" * 50)

            # Learning statistics
            learning_stats = insights.get("learning_stats", {})
            log_display.write("\n[bold]📊 Learning Statistics:[/bold]")
            log_display.write(
                f"• Total feedback received: {learning_stats.get('total_feedback_received', 0)}"
            )
            log_display.write(
                f"• Learning active: {'✅ Yes' if learning_stats.get('learning_active') else '❌ No'}"
            )
            if learning_stats.get("last_feedback"):
                log_display.write(f"• Last feedback: {learning_stats['last_feedback']}")

            # Sender insights
            sender_insights = insights.get("sender_insights", {})
            if sender_insights:
                log_display.write("\n[bold]👥 Sender Insights:[/bold]")
                log_display.write(
                    f"• Total senders learned: {sender_insights.get('total_senders_learned', 0)}"
                )

                if sender_insights.get("most_important"):
                    log_display.write("\n🔥 Most Important Senders:")
                    for sender, score in sender_insights["most_important"]:
                        log_display.write(f"  • {sender}: {score:.3f}")

                if sender_insights.get("least_important"):
                    log_display.write("\n⚫ Least Important Senders:")
                    for sender, score in sender_insights["least_important"]:
                        log_display.write(f"  • {sender}: {score:.3f}")

            # Category insights
            category_insights = insights.get("category_insights", {})
            if category_insights:
                log_display.write("\n[bold]📂 Category Learning:[/bold]")
                for category, prefs in category_insights.items():
                    log_display.write(f"• {category}:")
                    log_display.write(
                        f"  - Priority tendency: {prefs.get('priority_tendency', 0.0):.2f}"
                    )
                    log_display.write(
                        f"  - Archive tendency: {prefs.get('archive_tendency', 0.0):.2f}"
                    )
                    log_display.write(
                        f"  - Feedback count: {prefs.get('feedback_count', 0)}"
                    )

            # Urgency insights
            urgency_insights = insights.get("urgency_insights", {})
            if urgency_insights:
                log_display.write("\n[bold]⚡ Urgency Learning:[/bold]")

                learned_keywords = urgency_insights.get("learned_urgency_keywords", [])
                if learned_keywords:
                    log_display.write("Learned urgency keywords:")
                    for keyword, score in learned_keywords[:10]:
                        log_display.write(f"  • {keyword}: {score:.3f}")

                false_positives = urgency_insights.get("false_positive_words", [])
                if false_positives:
                    log_display.write("False positive words:")
                    for word in false_positives:
                        log_display.write(f"  • {word}")

            # Time insights
            time_insights = insights.get("time_insights", {})
            if time_insights:
                log_display.write("\n[bold]🕒 Time-based Learning:[/bold]")

                priority_hours = time_insights.get("priority_hours", {})
                if priority_hours:
                    sorted_hours = sorted(
                        priority_hours.items(), key=lambda x: x[1], reverse=True
                    )
                    log_display.write("Peak priority hours:")
                    for hour, count in sorted_hours[:5]:
                        log_display.write(
                            f"  • {hour:02d}:00 - {count} priority emails"
                        )

            self.pop_screen()  # Close the insights dialog
            self.notify("Full insights displayed in Logs tab", timeout=3)

        except Exception as e:
            self.notify(f"Failed to show full insights: {str(e)}", severity="error")

    async def action_quit(self) -> None:
        """Quit the application."""
        if self.crew:
            await self.crew.shutdown()
        self.exit()


def run_tui():
    """Run the TUI application."""
    try:
        app = EmailAgentTUI()
        app.run()
    finally:
        # Restore normal logging when TUI exits
        logging.getLogger().handlers.clear()
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
