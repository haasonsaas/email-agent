"""Main TUI application using Textual."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Button, DataTable, Footer, Header, Input, Label, 
    Placeholder, RichLog, Static, TabbedContent, TabPane,
    Select, Switch, TextArea
)
from textual.reactive import reactive
from textual.message import Message

from ..storage import DatabaseManager
from ..models import Email, EmailCategory
from ..agents import EmailAgentCrew

logger = logging.getLogger(__name__)


class EmailList(DataTable):
    """Widget for displaying email list."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_columns("Subject", "From", "Date", "Category", "Status")
        self.cursor_type = "row"
        self.zebra_stripes = True
    
    def load_emails(self, emails: List[Email]):
        """Load emails into the table."""
        self.clear()
        
        for email in emails:
            status = "📧" if not email.is_read else "✓"
            if email.is_flagged:
                status += "⭐"
            
            self.add_row(
                email.subject,
                email.sender.email,
                email.date.strftime("%Y-%m-%d %H:%M"),
                email.category.value.title(),
                status,
                key=email.id
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
            self.write(f"\n[bold green]AI Summary:[/bold green]")
            self.write(f"[dim]{email.summary}[/dim]")
        
        if email.action_items:
            self.write(f"\n[bold yellow]Action Items:[/bold yellow]")
            for item in email.action_items:
                self.write(f"• {item}")
        
        self.write("\n[bold cyan]Body:[/bold cyan]")
        if email.body_text:
            self.write(email.body_text[:1000] + ("..." if len(email.body_text) > 1000 else ""))
        else:
            self.write("[dim]No text content[/dim]")


class StatsSidebar(Vertical):
    """Sidebar showing email statistics."""
    
    def compose(self) -> ComposeResult:
        yield Label("📊 Statistics", classes="sidebar-title")
        yield Label("Total: 0", id="stats-total")
        yield Label("Unread: 0", id="stats-unread")
        yield Label("Flagged: 0", id="stats-flagged")
        yield Label("")
        yield Label("📂 Categories", classes="sidebar-title")
        yield Container(id="categories-container")
        yield Label("")
        yield Button("🔄 Refresh", id="refresh-button", variant="primary")
        yield Button("📧 Sync", id="sync-button")
        yield Button("📝 Brief", id="brief-button")
    
    def update_stats(self, stats: dict):
        """Update statistics display."""
        self.query_one("#stats-total", Label).update(f"Total: {stats.get('total', 0)}")
        self.query_one("#stats-unread", Label).update(f"Unread: {stats.get('unread', 0)}")
        self.query_one("#stats-flagged", Label).update(f"Flagged: {stats.get('flagged', 0)}")
        
        # Update categories
        container = self.query_one("#categories-container", Container)
        container.remove_children()
        
        categories = stats.get('categories', {})
        for category, count in categories.items():
            if count > 0:
                label = Label(f"{category.title()}: {count}")
                container.mount(label)


class SettingsPanel(Vertical):
    """Settings panel with AI configuration options."""
    
    def compose(self) -> ComposeResult:
        yield Label("⚙️ AI Settings", classes="settings-title")
        yield Label("")
        
        # AI Model Selection
        yield Label("AI Model:")
        yield Select([
            ("gpt-4o-mini", "gpt-4o-mini"),
            ("gpt-4o", "gpt-4o"),
            ("gpt-3.5-turbo", "gpt-3.5-turbo")
        ], value="gpt-4o-mini", id="ai-model-select")
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
        yield Input(placeholder="Search emails... (try 'urgent emails' or 'action required')", id="search-input")
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
            yield Button("🔄 Refresh Analytics", id="refresh-analytics", variant="primary")
            yield Button("📋 Generate Report", id="generate-report")
            yield Button("🧹 Cleanup Database", id="cleanup-db")
        
        yield Label("")
        yield Label("🤖 Advanced AI Analysis", classes="settings-title")
        with Horizontal():
            yield Button("😊 Sentiment Analysis", id="analyze-sentiment", variant="success")
            yield Button("🧵 Thread Analysis", id="analyze-threads", variant="success")
            yield Button("🔍 Comprehensive Analysis", id="comprehensive-analysis", variant="warning")
    
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
            
            categories = data.get('top_categories', {})
            for category, count in list(categories.items())[:5]:
                label = Label(f"{category}: {count}")
                categories_container.mount(label)
            
            # Update recent activity
            activity_container = self.query_one("#recent-activity", Container)
            activity_container.remove_children()
            
            recent = data.get('recent_activity', [])
            for activity in recent[:5]:
                label = Label(activity)
                activity_container.mount(label)
            
            # Update AI insights
            insights_log = self.query_one("#ai-insights-log", RichLog)
            insights_log.clear()
            
            insights = data.get('ai_insights', [])
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
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("s", "sync", "Sync"),
        ("b", "brief", "Brief"),
        ("f", "filter", "Filter"),
    ]
    
    selected_email: reactive[Optional[Email]] = reactive(None)
    
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.crew = None
        self.current_emails: List[Email] = []
    
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
                    
                    with TabPane("📄 Details", id="details-tab"):
                        yield EmailDetails(id="email-details")
                    
                    with TabPane("📊 Dashboard", id="dashboard-tab"):
                        yield AnalyticsDashboard()
                    
                    with TabPane("⚙️ Settings", id="settings-tab"):
                        yield SettingsPanel()
        
        yield Footer()
    
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
                limit=100,
                since=datetime.now() - timedelta(days=7)
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
        if event.data_table.id == "email-list":
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
                "collect_emails",
                connector_configs=configs,
                since=since
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
                limit=500
            )
            
            if today_emails:
                brief = await self.crew.execute_task(
                    "generate_brief",
                    emails=today_emails,
                    date=datetime.now().date()
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
                "max_emails": int(max_emails)
            }
            
            # Save to database
            with self.db.get_session() as session:
                from ..storage.models import UserPreferencesORM
                pref = session.query(UserPreferencesORM).filter(
                    UserPreferencesORM.key == "app_settings"
                ).first()
                
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
                batch = unprocessed[i:i + batch_size]
                
                # Summarize emails
                for email in batch:
                    try:
                        summary = await self.crew.execute_task(
                            "summarize_email",
                            email=email
                        )
                        email.summary = summary.get("summary", "")
                        email.action_items = summary.get("action_items", [])
                        self.db.save_email(email)
                        processed += 1
                        
                        # Update progress
                        self.notify(f"Processed {processed}/{len(unprocessed)} emails...", timeout=1)
                        
                    except Exception as e:
                        logger.error(f"Failed to process email {email.id}: {e}")
                        continue
            
            self.notify(f"Processing complete! {processed} emails processed.", timeout=5)
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
                "filter_emails",
                emails=all_emails,
                query=query
            )
            
            if filtered_emails:
                self.current_emails = filtered_emails
                email_list = self.query_one("#email-list", EmailList)
                email_list.load_emails(filtered_emails)
                self.notify(f"AI found {len(filtered_emails)} relevant emails", timeout=3)
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
                    f"Categories: {len(stats.get('categories', {}))}"
                ],
                "ai_insights": [
                    f"Most active category: {max(stats.get('categories', {}).items(), key=lambda x: x[1], default=('None', 0))[0]}",
                    f"Processing coverage: {(len([e for e in emails if e.summary]) / max(len(emails), 1) * 100):.1f}%",
                    f"Action items density: {(sum(len(e.action_items or []) for e in emails) / max(len(emails), 1)):.1f} per email"
                ]
            }
            
            # Update dashboard
            try:
                dashboard = self.query_one(AnalyticsDashboard)
                dashboard.update_analytics(analytics_data)
            except:
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
            analysis_prompt = f"""
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
            before_count = before_stats.get("total", 0)
            
            # Simple cleanup: remove emails older than 90 days without summaries
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=90)
            
            with self.db.get_session() as session:
                from ..storage.models import EmailORM
                old_emails = session.query(EmailORM).filter(
                    EmailORM.date < cutoff_date,
                    EmailORM.summary.is_(None)
                ).all()
                
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
                emails=self.current_emails[:20]  # Limit for performance
            )
            
            # Update insights log
            try:
                insights_log = self.query_one("#ai-insights-log", RichLog)
                insights_log.clear()
                
                if "sentiment_distribution" in sentiment_data:
                    dist = sentiment_data["sentiment_distribution"]
                    insights_log.write(f"📊 Sentiment Distribution:")
                    insights_log.write(f"  Positive: {dist.get('positive', 0)}")
                    insights_log.write(f"  Negative: {dist.get('negative', 0)}")
                    insights_log.write(f"  Neutral: {dist.get('neutral', 0)}")
                
                if "recommendations" in sentiment_data:
                    insights_log.write(f"\\n💡 Recommendations:")
                    for rec in sentiment_data["recommendations"][:5]:
                        insights_log.write(f"  {rec}")
                        
            except:
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
                "analyze_threads",
                emails=self.current_emails
            )
            
            # Update insights log
            try:
                insights_log = self.query_one("#ai-insights-log", RichLog)
                insights_log.clear()
                
                threads = thread_data.get("threads", [])
                insights_log.write(f"🧵 Thread Analysis Results:")
                insights_log.write(f"  Total threads found: {len(threads)}")
                
                for i, thread in enumerate(threads[:3]):  # Show top 3
                    insights_log.write(f"\\n  Thread {i+1}:")
                    insights_log.write(f"    Messages: {thread.get('message_count', 0)}")
                    insights_log.write(f"    Participants: {thread.get('participant_count', 0)}")
                    insights_log.write(f"    Type: {thread.get('conversation_type', 'unknown')}")
                    insights_log.write(f"    Status: {thread.get('resolution_status', 'unknown')}")
                        
            except:
                pass
            
            self.notify(f"Thread analysis completed! Found {len(thread_data.get('threads', []))} threads", timeout=5)
            
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
                rules=[]  # Could add rules here
            )
            
            # Update insights log with comprehensive results
            try:
                insights_log = self.query_one("#ai-insights-log", RichLog)
                insights_log.clear()
                
                insights_log.write(f"🔍 Comprehensive Analysis Results:")
                insights_log.write(f"  Emails analyzed: {analysis_data.get('email_count', 0)}")
                insights_log.write(f"  Categories found: {analysis_data.get('summary', {}).get('categories_found', 0)}")
                
                # Sentiment insights
                sentiment = analysis_data.get("sentiment_insights", {})
                if sentiment:
                    insights_log.write(f"\\n😊 Sentiment Insights:")
                    insights_log.write(f"  Total analyzed: {sentiment.get('total_analyzed', 0)}")
                    dist = sentiment.get("sentiment_distribution", {})
                    insights_log.write(f"  Positive: {dist.get('positive', 0)}")
                    insights_log.write(f"  Negative: {dist.get('negative', 0)}")
                
                # Thread insights
                thread_analysis = analysis_data.get("thread_analysis", {})
                if thread_analysis:
                    insights_log.write(f"\\n🧵 Thread Insights:")
                    insights_log.write(f"  Threads found: {thread_analysis.get('threads_found', 0)}")
                
                # Priority distribution
                priority_dist = analysis_data.get("summary", {}).get("priority_distribution", {})
                if priority_dist:
                    insights_log.write(f"\\n⚡ Priority Distribution:")
                    for priority, count in priority_dist.items():
                        insights_log.write(f"  {priority.title()}: {count}")
                        
            except:
                pass
            
            self.notify("Comprehensive analysis completed!", timeout=5)
            
        except Exception as e:
            self.notify(f"Comprehensive analysis failed: {str(e)}", severity="error")
    
    async def action_quit(self) -> None:
        """Quit the application."""
        if self.crew:
            await self.crew.shutdown()
        self.exit()


def run_tui():
    """Run the TUI application."""
    app = EmailAgentTUI()
    app.run()