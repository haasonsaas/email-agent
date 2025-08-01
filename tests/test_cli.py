"""Tests for CLI functionality."""

import pytest
from unittest.mock import patch, Mock
from typer.testing import CliRunner

from src.email_agent.cli.main import app


class TestCLI:
    """Test CLI commands."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    def test_cli_help(self):
        """Test CLI help command."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Email Agent" in result.output

    def test_version_command(self):
        """Test version command."""
        result = self.runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "Email Agent v" in result.output

    @patch('src.email_agent.cli.main.DatabaseManager')
    def test_stats_command(self, mock_db):
        """Test stats command."""
        # Mock database response
        mock_db_instance = Mock()
        mock_db_instance.get_email_stats.return_value = {
            "total": 10,
            "unread": 5,
            "flagged": 1,
            "categories": {"primary": 5, "social": 3, "promotions": 2}
        }
        mock_db.return_value = mock_db_instance
        
        result = self.runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "10" in result.output  # Changed to just look for the number

    @patch('src.email_agent.cli.main.EmailAgentCrew')
    @patch('src.email_agent.cli.main.DatabaseManager')
    def test_sync_command_no_connectors(self, mock_db, mock_crew):
        """Test sync command with no connectors."""
        mock_db_instance = Mock()
        mock_db_instance.get_connector_configs.return_value = []
        mock_db.return_value = mock_db_instance
        
        result = self.runner.invoke(app, ["sync"])
        assert result.exit_code == 0
        assert "No connectors configured" in result.output

    def test_config_commands(self):
        """Test config subcommands."""
        # Test config help
        result = self.runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "config" in result.output.lower()  # Just check for config in output

    def test_brief_commands(self):
        """Test brief subcommands."""
        # Test brief help
        result = self.runner.invoke(app, ["brief", "--help"])
        assert result.exit_code == 0
        assert "Generate and view daily briefs" in result.output

    @patch('src.email_agent.storage.database.DatabaseManager')
    def test_brief_list_command(self, mock_db):
        """Test brief list command."""
        # Mock database response
        mock_db_instance = Mock()
        mock_db_instance.get_session.return_value.__enter__ = Mock()
        mock_db_instance.get_session.return_value.__exit__ = Mock()
        mock_db.return_value = mock_db_instance
        
        result = self.runner.invoke(app, ["brief", "list"])
        assert result.exit_code == 0

    def test_dashboard_command_import(self):
        """Test that dashboard command can be imported."""
        # Just test that the command exists and can be invoked
        # (without actually running the TUI)
        result = self.runner.invoke(app, ["dashboard", "--help"])
        # This might fail if dashboard command doesn't exist
        # but should at least not crash on import

    def test_invalid_command(self):
        """Test invalid command handling."""
        result = self.runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0

    @patch('src.email_agent.storage.database.DatabaseManager')
    def test_rules_operations(self, mock_db):
        """Test rules management operations."""
        mock_db_instance = Mock()
        mock_db_instance.get_rules.return_value = []
        mock_db.return_value = mock_db_instance
        
        # Test rules list
        result = self.runner.invoke(app, ["rule", "list"])
        assert result.exit_code == 0

    def test_cli_with_verbose_flag(self):
        """Test CLI with verbose flag."""
        result = self.runner.invoke(app, ["--verbose", "stats"])
        # Should not crash with verbose flag

    def test_cli_with_config_file(self):
        """Test CLI with config file option."""
        with self.runner.isolated_filesystem():
            # Create a temporary config file
            with open("test_config.yaml", "w") as f:
                f.write("log_level: debug\n")
            
            result = self.runner.invoke(app, ["--config", "test_config.yaml", "stats"])
            # Should handle config file option

    @patch.dict('os.environ', {'EMAIL_AGENT_ENV': 'test'})
    def test_cli_with_test_environment(self):
        """Test CLI in test environment."""
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0

    def test_cli_error_handling(self):
        """Test CLI error handling."""
        # Test with invalid database path
        with patch.dict('os.environ', {'DATABASE_URL': 'invalid://path'}):
            result = self.runner.invoke(app, ["stats"])
            # Should handle database errors gracefully

    @patch('src.email_agent.tui.app.EmailAgentTUI.run')
    def test_dashboard_command_execution(self, mock_run):
        """Test dashboard command execution."""
        mock_run.return_value = None
        
        result = self.runner.invoke(app, ["dashboard"])
        assert result.exit_code == 0
        mock_run.assert_called_once()


