"""Pytest configuration and fixtures for Email Agent tests."""

import asyncio
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from email_agent.storage.database import DatabaseManager
from email_agent.models import (
    Email, EmailAddress, EmailCategory, EmailPriority, 
    EmailRule, RuleCondition, ConnectorConfig
)
from email_agent.agents.crew import EmailAgentCrew


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    # Create database manager with temp path
    db = DatabaseManager(f"sqlite:///{db_path}")
    
    yield db
    
    # Cleanup
    db.close()
    try:
        os.unlink(db_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def sample_emails() -> List[Email]:
    """Create sample emails for testing."""
    return [
        Email(
            id="test-email-1",
            message_id="msg-1",
            subject="Urgent: Server maintenance required",
            sender=EmailAddress(email="admin@company.com", name="System Admin"),
            recipients=[EmailAddress(email="user@company.com", name="User")],
            cc=[],
            bcc=[],
            body_text="The server requires immediate maintenance. Please schedule downtime for tonight.",
            body_html="<p>The server requires immediate maintenance. Please schedule downtime for tonight.</p>",
            attachments=[],
            date=datetime.now() - timedelta(hours=1),
            received_date=datetime.now() - timedelta(hours=1),
            is_read=False,
            is_flagged=True,
            is_draft=False,
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.URGENT,
            tags=["maintenance", "urgent"],
            processed_at=None,
            summary=None,
            action_items=[],
            raw_headers={},
            connector_data={"connector_type": "test"}
        ),
        Email(
            id="test-email-2",
            message_id="msg-2",
            subject="Weekly team meeting notes",
            sender=EmailAddress(email="manager@company.com", name="Team Manager"),
            recipients=[EmailAddress(email="team@company.com", name="Development Team")],
            cc=[],
            bcc=[],
            body_text="Here are the notes from our weekly team meeting. Next meeting is scheduled for Friday.",
            body_html="<p>Here are the notes from our weekly team meeting. Next meeting is scheduled for Friday.</p>",
            attachments=[],
            date=datetime.now() - timedelta(hours=3),
            received_date=datetime.now() - timedelta(hours=3),
            is_read=True,
            is_flagged=False,
            is_draft=False,
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            tags=["meeting", "team"],
            processed_at=datetime.now() - timedelta(hours=2),
            summary="Weekly team meeting notes with next meeting scheduled for Friday.",
            action_items=["Attend Friday meeting"],
            raw_headers={},
            connector_data={"connector_type": "test"}
        ),
        Email(
            id="test-email-3",
            message_id="msg-3",
            subject="Special offer: 50% off premium features",
            sender=EmailAddress(email="noreply@service.com", name="Service Provider"),
            recipients=[EmailAddress(email="user@company.com", name="User")],
            cc=[],
            bcc=[],
            body_text="Limited time offer on our premium features. Upgrade now and save 50%!",
            body_html="<p>Limited time offer on our premium features. Upgrade now and save 50%!</p>",
            attachments=[],
            date=datetime.now() - timedelta(hours=6),
            received_date=datetime.now() - timedelta(hours=6),
            is_read=False,
            is_flagged=False,
            is_draft=False,
            category=EmailCategory.PROMOTIONS,
            priority=EmailPriority.LOW,
            tags=["promotion", "offer"],
            processed_at=None,
            summary=None,
            action_items=[],
            raw_headers={},
            connector_data={"connector_type": "test"}
        )
    ]


@pytest.fixture
def sample_rules() -> List[EmailRule]:
    """Create sample email rules for testing."""
    return [
        EmailRule(
            id="rule-urgent",
            name="Mark urgent emails",
            description="Flag emails with urgent keywords as high priority",
            conditions=[
                RuleCondition(
                    field="subject",
                    operator="contains",
                    value="urgent",
                    case_sensitive=False
                )
            ],
            actions={"set_priority": "urgent", "add_tag": "urgent"},
            enabled=True,
            priority=1
        ),
        EmailRule(
            id="rule-promotion",
            name="Categorize promotions",
            description="Move promotional emails to promotions category",
            conditions=[
                RuleCondition(
                    field="subject",
                    operator="contains",
                    value="offer",
                    case_sensitive=False
                )
            ],
            actions={"set_category": "promotions", "add_tag": "promotion"},
            enabled=True,
            priority=2
        )
    ]


@pytest.fixture
def sample_connector_config() -> ConnectorConfig:
    """Create sample connector configuration for testing."""
    return ConnectorConfig(
        type="test",
        name="Test Connector",
        enabled=True,
        config={
            "test_mode": True,
            "max_emails": 10
        },
        auth_data={},
        sync_frequency=300,
        max_emails=100
    )


@pytest.fixture
async def email_crew():
    """Create an EmailAgentCrew for testing."""
    crew = EmailAgentCrew()
    await crew.initialize_crew({})
    yield crew
    await crew.shutdown()


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for testing."""
    class MockChoice:
        def __init__(self, content: str):
            self.message = MockMessage(content)
    
    class MockMessage:
        def __init__(self, content: str):
            self.content = content
    
    class MockUsage:
        def __init__(self, total_tokens: int = 100):
            self.total_tokens = total_tokens
    
    class MockResponse:
        def __init__(self, content: str, tokens: int = 100):
            self.choices = [MockChoice(content)]
            self.usage = MockUsage(tokens)
    
    return MockResponse


@pytest.fixture
def setup_test_environment():
    """Set up test environment variables."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ.update({
        "EMAIL_AGENT_ENV": "test",
        "DATABASE_URL": "sqlite:///test.db",
        "OPENAI_API_KEY": "test-key",
        "LOG_LEVEL": "DEBUG"
    })
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
