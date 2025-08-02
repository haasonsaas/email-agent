"""Tests for the AI Draft Agent."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from email_agent.agents.draft_agent import DraftAgent, WritingStyle, DraftSuggestion
from email_agent.models import Email, EmailAddress, EmailCategory, EmailPriority


@pytest.fixture
def draft_agent():
    """Create a draft agent for testing."""
    return DraftAgent(config={'openai_api_key': 'test-key'})


@pytest.fixture
def sample_sent_emails():
    """Create sample sent emails for testing writing style analysis."""
    emails = []
    
    # Email 1: Professional, formal
    emails.append(Email(
        id="sent1",
        message_id="sent1",
        subject="Meeting Follow-up",
        sender=EmailAddress(email="user@company.com", name="Test User"),
        recipients=[EmailAddress(email="colleague@company.com")],
        body_text="""Hi John,

Thank you for taking the time to meet with me yesterday. I wanted to follow up on our discussion regarding the Q4 project timeline.

As we discussed, I believe we can deliver the initial phase by November 15th if we prioritize the core features first. I'll send over the detailed project plan by end of week.

Please let me know if you have any questions or concerns.

Best regards,
Test User""",
        date=datetime(2023, 10, 15, 14, 30),
        received_date=datetime(2023, 10, 15, 14, 30),
        category=EmailCategory.PRIMARY,
        priority=EmailPriority.NORMAL
    ))
    
    # Email 2: Casual, friendly
    emails.append(Email(
        id="sent2",
        message_id="sent2",
        subject="Quick question",
        sender=EmailAddress(email="user@company.com", name="Test User"),
        recipients=[EmailAddress(email="friend@company.com")],
        body_text="""Hey Sarah!

Hope you're doing well! I had a quick question about the design mockups - are we still on track to get them by Friday?

Let me know when you have a chance.

Thanks!
Test""",
        date=datetime(2023, 10, 16, 10, 15),
        received_date=datetime(2023, 10, 16, 10, 15),
        category=EmailCategory.PRIMARY,
        priority=EmailPriority.NORMAL
    ))
    
    # Email 3: Brief, urgent
    emails.append(Email(
        id="sent3",
        message_id="sent3",
        subject="URGENT: Server Issue",
        sender=EmailAddress(email="user@company.com", name="Test User"),
        recipients=[EmailAddress(email="team@company.com")],
        body_text="""Team,

We're experiencing server issues in production. I'm investigating now and will update you within the hour.

Please hold off on any deployments until further notice.

Thanks,
Test User""",
        date=datetime(2023, 10, 17, 16, 45),
        received_date=datetime(2023, 10, 17, 16, 45),
        category=EmailCategory.PRIMARY,
        priority=EmailPriority.URGENT
    ))
    
    return emails


@pytest.fixture
def sample_incoming_email():
    """Create a sample incoming email to respond to."""
    return Email(
        id="incoming1",
        message_id="incoming1",
        subject="Project Status Update Request",
        sender=EmailAddress(email="manager@company.com", name="Manager"),
        recipients=[EmailAddress(email="user@company.com", name="Test User")],
        body_text="""Hi Test User,

I hope this email finds you well. I wanted to check in on the status of the Q4 project we discussed last week.

Could you please provide an update on:
1. Current progress and milestones completed?
2. Any blockers or challenges you're facing?
3. Updated timeline for completion?

I'd appreciate if you could get back to me by end of week so I can update the stakeholders.

Thanks for your hard work on this project.

