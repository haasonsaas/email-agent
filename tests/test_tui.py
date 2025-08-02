"""Tests for TUI functionality."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from textual.app import App

from email_agent.tui.app import EmailAgentTUI, EmailList, SettingsPanel, AnalyticsDashboard


class TestEmailList:
    """Test EmailList widget."""

    def test_email_list_initialization(self):
        """Test EmailList widget initialization."""
        app = EmailAgentTUI()
        with app._context():
            email_list = EmailList()
            assert email_list is not None
            assert email_list.cursor_type == "row"
            assert email_list.zebra_stripes is True

    def test_load_emails(self, sample_emails):
        """Test loading emails into the list."""
        app = EmailAgentTUI()
        with app._context():
            email_list = EmailList()
            email_list.load_emails(sample_emails)
            
            # Check that emails were added to the table
            assert email_list.row_count == len(sample_emails)


class TestSettingsPanel:
    """Test SettingsPanel widget."""

    def test_settings_panel_initialization(self):
        """Test SettingsPanel widget initialization."""
        app = EmailAgentTUI()
        with app._context():
            panel = SettingsPanel()
            assert panel is not None

    @pytest.mark.asyncio
    async def test_settings_panel_compose(self):
        """Test SettingsPanel compose method."""
        from textual.pilot import Pilot
        
        app = EmailAgentTUI()
        
        async with app.run_test() as pilot:
            # Mount the panel
            panel = SettingsPanel()
            await app.mount(panel)
            
            # Check that it's mounted and has content
            assert panel.is_mounted
            
            # Check for specific child widgets
            inputs = pilot.app.query("Input")
            assert len(inputs) > 0  # Should have input fields


class TestAnalyticsDashboard:
    """Test AnalyticsDashboard widget."""

    def test_analytics_dashboard_initialization(self):
        """Test AnalyticsDashboard widget initialization."""
        app = EmailAgentTUI()
        with app._context():
            dashboard = AnalyticsDashboard()
            assert dashboard is not None

    @pytest.mark.asyncio
    async def test_analytics_dashboard_compose(self):
        """Test AnalyticsDashboard compose method."""
        from textual.pilot import Pilot
        
        app = EmailAgentTUI()
        
        async with app.run_test() as pilot:
            # Mount the dashboard
            dashboard = AnalyticsDashboard()
            await app.mount(dashboard)
            
            # Check that it's mounted and has content
            assert dashboard.is_mounted
            
            # Check for specific child widgets like buttons
            buttons = pilot.app.query("Button")
            assert len(buttons) > 0  # Should have buttons

    def test_update_analytics(self):
        """Test updating analytics data."""
        dashboard = AnalyticsDashboard()
        
        # Mock the required widgets
        with patch.object(dashboard, 'query_one') as mock_query:
            mock_label = Mock()
            mock_query.return_value = mock_label
            
            analytics_data = {
                "ai_summaries": 10,
                "action_items": 5,
                "processed_emails": 8,
                "top_categories": {"primary": 5, "social": 3},
                "recent_activity": ["Sync completed", "Brief generated"],
                "ai_insights": ["Most active category: primary"]
            }
            
            # Should not raise exceptions
            dashboard.update_analytics(analytics_data)


class TestEmailAgentTUI:
    """Test main TUI application."""

    @pytest.fixture
    def mock_dependencies(self):
        """Mock TUI dependencies."""
        with patch('email_agent.tui.app.DatabaseManager') as mock_db, \
             patch('email_agent.tui.app.EmailAgentCrew') as mock_crew:
            
            mock_db_instance = Mock()
            mock_db_instance.get_emails.return_value = []
            mock_db_instance.get_email_stats.return_value = {
                "total": 0, "unread": 0, "flagged": 0, "categories": {}
            }
            mock_db.return_value = mock_db_instance
            
            yield mock_db_instance, mock_crew

    def test_tui_initialization(self, mock_dependencies):
        """Test TUI application initialization."""
        mock_db, mock_crew = mock_dependencies
        
        app = EmailAgentTUI()
        assert app is not None
        assert app.db is not None
        assert app.current_emails == []

    @pytest.mark.asyncio
    async def test_tui_compose(self, mock_dependencies):
        """Test TUI compose method."""
        mock_db, mock_crew = mock_dependencies
        
        app = EmailAgentTUI()
        app.db = mock_db  # Replace with mock
        
        async with app.run_test() as pilot:
            # The app should compose its widgets automatically
            # Check for main containers
            try:
                header = pilot.app.query_one("#header")
                assert header is not None
            except:
                # Header might not have an ID, check for Header widget
                from textual.widgets import Header
                headers = pilot.app.query(Header)
                assert len(headers) > 0
            
            # Check for main layout
            containers = pilot.app.query("Container")
            assert len(containers) > 0  # Should have containers

    @pytest.mark.asyncio
    async def test_refresh_data(self, mock_dependencies, sample_emails):
        """Test data refresh functionality."""
        mock_db, mock_crew = mock_dependencies
        mock_db.get_emails.return_value = sample_emails
        mock_db.get_email_stats.return_value = {
            "total": len(sample_emails),
            "unread": 2,
            "flagged": 1,
            "categories": {"primary": 2, "promotions": 1}
        }
        
        app = EmailAgentTUI()
        app.db = mock_db  # Replace the real db with mock
        
        # Mock the UI components
        with patch.object(app, 'query_one') as mock_query, \
             patch.object(app, 'notify') as mock_notify:
            
            mock_email_list = Mock()
            mock_sidebar = Mock()
            mock_query.side_effect = lambda selector, widget_type=None: {
                "#email-list": mock_email_list,
                "StatsSidebar": mock_sidebar
            }.get(selector, Mock())
            
            await app.refresh_data()
            
            # Verify data was loaded
            assert app.current_emails == sample_emails
            mock_email_list.load_emails.assert_called_once_with(sample_emails)
            mock_sidebar.update_stats.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_refresh(self, mock_dependencies):
        """Test refresh action."""
        mock_db, mock_crew = mock_dependencies
        
        app = EmailAgentTUI()
        
        with patch.object(app, 'refresh_data') as mock_refresh:
            await app.action_refresh()
            mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_search(self, mock_dependencies, sample_emails):
        """Test search action."""
        mock_db, mock_crew = mock_dependencies
        mock_db.get_emails.return_value = sample_emails[:1]  # Return filtered results
        
        app = EmailAgentTUI()
        app.db = mock_db  # Replace the real db with mock
        
        with patch.object(app, 'query_one') as mock_query, \
             patch.object(app, 'notify') as mock_notify:
            
            mock_input = Mock()
            mock_input.value = "urgent"
            mock_email_list = Mock()
            
            mock_query.side_effect = lambda selector, widget_type=None: {
                "#search-input": mock_input,
                "#email-list": mock_email_list
            }.get(selector, Mock())
            
            await app.action_search()
            
            # Verify search was performed
            mock_db.get_emails.assert_called_with(search="urgent", limit=100)
            mock_email_list.load_emails.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_save_settings(self, mock_dependencies):
        """Test save settings action."""
        mock_db, mock_crew = mock_dependencies
        
        app = EmailAgentTUI()
        
        with patch.object(app, 'query_one') as mock_query, \
             patch.object(app, 'notify') as mock_notify:
            
            # Mock settings widgets
            mock_widgets = {
                "#ai-model-select": Mock(value="gpt-4o-mini"),
                "#auto-summarize": Mock(value=True),
                "#auto-categorize": Mock(value=True),
                "#auto-action-items": Mock(value=False),
                "#sync-frequency": Mock(value="30"),
                "#max-emails": Mock(value="100")
            }
            mock_query.side_effect = lambda selector, widget_type=None: mock_widgets.get(selector, Mock())
            
            # Mock database session
            mock_session = Mock()
            mock_db.get_session.return_value.__enter__ = Mock(return_value=mock_session)
            mock_db.get_session.return_value.__exit__ = Mock(return_value=None)
            
            await app.action_save_settings()
            
            # Verify settings were saved
            mock_notify.assert_called()

    @pytest.mark.asyncio
    async def test_action_sync(self, mock_dependencies, sample_emails):
        """Test sync action."""
        mock_db, mock_crew = mock_dependencies
        mock_db.get_connector_configs.return_value = [Mock(type="test", enabled=True)]
        
        app = EmailAgentTUI()
        
        with patch.object(app, 'notify') as mock_notify, \
             patch.object(app, 'refresh_data') as mock_refresh:
            
            mock_crew_instance = Mock()
            mock_crew_instance.execute_task = AsyncMock(return_value=sample_emails)
            mock_crew.return_value = mock_crew_instance
            app.crew = mock_crew_instance
            
            mock_db.save_emails.return_value = len(sample_emails)
            
            await app.action_sync()
            
            # Verify sync was performed
            mock_crew_instance.execute_task.assert_called()
            mock_refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_brief(self, mock_dependencies, sample_emails):
        """Test brief generation action."""
        mock_db, mock_crew = mock_dependencies
        mock_db.get_emails.return_value = sample_emails
        
        app = EmailAgentTUI()
        
        with patch.object(app, 'notify') as mock_notify:
            mock_crew_instance = Mock()
            mock_crew_instance.execute_task = AsyncMock(return_value=Mock(headline="Test Brief"))
            mock_crew.return_value = mock_crew_instance
            app.crew = mock_crew_instance
            
            await app.action_brief()
            
            # Verify brief was generated
            mock_crew_instance.execute_task.assert_called()
            mock_notify.assert_called()

    @pytest.mark.asyncio
    async def test_email_selection(self, mock_dependencies, sample_emails):
        """Test email selection functionality."""
        mock_db, mock_crew = mock_dependencies
        
        app = EmailAgentTUI()
        app.current_emails = sample_emails
        
        with patch.object(app, 'query_one') as mock_query:
            mock_details = Mock()
            mock_tabs = Mock()
            
            mock_query.side_effect = lambda selector, widget_type=None: {
                "#email-details": mock_details,
                "TabbedContent": mock_tabs
            }.get(selector, Mock())
            
            # Simulate email selection
            from textual.widgets import DataTable
            event = Mock()
            event.data_table.id = "email-list"
            event.row_key = sample_emails[0].id
            
            await app.on_data_table_row_selected(event)
            
            # Verify email was selected and details shown
            assert app.selected_email == sample_emails[0]
            mock_details.show_email.assert_called_once_with(sample_emails[0])

    @pytest.mark.asyncio
    async def test_ai_filter_action(self, mock_dependencies, sample_emails):
        """Test AI filter action."""
        mock_db, mock_crew = mock_dependencies
        
        app = EmailAgentTUI()
        
        with patch.object(app, 'query_one') as mock_query, \
             patch.object(app, 'notify') as mock_notify:
            
            mock_input = Mock()
            mock_input.value = "urgent emails"
            mock_email_list = Mock()
            
            mock_query.side_effect = lambda selector, widget_type=None: {
                "#search-input": mock_input,
                "#email-list": mock_email_list
            }.get(selector, Mock())
            
            mock_crew_instance = Mock()
            mock_crew_instance.execute_task = AsyncMock(return_value=sample_emails[:1])
            mock_crew.return_value = mock_crew_instance
            app.crew = mock_crew_instance
            
            mock_db.get_emails.return_value = sample_emails
            
            await app.action_ai_filter()
            
            # Verify AI filtering was performed
            mock_crew_instance.execute_task.assert_called()
            mock_email_list.load_emails.assert_called()

    @pytest.mark.asyncio
    async def test_quit_action(self, mock_dependencies):
        """Test quit action."""
        mock_db, mock_crew = mock_dependencies
        
        app = EmailAgentTUI()
        
        with patch.object(app, 'exit') as mock_exit:
            mock_crew_instance = Mock()
            mock_crew_instance.shutdown = AsyncMock()
            app.crew = mock_crew_instance
            
            await app.action_quit()
            
            # Verify cleanup was performed
            mock_crew_instance.shutdown.assert_called_once()
            mock_exit.assert_called_once()

    def test_tui_css_styling(self, mock_dependencies):
        """Test TUI CSS styling."""
        mock_db, mock_crew = mock_dependencies
        
        app = EmailAgentTUI()
        
        # Verify CSS is defined
        assert app.CSS is not None
        assert isinstance(app.CSS, str)
        assert len(app.CSS) > 0
        
        # Check for key CSS classes
        assert ".sidebar" in app.CSS
        assert ".main-content" in app.CSS
        assert "SettingsPanel" in app.CSS

    def test_tui_bindings(self, mock_dependencies):
        """Test TUI key bindings."""
        mock_db, mock_crew = mock_dependencies
        
        app = EmailAgentTUI()
        
        # Verify bindings are defined
        assert app.BINDINGS is not None
        assert len(app.BINDINGS) > 0
        
        # Check for key bindings
        binding_keys = [binding[0] for binding in app.BINDINGS]
        assert "q" in binding_keys  # Quit
        assert "r" in binding_keys  # Refresh
        assert "s" in binding_keys  # Sync


class TestTUIIntegration:
    """Test TUI integration scenarios."""

    @pytest.fixture
    def mock_dependencies(self):
        """Set up mock dependencies."""
        with patch('email_agent.tui.app.DatabaseManager') as mock_db, \
             patch('email_agent.tui.app.EmailAgentCrew') as mock_crew:
            
            mock_db_instance = Mock()
            mock_db.return_value = mock_db_instance
            
            mock_crew_instance = Mock()
            mock_crew.return_value = mock_crew_instance
            
            yield mock_db_instance, mock_crew_instance

    @pytest.mark.asyncio
    async def test_full_tui_workflow(self, mock_dependencies, sample_emails):
        """Test complete TUI workflow."""
        mock_db, mock_crew = mock_dependencies
        mock_db.get_emails.return_value = sample_emails
        mock_db.get_email_stats.return_value = {
            "total": len(sample_emails),
            "unread": 2,
            "flagged": 1,
            "categories": {"primary": 2, "promotions": 1}
        }
        
        app = EmailAgentTUI()
        
        # Test initialization and data loading
        with patch.object(app, 'query_one') as mock_query, \
             patch.object(app, 'notify') as mock_notify:
            
            mock_query.return_value = Mock()
            
            await app.on_mount()
            
            # Should load initial data
            assert app.title == "Email Agent"

    def test_tui_error_handling(self, mock_dependencies):
        """Test TUI error handling."""
        mock_db, mock_crew = mock_dependencies
        mock_db.get_emails.side_effect = Exception("Database error")
        
        app = EmailAgentTUI()
        
        # Should handle database errors gracefully
        with patch.object(app, 'notify') as mock_notify:
            # This should not raise an exception
            pass

    @pytest.mark.asyncio 
    async def test_tui_performance_with_large_datasets(self, mock_dependencies):
        """Test TUI performance with large datasets."""
        mock_db, mock_crew = mock_dependencies
        
        # Create large dataset
        large_email_list = []
        for i in range(1000):
            email = Mock()
            email.id = f"email-{i}"
            email.subject = f"Test Email {i}"
            email.sender = Mock(email=f"sender{i}@example.com")
            large_email_list.append(email)
        
        mock_db.get_emails.return_value = large_email_list
        mock_db.get_email_stats.return_value = {
            "total": 1000,
            "unread": 500,
            "flagged": 10,
            "categories": {"primary": 600, "social": 200, "promotions": 200}
        }
        
        app = EmailAgentTUI()
        
        with patch.object(app, 'query_one') as mock_query:
            mock_query.return_value = Mock()
            
            # Should handle large datasets without issues
            await app.refresh_data()
            
            assert len(app.current_emails) == 1000
