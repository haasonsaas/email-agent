"""Tests for email agent functionality."""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, date

from src.email_agent.agents.collector import CollectorAgent
from src.email_agent.agents.categorizer import CategorizerAgent
from src.email_agent.agents.summarizer import SummarizerAgent
from src.email_agent.agents.crew import EmailAgentCrew
from src.email_agent.models import EmailCategory, EmailPriority


class TestCollectorAgent:
    """Test email collection functionality."""

    @pytest.mark.asyncio
    async def test_collector_initialization(self):
        """Test collector agent initialization."""
        collector = CollectorAgent()
        assert collector is not None
        
        status = await collector.get_status()
        assert "connectors" in status
        assert "stats" in status

    @pytest.mark.asyncio
    async def test_collector_with_no_connectors(self):
        """Test collector behavior with no connectors."""
        collector = CollectorAgent()
        emails = await collector.collect_emails([], since=datetime.now())
        assert emails == []

    @pytest.mark.asyncio
    async def test_collector_shutdown(self):
        """Test collector shutdown."""
        collector = CollectorAgent()
        await collector.shutdown()
        # Should not raise any exceptions


class TestCategorizerAgent:
    """Test email categorization functionality."""

    @pytest.mark.asyncio
    async def test_categorizer_initialization(self):
        """Test categorizer agent initialization."""
        categorizer = CategorizerAgent()
        assert categorizer is not None
        
        status = await categorizer.get_status()
        assert "rules_loaded" in status
        assert "stats" in status

    @pytest.mark.asyncio
    async def test_categorize_emails(self, sample_emails, sample_rules):
        """Test email categorization."""
        categorizer = CategorizerAgent()
        
        # Test categorization
        categorized = await categorizer.categorize_emails(sample_emails, sample_rules)
        
        assert len(categorized) == len(sample_emails)
        
        # Check that urgent email was processed
        urgent_email = next((e for e in categorized if "urgent" in e.subject.lower()), None)
        assert urgent_email is not None
        assert urgent_email.priority == EmailPriority.URGENT

    @pytest.mark.asyncio
    async def test_rule_application(self, sample_emails, sample_rules):
        """Test individual rule application."""
        categorizer = CategorizerAgent()
        
        email = sample_emails[0]  # Urgent email
        rule = sample_rules[0]    # Urgent rule
        
        # Apply rule
        result = categorizer._apply_rule_to_email(email, rule)
        
        assert result is True
        assert "urgent" in email.tags

    @pytest.mark.asyncio
    async def test_rule_condition_matching(self, sample_emails, sample_rules):
        """Test rule condition matching."""
        categorizer = CategorizerAgent()
        
        email = sample_emails[0]  # Has "urgent" in subject
        condition = sample_rules[0].conditions[0]  # Matches "urgent"
        
        matches = categorizer._matches_condition(email, condition)
        assert matches is True

    @pytest.mark.asyncio
    async def test_categorizer_with_no_rules(self, sample_emails):
        """Test categorizer with no rules."""
        categorizer = CategorizerAgent()
        
        categorized = await categorizer.categorize_emails(sample_emails, [])
        assert len(categorized) == len(sample_emails)
        # Emails should remain unchanged
        for original, cat in zip(sample_emails, categorized):
            assert original.id == cat.id


class TestSummarizerAgent:
    """Test email summarization functionality."""

    @pytest.mark.asyncio
    async def test_summarizer_initialization(self):
        """Test summarizer agent initialization."""
        summarizer = SummarizerAgent()
        assert summarizer is not None
        
        status = await summarizer.get_status()
        assert "llm_available" in status
        assert "stats" in status

    @pytest.mark.asyncio
    async def test_generate_brief(self, sample_emails):
        """Test daily brief generation."""
        summarizer = SummarizerAgent()
        
        target_date = date.today()
        brief = await summarizer.generate_brief(sample_emails, target_date)
        
        assert brief is not None
        assert brief.total_emails == len(sample_emails)
        assert brief.headline is not None
        assert brief.summary is not None

    @pytest.mark.asyncio
    async def test_summarize_email(self, sample_emails):
        """Test individual email summarization."""
        summarizer = SummarizerAgent()
        
        email = sample_emails[0]
        summary_data = await summarizer.summarize_email(email)
        
        assert "summary" in summary_data
        assert "action_items" in summary_data
        assert "priority" in summary_data

    @pytest.mark.asyncio
    async def test_filter_emails_by_query(self, sample_emails):
        """Test AI-powered email filtering."""
        summarizer = SummarizerAgent()
        
        # Test filtering for urgent emails
        filtered = await summarizer.filter_emails_by_query(sample_emails, "urgent")
        
        # Should find at least the urgent email
        assert len(filtered) >= 1
        urgent_found = any("urgent" in email.subject.lower() for email in filtered)
        assert urgent_found

    @pytest.mark.asyncio
    async def test_brief_with_no_emails(self):
        """Test brief generation with no emails."""
        summarizer = SummarizerAgent()
        
        brief = await summarizer.generate_brief([], date.today())
        
        assert brief.total_emails == 0
        assert brief.headline == "No emails for today"

    @pytest.mark.asyncio
    async def test_email_analysis_parsing(self):
        """Test parsing of AI analysis response."""
        summarizer = SummarizerAgent()
        
        mock_content = """
        SUMMARY: This is a test email summary
        ACTION_ITEMS: 
        • Review the document
        • Schedule a meeting
        PRIORITY: high
        """
        
        parsed = summarizer._parse_email_analysis(mock_content)
        
        assert parsed["summary"] == "This is a test email summary"
        assert len(parsed["action_items"]) == 2
        assert parsed["priority"] == "high"


