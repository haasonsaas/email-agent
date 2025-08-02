"""Core data models for Email Agent."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


class EmailCategory(str, Enum):
    """Email categories based on Gmail's tab model."""

    PRIMARY = "primary"
    SOCIAL = "social"
    PROMOTIONS = "promotions"
    UPDATES = "updates"
    FORUMS = "forums"
    SPAM = "spam"
    UNREAD = "unread"


class EmailPriority(str, Enum):
    """Email priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class EmailAddress(BaseModel):
    """Email address with optional display name."""

    email: str
    name: Optional[str] = None

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.email}>"
        return self.email


class EmailAttachment(BaseModel):
    """Email attachment metadata."""

    filename: str
    content_type: str
    size: int
    content_id: Optional[str] = None
    inline: bool = False


class Email(BaseModel):
    """Core email model."""

    id: str
    message_id: str
    thread_id: Optional[str] = None

    # Headers
    subject: str
    sender: EmailAddress
    recipients: List[EmailAddress] = Field(default_factory=list)
    cc: List[EmailAddress] = Field(default_factory=list)
    bcc: List[EmailAddress] = Field(default_factory=list)
    reply_to: Optional[EmailAddress] = None

    # Content
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    attachments: List[EmailAttachment] = Field(default_factory=list)

    # Metadata
    date: datetime
    received_date: datetime
    is_read: bool = False
    is_flagged: bool = False
    is_draft: bool = False

    # Categorization
    category: EmailCategory = EmailCategory.PRIMARY
    priority: EmailPriority = EmailPriority.NORMAL
    tags: List[str] = Field(default_factory=list)

    # Processing
    processed_at: Optional[datetime] = None
    summary: Optional[str] = None
    action_items: List[str] = Field(default_factory=list)

    # Raw data
    raw_headers: Dict[str, Any] = Field(default_factory=dict)
    connector_data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("date", "received_date", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        if isinstance(v, str):
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        return v


class EmailThread(BaseModel):
    """Email thread containing multiple related emails."""

    id: str
    subject: str
    emails: List[Email] = Field(default_factory=list)
    participants: List[EmailAddress] = Field(default_factory=list)
    last_activity: datetime
    message_count: int = 0
    unread_count: int = 0

    # Categorization
    category: EmailCategory = EmailCategory.PRIMARY
    priority: EmailPriority = EmailPriority.NORMAL
    tags: List[str] = Field(default_factory=list)

    # Summary
    summary: Optional[str] = None
    key_points: List[str] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)


class BriefTemplate(BaseModel):
    """Template for daily brief generation."""

    headline: str
    bullets: List[str] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)
    deadlines: List[str] = Field(default_factory=list)
    key_threads: List[str] = Field(default_factory=list)
    statistics: Dict[str, Union[int, str]] = Field(default_factory=dict)


class DailyBrief(BaseModel):
    """Daily email brief summary."""

    date: datetime
    total_emails: int
    unread_emails: int
    categories: Dict[EmailCategory, int] = Field(default_factory=dict)
    priorities: Dict[EmailPriority, int] = Field(default_factory=dict)

    # Content
    headline: str
    summary: str
    key_threads: List[EmailThread] = Field(default_factory=list)
    action_items: List[str] = Field(default_factory=list)
    deadlines: List[str] = Field(default_factory=list)

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.now)
    model_used: Optional[str] = None
    processing_time: Optional[float] = None


class RuleCondition(BaseModel):
    """Condition for email categorization rules."""

    field: str  # subject, sender, body, etc.
    operator: str  # contains, equals, regex, etc.
    value: str
    case_sensitive: bool = False


class EmailRule(BaseModel):
    """Email categorization rule."""

    id: str
    name: str
    description: Optional[str] = None
    conditions: List[RuleCondition]
    actions: Dict[str, Any]  # category, priority, tags, etc.
    enabled: bool = True
    priority: int = 0  # Lower numbers have higher priority

    created_at: datetime = Field(default_factory=datetime.now)
    last_modified: datetime = Field(default_factory=datetime.now)


class ConnectorConfig(BaseModel):
    """Configuration for email connectors."""

    type: str  # gmail, outlook, imap
    name: str
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    auth_data: Dict[str, Any] = Field(default_factory=dict)

    last_sync: Optional[datetime] = None
    sync_frequency: int = 300  # seconds
    max_emails: int = 1000