Best,
Manager""",
        date=datetime(2023, 10, 18, 9, 0),
        received_date=datetime(2023, 10, 18, 9, 0),
        category=EmailCategory.PRIMARY,
        priority=EmailPriority.HIGH
    )


class TestWritingStyleAnalysis:
    """Test writing style analysis functionality."""
    
    def test_analyze_writing_style_insufficient_emails(self, draft_agent):
        """Test analysis with insufficient emails."""
        emails = []  # Empty list
        style = draft_agent.analyze_writing_style(emails)
        
        assert isinstance(style, WritingStyle)
        assert style.avg_length == 0
        assert style.greeting_style == "Hi"
        assert style.closing_style == "Best"
    
    def test_analyze_writing_style_basic_metrics(self, draft_agent, sample_sent_emails):
        """Test basic writing style metrics."""
        style = draft_agent.analyze_writing_style(sample_sent_emails)
        
        assert isinstance(style, WritingStyle)
        assert style.avg_length > 0  # Should calculate average word count
        assert style.greeting_style in ["Hi", "Hey", "Hello", "Team", "Thank"]  # Should detect greetings
        assert style.closing_style in ["Best", "Thanks", "Best regards"]  # Should detect closings
        assert 0 <= style.formality_score <= 1  # Should be normalized
        assert 0 <= style.sentence_complexity <= 1  # Should be normalized
    
    def test_greeting_analysis(self, draft_agent):
        """Test greeting pattern analysis."""
        emails = [
            "Hi John,\nHow are you?",
            "Hello there,\nThanks for reaching out.",
            "Hi team,\nJust a quick update.",
            "Hey Sarah!\nHope you're well."
        ]
        
        greeting = draft_agent._analyze_greetings(emails)
        assert greeting in ["Hi", "Hello", "Hey"]
    
    def test_closing_analysis(self, draft_agent):
        """Test closing pattern analysis."""
        emails = [
            "Looking forward to hearing from you.\nBest regards,\nJohn",
            "Thanks for your time.\nBest,\nJohn",
            "Talk soon!\nCheers,\nJohn",
            "Let me know if you have questions.\nThanks,\nJohn"
        ]
        
        closing = draft_agent._analyze_closings(emails)
        assert closing in ["Best", "Thanks", "Cheers", "Best regards"]
    
    def test_formality_analysis(self, draft_agent):
        """Test formality scoring."""
        formal_emails = [
            "I would like to request a meeting. Please let me know your availability. Sincerely, John",
            "I am writing to inform you about the project status. Kindly review the attached document.",
        ]
        
        casual_emails = [
            "Hey! Just wanted to check in. Let me know if you need anything. Thanks!",
            "Hi there! Hope you're doing well. BTW, the meeting was awesome!"
        ]
        
        formal_score = draft_agent._analyze_formality(formal_emails)
        casual_score = draft_agent._analyze_formality(casual_emails)
        
        assert formal_score > 0.5  # Should score as more formal
        assert casual_score < 0.5  # Should score as more casual
    
    def test_sentence_complexity_analysis(self, draft_agent):
        """Test sentence complexity scoring."""
        simple_emails = [
            "Hi. How are you? I am fine. Thanks.",
            "Let me know. I will help. See you soon."
        ]
        
        complex_emails = [
            "Although I appreciate your comprehensive analysis, I believe we should consider alternative approaches that might be more effective.",
            "While the project has been progressing smoothly, there are several challenges that we need to address before the upcoming deadline."
        ]
        
        simple_score = draft_agent._analyze_sentence_complexity(simple_emails)
        complex_score = draft_agent._analyze_sentence_complexity(complex_emails)
        
        assert complex_score > simple_score  # Complex should score higher


class TestDraftGeneration:
    """Test draft generation functionality."""
    
    @patch('email_agent.agents.draft_agent.OpenAI')
    def test_generate_draft_suggestions_basic(self, mock_openai, draft_agent, sample_incoming_email):
        """Test basic draft generation."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
SUBJECT: Re: Project Status Update Request
BODY: Hi Manager,

Thank you for checking in on the Q4 project. Here's the current status:

1. Progress: We've completed 75% of the core features
2. Blockers: Waiting on API documentation from the external vendor
3. Timeline: On track for November 15th completion

I'll keep you updated on any changes.

