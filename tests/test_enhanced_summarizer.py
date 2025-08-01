"""Tests for the Enhanced Summarizer Agent."""

import pytest
from datetime import datetime, date
from unittest.mock import Mock, patch

from src.email_agent.agents.enhanced_summarizer import EnhancedSummarizerAgent
from src.email_agent.models import Email, EmailAddress, EmailCategory, EmailPriority, DailyBrief


@pytest.fixture
def enhanced_summarizer():
    """Create an enhanced summarizer for testing."""
    return EnhancedSummarizerAgent(config={'openai_api_key': 'test-key'})


@pytest.fixture
def sample_emails():
    """Create sample emails for testing."""
    emails = []
    
    # Email 1: Work project update
    emails.append(Email(
        id="email1",
        message_id="email1",
        subject="Q4 Project Update - Critical Milestone Reached",
        sender=EmailAddress(email="project.manager@company.com", name="Project Manager"),
        recipients=[EmailAddress(email="user@company.com")],
        body_text="""Hi Team,

Great news! We've successfully completed the integration phase of our Q4 project. This puts us ahead of schedule and well-positioned for the final phase.

Key achievements:
- API integration completed
- User testing phase started
- Performance benchmarks exceeded expectations

Next steps:
- Complete user testing by Friday
- Prepare for production deployment
- Schedule stakeholder review meeting

Let me know if you have any questions.

Best regards,
Project Manager""",
        date=datetime(2023, 10, 15, 9, 30),
        received_date=datetime(2023, 10, 15, 9, 30),
        category=EmailCategory.PRIMARY,
        priority=EmailPriority.HIGH,
        is_read=False
    ))
    
    # Email 2: Meeting request
    emails.append(Email(
        id="email2", 
        message_id="email2",
        subject="Re: Schedule Team Sync - This Week",
        sender=EmailAddress(email="team.lead@company.com", name="Team Lead"),
        recipients=[EmailAddress(email="user@company.com")],
        body_text="""Hi,

Following up on our discussion yesterday. Can we schedule our team sync for Thursday at 2 PM? 

We need to discuss:
- Sprint planning for next iteration
- Resource allocation
- Blocker resolution

Let me know if this works for everyone.

Thanks,
Team Lead""",
        date=datetime(2023, 10, 15, 11, 15),
        received_date=datetime(2023, 10, 15, 11, 15),
        category=EmailCategory.PRIMARY,
        priority=EmailPriority.NORMAL,
        is_read=True
    ))
    
    # Email 3: Client feedback
    emails.append(Email(
        id="email3",
        message_id="email3", 
        subject="Client Feedback - Demo Review",
        sender=EmailAddress(email="client@external.com", name="Client Manager"),
        recipients=[EmailAddress(email="user@company.com")],
        body_text="""Hello,

Thank you for the demo presentation yesterday. Our team was impressed with the progress and the user interface improvements.

A few points of feedback:
- The new dashboard is much more intuitive
- Loading times have improved significantly
- Minor issue with the export functionality needs attention

Overall, we're very pleased with the direction. Looking forward to the next iteration.

Best,
Client Manager""",
        date=datetime(2023, 10, 15, 14, 45),
        received_date=datetime(2023, 10, 15, 14, 45),
        category=EmailCategory.PRIMARY,
        priority=EmailPriority.HIGH,
        is_read=False
    ))
    
    return emails