class TestEmailAgentCrew:
    """Test crew orchestration functionality."""

    @pytest.mark.asyncio
    async def test_crew_initialization(self):
        """Test crew initialization."""
        crew = EmailAgentCrew()
        await crew.initialize_crew({})
        
        assert crew.crew is not None
        assert len(crew.agents) == 3
        assert "collector" in crew.agents
        assert "categorizer" in crew.agents
        assert "summarizer" in crew.agents
        
        await crew.shutdown()

    @pytest.mark.asyncio
    async def test_full_processing_pipeline(self, sample_emails, sample_rules, temp_db):
        """Test full email processing pipeline."""
        crew = EmailAgentCrew()
        await crew.initialize_crew({})
        
        # Mock the collection step to return our sample emails
        with patch.object(crew.collector_agent, 'collect_emails', return_value=sample_emails):
            results = await crew.execute_task(
                "full_processing",
                connector_configs=[],
                rules=sample_rules,
                since=datetime.now(),
                generate_brief=True
            )
        
        assert results["emails_collected"] == len(sample_emails)
        assert results["emails_categorized"] == len(sample_emails)
        assert results["brief_generated"] is True
        
        await crew.shutdown()

    @pytest.mark.asyncio
    async def test_individual_task_execution(self, sample_emails):
        """Test individual task execution."""
        crew = EmailAgentCrew()
        await crew.initialize_crew({})
        
        # Test email summarization task
        email = sample_emails[0]
        summary_data = await crew.execute_task("summarize_email", email=email)
        
        assert "summary" in summary_data
        assert "action_items" in summary_data
        
        await crew.shutdown()

    @pytest.mark.asyncio
    async def test_agent_status_retrieval(self):
        """Test agent status retrieval."""
        crew = EmailAgentCrew()
        await crew.initialize_crew({})
        
        # Test status for each agent
        for agent_name in ["collector", "categorizer", "summarizer"]:
            status = await crew.get_agent_status(agent_name)
            assert "name" in status
            assert "role" in status
            assert "status" in status
        
        await crew.shutdown()

    @pytest.mark.asyncio
    async def test_unknown_task_handling(self):
        """Test handling of unknown tasks."""
        crew = EmailAgentCrew()
        await crew.initialize_crew({})
        
        with pytest.raises(Exception):  # Should raise AgentError
            await crew.execute_task("unknown_task")
        
        await crew.shutdown()

    @pytest.mark.asyncio
    async def test_crew_shutdown(self):
        """Test crew shutdown process."""
        crew = EmailAgentCrew()
        await crew.initialize_crew({})
        
        # Should not raise any exceptions
        await crew.shutdown()

    @pytest.mark.asyncio
    async def test_email_filtering_task(self, sample_emails):
        """Test email filtering task execution."""
        crew = EmailAgentCrew()
        await crew.initialize_crew({})
        
        filtered = await crew.execute_task(
            "filter_emails",
            emails=sample_emails,
            query="urgent maintenance"
        )
        
        assert isinstance(filtered, list)
        # Should find emails related to the query
        
        await crew.shutdown()

    @pytest.mark.asyncio
    async def test_categorization_task(self, sample_emails, sample_rules):
        """Test categorization task execution."""
        crew = EmailAgentCrew()
        await crew.initialize_crew({})
        
        categorized = await crew.execute_task(
            "categorize_emails",
            emails=sample_emails,
            rules=sample_rules
        )
        
        assert len(categorized) == len(sample_emails)
        
        await crew.shutdown()

    @pytest.mark.asyncio
    async def test_brief_generation_task(self, sample_emails):
        """Test brief generation task execution."""
        crew = EmailAgentCrew()
        await crew.initialize_crew({})
        
        brief = await crew.execute_task(
            "generate_brief",
            emails=sample_emails,
            date=date.today()
        )
        
        assert brief is not None
        assert brief.total_emails == len(sample_emails)
        
        await crew.shutdown()
