"""Tests for data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.email_agent.models import (
    Email, EmailAddress, EmailAttachment, EmailCategory, EmailPriority,
    EmailRule, RuleCondition, ConnectorConfig, DailyBrief
)


class TestEmailAddress:
    """Test EmailAddress model."""

    def test_email_address_creation(self):
        """Test creating an email address."""
        addr = EmailAddress(email="test@example.com", name="Test User")
        assert addr.email == "test@example.com"
        assert addr.name == "Test User"

    def test_email_address_without_name(self):
        """Test creating an email address without name."""
        addr = EmailAddress(email="test@example.com")
        assert addr.email == "test@example.com"
        assert addr.name is None

    def test_email_address_validation(self):
        """Test email address validation."""
        # Valid email
        addr = EmailAddress(email="valid@example.com")
        assert addr.email == "valid@example.com"
        
        # Invalid email should still work (basic validation)
        # Pydantic's email validation might be more lenient

    def test_email_address_string_representation(self):
        """Test string representation of email address."""
        addr = EmailAddress(email="test@example.com", name="Test User")
        str_repr = str(addr)
        assert "test@example.com" in str_repr


class TestEmailAttachment:
    """Test EmailAttachment model."""

    def test_attachment_creation(self):
        """Test creating an email attachment."""
        attachment = EmailAttachment(
            filename="document.pdf",
            content_type="application/pdf",
            size=1024,
            content_id="attach1"
        )
        assert attachment.filename == "document.pdf"
        assert attachment.content_type == "application/pdf"
        assert attachment.size == 1024

    def test_attachment_without_optional_fields(self):
        """Test creating attachment without optional fields."""
        attachment = EmailAttachment(
            filename="file.txt",
            content_type="text/plain",
            size=100
        )
        assert attachment.filename == "file.txt"
        assert attachment.content_type == "text/plain"
        assert attachment.size == 100


class TestEmail:
    """Test Email model."""

    def test_email_creation(self):
        """Test creating a complete email."""
        email = Email(
            id="test-1",
            message_id="msg-1",
            subject="Test Subject",
            sender=EmailAddress(email="sender@example.com"),
            recipients=[EmailAddress(email="recipient@example.com")],
            cc=[],
            bcc=[],
            body_text="Test body",
            body_html="<p>Test body</p>",
            attachments=[],
            date=datetime.now(),
            received_date=datetime.now(),
            is_read=False,
            is_flagged=False,
            is_draft=False,
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            tags=[],
            raw_headers={},
            connector_data={}
        )
        
        assert email.id == "test-1"
        assert email.subject == "Test Subject"
        assert email.category == EmailCategory.PRIMARY
        assert email.priority == EmailPriority.NORMAL

    def test_email_with_attachments(self):
        """Test email with attachments."""
        attachment = EmailAttachment(
            filename="test.pdf", 
            content_type="application/pdf",
            size=1024
        )
        
        email = Email(
            id="test-1",
            message_id="msg-1",
            subject="Test with Attachment",
            sender=EmailAddress(email="sender@example.com"),
            recipients=[EmailAddress(email="recipient@example.com")],
            cc=[],
            bcc=[],
            attachments=[attachment],
            date=datetime.now(),
            received_date=datetime.now(),
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.NORMAL,
            raw_headers={},
            connector_data={}
        )
        
        assert len(email.attachments) == 1
        assert email.attachments[0].filename == "test.pdf"

    def test_email_validation(self):
        """Test email validation."""
        # Missing required fields should raise ValidationError
        with pytest.raises(ValidationError):
            Email(id="test")  # Missing many required fields

    def test_email_categories(self):
        """Test email category enum."""
        assert EmailCategory.PRIMARY.value == "primary"
        assert EmailCategory.SOCIAL.value == "social"
        assert EmailCategory.PROMOTIONS.value == "promotions"
        assert EmailCategory.UPDATES.value == "updates"
        assert EmailCategory.FORUMS.value == "forums"

    def test_email_priorities(self):
        """Test email priority enum."""
        assert EmailPriority.LOW.value == "low"
        assert EmailPriority.NORMAL.value == "normal"
        assert EmailPriority.HIGH.value == "high"
        assert EmailPriority.URGENT.value == "urgent"


class TestRuleCondition:
    """Test RuleCondition model."""

    def test_rule_condition_creation(self):
        """Test creating a rule condition."""
        condition = RuleCondition(
            field="subject",
            operator="contains",
            value="urgent",
            case_sensitive=False
        )
        
        assert condition.field == "subject"
        assert condition.operator == "contains"
        assert condition.value == "urgent"
        assert condition.case_sensitive is False

    def test_rule_condition_defaults(self):
        """Test rule condition with defaults."""
        condition = RuleCondition(
            field="from",
            operator="equals",
            value="admin@company.com"
        )
        
        assert condition.case_sensitive is False  # Default value


class TestEmailRule:
    """Test EmailRule model."""

    def test_rule_creation(self):
        """Test creating an email rule."""
        condition = RuleCondition(
            field="subject",
            operator="contains",
            value="urgent"
        )
        
        rule = EmailRule(
            id="rule-1",
            name="Urgent Rule",
            description="Mark urgent emails",
            conditions=[condition],
            actions={"set_priority": "urgent"},
            enabled=True,
            priority=1
        )
        
        assert rule.id == "rule-1"
        assert rule.name == "Urgent Rule"
        assert len(rule.conditions) == 1
        assert rule.actions["set_priority"] == "urgent"
        assert rule.enabled is True

    def test_rule_with_multiple_conditions(self):
        """Test rule with multiple conditions."""
        conditions = [
            RuleCondition(field="subject", operator="contains", value="urgent"),
            RuleCondition(field="from", operator="contains", value="admin")
        ]
        
        rule = EmailRule(
            id="complex-rule",
            name="Complex Rule",
            conditions=conditions,
            actions={"set_priority": "urgent", "add_tag": "admin"},
            enabled=True,
            priority=1
        )
        
        assert len(rule.conditions) == 2
        assert len(rule.actions) == 2

    def test_rule_validation(self):
        """Test rule validation."""
        with pytest.raises(ValidationError):
            EmailRule(id="test")  # Missing required fields


class TestConnectorConfig:
    """Test ConnectorConfig model."""

    def test_connector_config_creation(self):
        """Test creating a connector configuration."""
        config = ConnectorConfig(
            type="gmail",
            name="Gmail Connector",
            enabled=True,
            config={
                "credentials_file": "creds.json",
                "scopes": ["gmail.readonly"]
            },
            auth_data={},
            sync_frequency=300,
            max_emails=100
        )
        
        assert config.type == "gmail"
        assert config.name == "Gmail Connector"
        assert config.enabled is True
        assert config.sync_frequency == 300

    def test_connector_config_defaults(self):
        """Test connector configuration with defaults."""
        config = ConnectorConfig(
            type="test",
            name="Test Connector"
        )
        
        assert config.enabled is True  # Default value
        assert config.config == {}     # Default value
        assert config.auth_data == {}  # Default value


class TestDailyBrief:
    """Test DailyBrief model."""

    def test_brief_creation(self):
        """Test creating a daily brief."""
        brief = DailyBrief(
            date=datetime.now(),
            total_emails=10,
            unread_emails=5,
            categories={"primary": 3, "social": 2},
            priorities={"urgent": 1, "normal": 9},
            headline="Daily Email Summary",
            summary="You have 10 emails today with 5 unread.",
            key_threads=[],
            action_items=["Review urgent email"],
            deadlines=[]
        )
        
        assert brief.total_emails == 10
        assert brief.unread_emails == 5
        assert brief.headline == "Daily Email Summary"
        assert len(brief.action_items) == 1

    def test_brief_validation(self):
        """Test brief validation."""
        with pytest.raises(ValidationError):
            DailyBrief()  # Missing required fields

    def test_brief_with_metrics(self):
        """Test brief with processing metrics."""
        brief = DailyBrief(
            date=datetime.now(),
            total_emails=5,
            unread_emails=2,
            categories={},
            priorities={},
            headline="Test Brief",
            summary="Test summary",
            key_threads=[],
            action_items=[],
            deadlines=[],
            generated_at=datetime.now(),
            model_used="gpt-4o-mini",
            processing_time=1.5
        )
        
        assert brief.model_used == "gpt-4o-mini"
        assert brief.processing_time == 1.5
        assert brief.generated_at is not None


class TestModelIntegration:
    """Test model integration and relationships."""

    def test_email_with_complex_data(self):
        """Test email with complex nested data."""
        email = Email(
            id="complex-email",
            message_id="msg-complex",
            subject="Complex Test Email",
            sender=EmailAddress(email="sender@example.com", name="Test Sender"),
            recipients=[
                EmailAddress(email="user1@example.com", name="User One"),
                EmailAddress(email="user2@example.com", name="User Two")
            ],
            cc=[EmailAddress(email="cc@example.com")],
            bcc=[EmailAddress(email="bcc@example.com")],
            attachments=[
                EmailAttachment(filename="doc1.pdf", content_type="application/pdf", size=1024),
                EmailAttachment(filename="doc2.txt", content_type="text/plain", size=512)
            ],
            date=datetime.now(),
            received_date=datetime.now(),
            category=EmailCategory.PRIMARY,
            priority=EmailPriority.HIGH,
            tags=["important", "project"],
            summary="This is a test email summary",
            action_items=["Review documents", "Schedule meeting"],
            raw_headers={"X-Custom": "value"},
            connector_data={"source": "test", "thread_id": "123"}
        )
        
        assert len(email.recipients) == 2
        assert len(email.attachments) == 2
        assert len(email.tags) == 2
        assert len(email.action_items) == 2
        assert email.raw_headers["X-Custom"] == "value"

    def test_model_serialization(self):
        """Test model serialization to dict."""
        addr = EmailAddress(email="test@example.com", name="Test")
        addr_dict = addr.model_dump()
        
        assert addr_dict["email"] == "test@example.com"
        assert addr_dict["name"] == "Test"

    def test_model_json_serialization(self):
        """Test model JSON serialization."""
        addr = EmailAddress(email="test@example.com", name="Test")
        json_str = addr.model_dump_json()
        
        assert "test@example.com" in json_str
        assert "Test" in json_str
