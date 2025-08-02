"""SQLAlchemy ORM models for Email Agent storage."""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class EmailORM(Base):
    """ORM model for email storage."""

    __tablename__ = "emails"

    # Primary keys
    id = Column(String, primary_key=True)
    message_id = Column(String, nullable=False, index=True)
    thread_id = Column(String, ForeignKey("email_threads.id"), index=True)

    # Headers
    subject = Column(Text, nullable=False)
    sender_email = Column(String, nullable=False, index=True)
    sender_name = Column(String)
    recipients = Column(JSON)  # List of EmailAddress dicts
    cc = Column(JSON)  # List of EmailAddress dicts
    bcc = Column(JSON)  # List of EmailAddress dicts
    reply_to_email = Column(String)
    reply_to_name = Column(String)

    # Content
    body_text = Column(Text)
    body_html = Column(Text)
    attachments = Column(JSON)  # List of EmailAttachment dicts

    # Metadata
    date = Column(DateTime, nullable=False, index=True)
    received_date = Column(DateTime, nullable=False, index=True)
    is_read = Column(Boolean, default=False, index=True)
    is_flagged = Column(Boolean, default=False, index=True)
    is_draft = Column(Boolean, default=False)

    # Categorization
    category = Column(String, nullable=False, index=True)
    priority = Column(String, nullable=False, index=True)
    tags = Column(JSON)  # List of strings

    # Processing
    processed_at = Column(DateTime)
    summary = Column(Text)
    action_items = Column(JSON)  # List of strings

    # Raw data
    raw_headers = Column(JSON)
    connector_data = Column(JSON)
    connector_type = Column(String, nullable=False, index=True)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    thread = relationship("EmailThreadORM", back_populates="emails")


class EmailThreadORM(Base):
    """ORM model for email thread storage."""

    __tablename__ = "email_threads"

    id = Column(String, primary_key=True)
    subject = Column(Text, nullable=False)
    participants = Column(JSON)  # List of EmailAddress dicts
    last_activity = Column(DateTime, nullable=False, index=True)
    message_count = Column(Integer, default=0)
    unread_count = Column(Integer, default=0)

    # Categorization
    category = Column(String, nullable=False, index=True)
    priority = Column(String, nullable=False, index=True)
    tags = Column(JSON)  # List of strings

    # Summary
    summary = Column(Text)
    key_points = Column(JSON)  # List of strings
    action_items = Column(JSON)  # List of strings

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    emails = relationship("EmailORM", back_populates="thread")


class EmailRuleORM(Base):
    """ORM model for email rules storage."""

    __tablename__ = "email_rules"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    conditions = Column(JSON, nullable=False)  # List of RuleCondition dicts
    actions = Column(JSON, nullable=False)  # Dict of actions
    enabled = Column(Boolean, default=True, index=True)
    priority = Column(Integer, default=0, index=True)

    # Statistics
    match_count = Column(Integer, default=0)
    last_matched = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class ConnectorConfigORM(Base):
    """ORM model for connector configuration storage."""

    __tablename__ = "connector_configs"

    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    enabled = Column(Boolean, default=True, index=True)
    config = Column(JSON)  # Configuration dict
    auth_data = Column(JSON)  # Authentication data (encrypted)

    # Sync metadata
    last_sync = Column(DateTime)
    sync_frequency = Column(Integer, default=300)  # seconds
    max_emails = Column(Integer, default=1000)

    # Statistics
    total_emails_synced = Column(Integer, default=0)
    last_error = Column(Text)
    error_count = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    sync_logs = relationship("SyncLogORM", back_populates="connector")


class DailyBriefORM(Base):
    """ORM model for daily brief storage."""

    __tablename__ = "daily_briefs"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False, unique=True, index=True)
    total_emails = Column(Integer, nullable=False)
    unread_emails = Column(Integer, nullable=False)
    categories = Column(JSON)  # Dict of category counts
    priorities = Column(JSON)  # Dict of priority counts

    # Content
    headline = Column(Text, nullable=False)
    summary = Column(Text, nullable=False)
    key_threads = Column(JSON)  # List of thread IDs
    action_items = Column(JSON)  # List of strings
    deadlines = Column(JSON)  # List of strings

    # Metadata
    generated_at = Column(DateTime, default=func.now())
    model_used = Column(String)
    processing_time = Column(Float)  # seconds

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class SyncLogORM(Base):
    """ORM model for sync operation logging."""

    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True)
    connector_id = Column(Integer, ForeignKey("connector_configs.id"), nullable=False)
    started_at = Column(DateTime, nullable=False, default=func.now())
    completed_at = Column(DateTime)

    # Results
    emails_processed = Column(Integer, default=0)
    emails_new = Column(Integer, default=0)
    emails_updated = Column(Integer, default=0)
    errors_count = Column(Integer, default=0)

    # Status
    status = Column(
        String, nullable=False, default="running"
    )  # running, completed, failed
    error_message = Column(Text)

    # Relationship
    connector = relationship("ConnectorConfigORM", back_populates="sync_logs")


class UserPreferencesORM(Base):
    """ORM model for user preferences."""

    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True)
    key = Column(String, nullable=False, unique=True)
    value = Column(JSON, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