class TestNarrativeAnalysis:
    """Test narrative analysis functionality."""
    
    @pytest.mark.asyncio
    async def test_analyze_for_narrative_basic(self, enhanced_summarizer, sample_emails):
        """Test basic narrative analysis."""
        analysis = await enhanced_summarizer._analyze_for_narrative(sample_emails)
        
        assert isinstance(analysis, dict)
        assert "total_emails" in analysis
        assert "key_people" in analysis
        assert "themes" in analysis
        assert "story_elements" in analysis
        assert "temporal_flow" in analysis
        
        assert analysis["total_emails"] == len(sample_emails)
        assert len(analysis["key_people"]) > 0
    
    @pytest.mark.asyncio
    async def test_identify_story_arcs(self, enhanced_summarizer, sample_emails):
        """Test story arc identification."""
        story_arcs = await enhanced_summarizer._identify_story_arcs(sample_emails)
        
        assert isinstance(story_arcs, list)
        # Should group emails with similar subjects
        # In this case, might find the "Re: Schedule Team Sync" as a continuation
        
    def test_analyze_temporal_flow(self, enhanced_summarizer, sample_emails):
        """Test temporal flow analysis."""
        temporal_flow = enhanced_summarizer._analyze_temporal_flow(sample_emails)
        
        assert isinstance(temporal_flow, dict)
        assert "hourly_distribution" in temporal_flow
        assert "peak_hour" in temporal_flow
        assert "morning_activity" in temporal_flow
        assert "afternoon_activity" in temporal_flow
        
        # Should detect activity across different times of day
        assert temporal_flow["morning_activity"] > 0
        assert temporal_flow["afternoon_activity"] > 0
    
    def test_extract_themes_rule_based(self, enhanced_summarizer, sample_emails):
        """Test rule-based theme extraction."""
        themes = enhanced_summarizer._extract_themes_rule_based(sample_emails)
        
        assert isinstance(themes, list)
        # Should identify themes like "project management", "meetings", etc.
        assert any("project" in theme.lower() for theme in themes)
    
    @pytest.mark.asyncio
    async def test_analyze_emotional_tone_rule_based(self, enhanced_summarizer, sample_emails):
        """Test rule-based emotional tone analysis."""
        # Test without OpenAI client
        enhanced_summarizer.openai_client = None
        
        tone_analysis = await enhanced_summarizer._analyze_emotional_tone(sample_emails)
        
        assert isinstance(tone_analysis, dict)
        assert "dominant" in tone_analysis
        assert "distribution" in tone_analysis
        assert tone_analysis["dominant"] in ["positive", "negative", "neutral", "urgent", "professional", "casual"]
    
    def test_identify_urgency_clusters(self, enhanced_summarizer, sample_emails):
        """Test urgency cluster identification."""
        clusters = enhanced_summarizer._identify_urgency_clusters(sample_emails)
        
        assert isinstance(clusters, list)
        # With high priority emails in sample data, should find clusters if they're close in time
    
    def test_extract_action_items(self, enhanced_summarizer, sample_emails):
        """Test action item extraction."""
        action_items = enhanced_summarizer._extract_action_items(sample_emails)
        
        assert isinstance(action_items, list)
        # Should extract actions from unread or high priority emails
        assert len(action_items) > 0
    
    def test_extract_deadlines(self, enhanced_summarizer, sample_emails):
        """Test deadline extraction."""
        deadlines = enhanced_summarizer._extract_deadlines(sample_emails)
        
        assert isinstance(deadlines, list)
        # Should find "by Friday" and "Thursday at 2 PM" mentions