Best regards,
Test User
APPROACH: Professional response addressing all requested points with clear structure.
"""
        
        mock_openai.return_value.chat.completions.create.return_value = mock_response
        
        suggestions = draft_agent.generate_draft_suggestions(sample_incoming_email)
        
        assert len(suggestions) > 0
        assert all(isinstance(s, DraftSuggestion) for s in suggestions)
        
        # Check first suggestion
        suggestion = suggestions[0]
        assert suggestion.subject.startswith("Re:")
        assert len(suggestion.body) > 0
        assert 0 <= suggestion.confidence <= 1
        assert 0 <= suggestion.style_match <= 1
        assert suggestion.suggested_tone in ["formal", "casual", "urgent", "friendly", "professional"]
        assert suggestion.estimated_length in ["short", "medium", "long"]
    
    def test_analyze_email_context(self, draft_agent, sample_incoming_email):
        """Test email context analysis."""
        context = draft_agent._analyze_email_context(sample_incoming_email)
        
        assert isinstance(context, dict)
        assert "urgency_level" in context
        assert "response_type_needed" in context
        assert "topic_category" in context
        assert "key_points_to_address" in context
        
        # Should detect questions in the email
        assert context["response_type_needed"] == "answer"
    
    def test_context_analysis_urgent_email(self, draft_agent):
        """Test context analysis for urgent emails."""
        urgent_email = Email(
            id="urgent1",
            message_id="urgent1",
            subject="URGENT: Server Down",
            sender=EmailAddress(email="ops@company.com"),
            recipients=[EmailAddress(email="user@company.com")],
            body_text="Emergency server outage. Need immediate response.",
            date=datetime.now(),
            received_date=datetime.now(),
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.URGENT
        )
        
        context = draft_agent._analyze_email_context(urgent_email)
        assert context["urgency_level"] == "high"
    
    def test_context_analysis_meeting_email(self, draft_agent):
        """Test context analysis for meeting-related emails."""
        meeting_email = Email(
            id="meeting1",
            message_id="meeting1",
            subject="Schedule Team Meeting",
            sender=EmailAddress(email="manager@company.com"),
            recipients=[EmailAddress(email="user@company.com")],
            body_text="We need to schedule a team meeting for next week.",
            date=datetime.now(),
            received_date=datetime.now(),
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL
        )
        
        context = draft_agent._analyze_email_context(meeting_email)
        assert context["topic_category"] == "scheduling"
        assert context["response_type_needed"] == "scheduling"


class TestStyleMatching:
    """Test style matching and confidence scoring."""
    
    def test_calculate_draft_confidence(self, draft_agent):
        """Test draft confidence calculation."""
        context = {
            "key_points_to_address": ["project status", "timeline", "blockers"]
        }
        
        good_draft = "Here's the project status: we're on track. The timeline is November 15th. No major blockers currently."
        poor_draft = "Thanks for your email. I'll get back to you soon."
        
        good_confidence = draft_agent._calculate_draft_confidence(good_draft, context)
        poor_confidence = draft_agent._calculate_draft_confidence(poor_draft, context)
        
        assert good_confidence > poor_confidence
        assert 0 <= good_confidence <= 1
        assert 0 <= poor_confidence <= 1
    
    def test_calculate_style_match(self, draft_agent, sample_sent_emails):
        """Test style matching calculation."""
        # First analyze style
        draft_agent.analyze_writing_style(sample_sent_emails)
        
        # Test drafts with different style matches
        matching_draft = "Hi John,\nThanks for reaching out. I'll get back to you soon.\nBest regards,\nTest"
        non_matching_draft = "Yo! What's up? Talk later!"
        
        matching_score = draft_agent._calculate_style_match(matching_draft)
        non_matching_score = draft_agent._calculate_style_match(non_matching_draft)
        
        assert matching_score >= non_matching_score
        assert 0 <= matching_score <= 1
        assert 0 <= non_matching_score <= 1


class TestUtilityMethods:
    """Test utility methods."""
    
    def test_determine_tone(self, draft_agent):
        """Test tone determination."""
        formal_text = "I would like to kindly request your assistance with this matter."
        casual_text = "Hey! This is awesome, thanks!"
        urgent_text = "URGENT: Need immediate action on this critical issue!"
        friendly_text = "Hope you're doing great! Excited to work with you."
        
        assert draft_agent._determine_tone(formal_text) == "formal"
        assert draft_agent._determine_tone(casual_text) == "casual"
        assert draft_agent._determine_tone(urgent_text) == "urgent"
        assert draft_agent._determine_tone(friendly_text) == "friendly"
    
    def test_estimate_length(self, draft_agent):
        """Test length estimation."""
        short_text = "Thanks for the update."
        medium_text = " ".join(["This is a medium length email."] * 15)
        long_text = " ".join(["This is a very long email with lots of content."] * 30)
        
        assert draft_agent._estimate_length(short_text) == "short"
        assert draft_agent._estimate_length(medium_text) == "medium"
        assert draft_agent._estimate_length(long_text) == "long"
    
    def test_html_to_text(self, draft_agent):
        """Test HTML to text conversion."""
        html = "<p>Hello <strong>world</strong>!</p><br><div>How are you?</div>"
        text = draft_agent._html_to_text(html)
        
        assert "<" not in text
        assert ">" not in text
        assert "Hello world!" in text
        assert "How are you?" in text
    
    def test_extract_common_phrases(self, draft_agent):
        """Test common phrase extraction."""
        emails = [
            "Thanks for reaching out. Let me know if you have any questions.",
            "Thanks for reaching out. Let me know if you need anything else.",
            "I hope this helps. Let me know if you have any questions.",
            "Thanks for your email. Let me know if you need clarification."
        ]
        
        phrases = draft_agent._extract_common_phrases(emails)
        
        assert isinstance(phrases, list)
        # Should find repeated phrases
        # The method returns the actual matched phrases, not just indicators
        assert len(phrases) > 0  # Should find some common phrases


class TestStyleSummary:
    """Test style summary functionality."""
    
    def test_get_style_summary_not_analyzed(self, draft_agent):
        """Test style summary when not analyzed."""
        summary = draft_agent.get_style_summary()
        
        assert summary["status"] == "not_analyzed"
        assert "message" in summary
    
    def test_get_style_summary_analyzed(self, draft_agent, sample_sent_emails):
        """Test style summary after analysis."""
        draft_agent.analyze_writing_style(sample_sent_emails)
        summary = draft_agent.get_style_summary()
        
        assert summary["status"] == "analyzed"
        assert "last_updated" in summary
        assert "avg_length" in summary
        assert "formality_score" in summary
        assert "greeting_style" in summary
        assert "closing_style" in summary
    
    def test_should_refresh_style(self, draft_agent):
        """Test style refresh logic."""
        # Should refresh when not analyzed
        assert draft_agent.should_refresh_style() is True
        
        # Should not refresh immediately after analysis
        draft_agent.last_style_update = datetime.now()
        assert draft_agent.should_refresh_style() is False


if __name__ == "__main__":
    pytest.main([__file__])
