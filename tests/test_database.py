"""Tests for database operations."""

import pytest
from datetime import datetime, timedelta

from email_agent.models import EmailCategory, EmailPriority


class TestDatabaseManager:
    """Test database operations."""

    def test_database_initialization(self, temp_db):
        """Test database initialization."""
        assert temp_db is not None
        session = temp_db.get_session()
        assert session is not None
        session.close()

    def test_save_and_retrieve_email(self, temp_db, sample_emails):
        """Test saving and retrieving emails."""
        email = sample_emails[0]
        
        # Save email
        success = temp_db.save_email(email)
        assert success is True
        
        # Retrieve email
        retrieved = temp_db.get_email(email.id)
        assert retrieved is not None
        assert retrieved.id == email.id
        assert retrieved.subject == email.subject
        assert retrieved.sender.email == email.sender.email

    def test_save_multiple_emails(self, temp_db, sample_emails):
        """Test saving multiple emails."""
        saved_count = temp_db.save_emails(sample_emails)
        assert saved_count == len(sample_emails)
        
        # Verify all emails were saved
        for email in sample_emails:
            retrieved = temp_db.get_email(email.id)
            assert retrieved is not None

    def test_get_emails_with_filters(self, temp_db, sample_emails):
        """Test retrieving emails with various filters."""
        # Save test emails
        temp_db.save_emails(sample_emails)
        
        # Test category filter
        primary_emails = temp_db.get_emails(category=EmailCategory.PRIMARY)
        assert len(primary_emails) == 2
        
        # Test unread filter
        unread_emails = temp_db.get_emails(is_unread=True)
        assert len(unread_emails) == 2
        
        # Test sender filter
        admin_emails = temp_db.get_emails(sender="admin@company.com")
        assert len(admin_emails) == 1
        
        # Test search filter
        urgent_emails = temp_db.get_emails(search="urgent")
        assert len(urgent_emails) == 1

    def test_email_stats(self, temp_db, sample_emails):
        """Test email statistics generation."""
        # Save test emails
        temp_db.save_emails(sample_emails)
        
        stats = temp_db.get_email_stats()
        
        assert stats["total"] == 3
        assert stats["unread"] == 2
        assert stats["flagged"] == 1
        assert stats["categories"]["primary"] == 2
        assert stats["categories"]["promotions"] == 1

    def test_save_and_retrieve_rules(self, temp_db, sample_rules):
        """Test saving and retrieving email rules."""
        rule = sample_rules[0]
        
        # Save rule
        success = temp_db.save_rule(rule)
        assert success is True
        
        # Retrieve rules
        rules = temp_db.get_rules()
        assert len(rules) >= 1
        
        saved_rule = next((r for r in rules if r.id == rule.id), None)
        assert saved_rule is not None
        assert saved_rule.name == rule.name

    def test_connector_config_operations(self, temp_db, sample_connector_config):
        """Test connector configuration operations."""
        config = sample_connector_config
        
        # Save config
        success = temp_db.save_connector_config(config)
        assert success is True
        
        # Retrieve configs
        configs = temp_db.get_connector_configs()
        assert len(configs) >= 1
        
        saved_config = configs[0]
        assert saved_config.type == config.type
        assert saved_config.name == config.name

    def test_database_pagination(self, temp_db, sample_emails):
        """Test database pagination."""
        # Create more emails for pagination testing
        emails = []
        for i in range(30):  # Create 30 unique emails
            base_email = sample_emails[i % len(sample_emails)]
            email = base_email.model_copy(deep=True)
            email.id = f"test-email-{i}"
            email.message_id = f"msg-{i}"
            emails.append(email)
        
        temp_db.save_emails(emails)
        
        # Test pagination
        page1 = temp_db.get_emails(limit=10, offset=0)
        page2 = temp_db.get_emails(limit=10, offset=10)
        page3 = temp_db.get_emails(limit=10, offset=20)
        
        assert len(page1) == 10
        assert len(page2) == 10
        assert len(page3) == 10
        
        # Ensure pages don't overlap
        page1_ids = {e.id for e in page1}
        page2_ids = {e.id for e in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_date_range_filtering(self, temp_db, sample_emails):
        """Test filtering emails by date range."""
        temp_db.save_emails(sample_emails)
        
        # Filter by date range
        since = datetime.now() - timedelta(hours=2)
        until = datetime.now()
        
        recent_emails = temp_db.get_emails(since=since, until=until)
        assert len(recent_emails) >= 1

    def test_email_update(self, temp_db, sample_emails):
        """Test updating existing emails."""
        email = sample_emails[0]
        
        # Save original email
        temp_db.save_email(email)
        
        # Update email
        email.summary = "Updated summary"
        email.action_items = ["Updated action"]
        email.processed_at = datetime.now()
        
        # Save updated email
        success = temp_db.save_email(email)
        assert success is True
        
        # Verify update
        retrieved = temp_db.get_email(email.id)
        assert retrieved.summary == "Updated summary"
        assert retrieved.action_items == ["Updated action"]
        assert retrieved.processed_at is not None