class TestNarrativeGeneration:
    """Test narrative content generation."""
    
    def test_create_rule_based_headline(self, enhanced_summarizer, sample_emails):
        """Test rule-based headline creation."""
        analysis = {
            "total_emails": len(sample_emails),
            "unread_emails": 2,
            "priorities": {"urgent": 1, "high": 1, "normal": 1}
        }
        
        headline = enhanced_summarizer._create_rule_based_headline(sample_emails, analysis)
        
        assert isinstance(headline, str)
        assert len(headline) > 0
        assert "high" in headline.lower() or "urgent" in headline.lower()  # Should mention high priority
    
    def test_create_rule_based_narrative(self, enhanced_summarizer, sample_emails):
        """Test rule-based narrative creation."""
        analysis = {
            "total_emails": len(sample_emails),
            "unread_emails": 2,
            "key_people": {"project.manager@company.com": 1, "team.lead@company.com": 1},
            "themes": ["project management", "meetings"],
            "priorities": {"high": 2, "normal": 1}
        }
        
        narrative = enhanced_summarizer._create_rule_based_narrative(sample_emails, analysis)
        
        assert isinstance(narrative, str)
        assert len(narrative) > 50  # Should be substantial
        assert str(len(sample_emails)) in narrative  # Should mention email count
        assert "project" in narrative.lower() or "meeting" in narrative.lower()  # Should mention themes
    
    @pytest.mark.asyncio
    async def test_generate_narrative_brief_without_ai(self, enhanced_summarizer, sample_emails):
        """Test narrative brief generation without AI."""
        enhanced_summarizer.openai_client = None  # Disable AI
        
        target_date = date(2023, 10, 15)
        brief = await enhanced_summarizer.generate_narrative_brief(sample_emails, target_date)
        
        assert isinstance(brief, DailyBrief)
        assert brief.total_emails == len(sample_emails)
        assert brief.unread_emails == 2  # Two unread emails in sample data
        assert len(brief.headline) > 0
        assert len(brief.summary) > 0
        assert brief.model_used == "enhanced_narrative"
        
        # Check that metadata is stored in summary
        assert "---NARRATIVE_METADATA---" in brief.summary
    
    @patch('src.email_agent.agents.enhanced_summarizer.OpenAI')
    @pytest.mark.asyncio
    async def test_generate_narrative_brief_with_ai(self, mock_openai_class, enhanced_summarizer, sample_emails):
        """Test narrative brief generation with AI."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
HEADLINE: Today's inbox unveils a story of project triumph and collaborative momentum

NARRATIVE: Today's email story begins with celebration as the Q4 project team reaches a critical milestone ahead of schedule. The morning brought news of successful API integration and exceeded performance benchmarks, setting an optimistic tone for the day. As the hours progressed, the narrative shifted to forward-looking collaboration, with team synchronization plans emerging for Thursday's strategic session. The afternoon concluded with external validation, as client feedback revealed genuine satisfaction with the demo presentation and user interface improvements. This three-act email drama showcases a productive day where technical achievement, team coordination, and client satisfaction converged to paint a picture of project success and organizational momentum.

ACTION_ITEMS:
- Complete user testing by Friday deadline
- Confirm Thursday 2 PM team sync attendance  
- Address minor export functionality issue raised by client
- Schedule stakeholder review meeting for Q4 project
- Prepare for production deployment phase

DEADLINES:
- User testing completion: Friday
- Team sync meeting: Thursday 2 PM

CHARACTERS:
- Project Manager (milestone achievement communicator)
- Team Lead (coordination facilitator)
- Client Manager (feedback provider and validation source)

THEMES:
- Project milestone achievement
- Team collaboration and scheduling
- Client satisfaction and feedback integration
"""
        
        mock_openai_instance = Mock()
        mock_openai_instance.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_openai_instance
        
        # Reinitialize with mocked OpenAI
        enhanced_summarizer.openai_client = mock_openai_instance
        
        target_date = date(2023, 10, 15)
        brief = await enhanced_summarizer.generate_narrative_brief(sample_emails, target_date)
        
        assert isinstance(brief, DailyBrief)
        assert "story" in brief.headline.lower() or "triumph" in brief.headline.lower()
        assert "project" in brief.summary.lower()
        assert len(brief.action_items) > 0
        assert "Friday" in str(brief.deadlines) or "Thursday" in str(brief.deadlines)
        
        # Check narrative elements in metadata
        assert "---NARRATIVE_METADATA---" in brief.summary


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_calculate_narrative_score(self, enhanced_summarizer):
        """Test narrative score calculation."""
        content_with_narrative = {
            "narrative_summary": "Today's story began with excitement as the team journey unfolded through various developments and ultimately concluded with success.",
            "key_characters": ["Project Manager", "Team Lead"],
            "themes": ["collaboration", "achievement"],
            "headline": "Today's email story reveals triumph"
        }
        
        content_without_narrative = {
            "narrative_summary": "Received emails about project status and meeting scheduling.",
            "key_characters": [],
            "themes": [],
            "headline": "Daily email summary"
        }
        
        high_score = enhanced_summarizer._calculate_narrative_score(content_with_narrative)
        low_score = enhanced_summarizer._calculate_narrative_score(content_without_narrative)
        
        assert high_score > low_score
        assert 0 <= high_score <= 1
        assert 0 <= low_score <= 1
    
    def test_parse_narrative_response(self, enhanced_summarizer):
        """Test narrative response parsing."""
        ai_response = """
HEADLINE: Today's inbox tells a compelling story

NARRATIVE: The day began with project updates and continued with collaborative planning sessions.

ACTION_ITEMS:
- Complete user testing
- Schedule team meeting

DEADLINES:
- Project deadline: Friday

CHARACTERS:
- Project Manager
- Team Lead

THEMES:
- Project management
- Team collaboration
"""
        
        parsed = enhanced_summarizer._parse_narrative_response(ai_response)
        
        assert parsed["headline"] == "Today's inbox tells a compelling story"
        assert "project updates" in parsed["narrative_summary"]
        assert len(parsed["action_items"]) == 2
        assert len(parsed["deadlines"]) == 1
        assert len(parsed["key_characters"]) == 2
        assert len(parsed["themes"]) == 2
        assert 0 <= parsed["narrative_score"] <= 1
    
    @pytest.mark.asyncio
    async def test_get_status(self, enhanced_summarizer):
        """Test status reporting."""
        status = await enhanced_summarizer.get_status()
        
        assert isinstance(status, dict)
        assert "agent_type" in status
        assert status["agent_type"] == "enhanced_summarizer"
        assert "target_reading_time" in status
        assert "max_words" in status
        assert "stats" in status


class TestEmptyAndErrorCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_generate_brief_empty_emails(self, enhanced_summarizer):
        """Test brief generation with no emails."""
        brief = await enhanced_summarizer.generate_narrative_brief([], date.today())
        
        assert isinstance(brief, DailyBrief)
        assert brief.total_emails == 0
        assert "quiet day" in brief.headline.lower()
        assert "no emails" in brief.summary.lower()
    
    def test_create_empty_brief(self, enhanced_summarizer):
        """Test empty brief creation."""
        target_date = date(2023, 10, 15)
        brief = enhanced_summarizer._create_empty_brief(target_date)
        
        assert isinstance(brief, DailyBrief)
        assert brief.total_emails == 0
        assert brief.date.date() == target_date
        assert brief.model_used == "enhanced_narrative"
    
    def test_create_error_brief(self, enhanced_summarizer):
        """Test error brief creation."""
        target_date = date(2023, 10, 15)
        error_msg = "Test error message"
        brief = enhanced_summarizer._create_error_brief(target_date, error_msg)
        
        assert isinstance(brief, DailyBrief)
        assert error_msg in brief.summary
        assert brief.model_used == "error_fallback"


if __name__ == "__main__":
    pytest.main([__file__])