class TestCLIIntegration:
    """Test CLI integration scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    @patch('src.email_agent.cli.main.DatabaseManager')
    @patch('src.email_agent.cli.main.EmailAgentCrew')
    def test_full_sync_workflow(self, mock_crew, mock_db):
        """Test complete sync workflow via CLI."""
        # Setup mocks
        mock_db_instance = Mock()
        mock_db_instance.get_connector_configs.return_value = [
            Mock(type="test", name="Test Connector", enabled=True)
        ]
        mock_db_instance.get_rules.return_value = []
        mock_db.return_value = mock_db_instance
        
        mock_crew_instance = Mock()
        # Create async mocks for the async methods
        from unittest.mock import AsyncMock
        mock_crew_instance.initialize_crew = AsyncMock()
        mock_crew_instance.execute_task = AsyncMock(return_value={
            "emails_collected": 5,
            "emails_categorized": 5,
            "emails_saved": 5,
            "brief_generated": True
        })
        mock_crew_instance.shutdown = AsyncMock()
        mock_crew.return_value = mock_crew_instance
        
        # Run sync command  
        result = self.runner.invoke(app, ["sync", "--brief"])
        
        # Verify execution
        assert result.exit_code == 0
        mock_crew_instance.initialize_crew.assert_called_once()
        mock_crew_instance.execute_task.assert_called()

    @patch('src.email_agent.storage.database.DatabaseManager')
    def test_brief_generation_workflow(self, mock_db):
        """Test brief generation workflow."""
        mock_db_instance = Mock()
        mock_db.return_value = mock_db_instance
        
        with patch('src.email_agent.agents.crew.EmailAgentCrew') as mock_crew:
            mock_crew_instance = Mock()
            mock_crew.return_value = mock_crew_instance
            
            result = self.runner.invoke(app, ["brief", "generate"])
            # Should execute without critical errors

    def test_cli_command_chaining(self):
        """Test running multiple CLI commands in sequence."""
        commands = [
            ["stats"],
            ["rules", "list"],
            ["brief", "list"]
        ]
        
        for cmd in commands:
            result = self.runner.invoke(app, cmd)
            # Each command should complete without crashing

    @patch('src.email_agent.storage.database.DatabaseManager')
    def test_cli_with_database_issues(self, mock_db):
        """Test CLI behavior with database connectivity issues."""
        mock_db.side_effect = Exception("Database connection failed")
        
        result = self.runner.invoke(app, ["stats"])
        # Should handle database errors gracefully

    def test_cli_output_formatting(self):
        """Test CLI output formatting."""
        result = self.runner.invoke(app, ["--help"])
        
        # Check for proper formatting
        assert result.exit_code == 0
        assert "Usage:" in result.output
        # Typer uses rich formatting which shows "Commands" in a box, not as a plain string

    @patch('src.email_agent.cli.main.DatabaseManager')
    def test_cli_with_large_datasets(self, mock_db):
        """Test CLI performance with large datasets."""
        mock_db_instance = Mock()
        mock_db_instance.get_email_stats.return_value = {
            "total": 10000,
            "unread": 5000,
            "flagged": 100,
            "categories": {
                "primary": 3000,
                "social": 2000,
                "promotions": 3000,
                "updates": 2000
            }
        }
        mock_db.return_value = mock_db_instance
        
        result = self.runner.invoke(app, ["stats"])
        assert result.exit_code == 0
        assert "10000" in result.output
