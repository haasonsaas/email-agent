"""Base interfaces for Email Agent SDK."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import Email, EmailRule, BriefTemplate


class BaseAgent(ABC):
    """Base class for Email Agent components."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.stats = {}
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        pass
    
    async def shutdown(self) -> None:
        """Shutdown the agent."""
        pass


class BaseConnector(ABC):
    """Base class for email connectors."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.authenticated = False
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate with the email service."""
        pass
    
    @abstractmethod
    async def pull(self, since: Optional[datetime] = None) -> List[Email]:
        """Pull emails from the service since given datetime."""
        pass
    
    @abstractmethod
    async def get_email(self, email_id: str) -> Optional[Email]:
        """Get a specific email by ID."""
        pass
    
    @abstractmethod
    async def mark_read(self, email_id: str) -> bool:
        """Mark an email as read."""
        pass
    
    @abstractmethod
    async def mark_unread(self, email_id: str) -> bool:
        """Mark an email as unread."""
        pass
    
    @abstractmethod
    async def archive(self, email_id: str) -> bool:
        """Archive an email."""
        pass
    
    @abstractmethod
    async def delete(self, email_id: str) -> bool:
        """Delete an email."""
        pass
    
    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Return the connector type identifier."""
        pass
    
    @property
    @abstractmethod
    def supports_push(self) -> bool:
        """Return whether the connector supports push notifications."""
        pass


class BaseRule(ABC):
    """Base class for email categorization rules."""
    
    def __init__(self, rule_config: EmailRule) -> None:
        self.rule_config = rule_config
    
    @abstractmethod
    def applies(self, email: Email) -> bool:
        """Check if this rule applies to the given email."""
        pass
    
    @abstractmethod
    def execute(self, email: Email) -> Email:
        """Execute the rule actions on the email."""
        pass
    
    @property
    def priority(self) -> int:
        """Return the rule priority (lower = higher priority)."""
        return self.rule_config.priority
    
    @property
    def enabled(self) -> bool:
        """Return whether the rule is enabled."""
        return self.rule_config.enabled


class BaseCrewAdapter(ABC):
    """Base class for multi-agent orchestration adapters."""
    
    @abstractmethod
    async def initialize_crew(self, agents_config: Dict[str, Any]) -> None:
        """Initialize the agent crew."""
        pass
    
    @abstractmethod
    async def execute_task(self, task_name: str, **kwargs: Any) -> Any:
        """Execute a task using the agent crew."""
        pass
    
    @abstractmethod
    async def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """Get the status of a specific agent."""
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """Shutdown the agent crew."""
        pass


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
    
    @abstractmethod
    async def generate_summary(self, emails: List[Email]) -> str:
        """Generate a summary of the given emails."""
        pass
    
    @abstractmethod
    async def generate_brief(self, emails: List[Email]) -> BriefTemplate:
        """Generate a daily brief from the given emails."""
        pass
    
    @abstractmethod
    async def extract_action_items(self, email: Email) -> List[str]:
        """Extract action items from an email."""
        pass
    
    @abstractmethod
    async def categorize_email(self, email: Email) -> str:
        """Categorize an email using ML."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name being used."""
        pass