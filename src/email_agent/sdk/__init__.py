"""SDK interfaces for Email Agent extensibility."""

from .base import BaseConnector, BaseRule, BaseCrewAdapter
from .exceptions import ConnectorError, AuthenticationError, RateLimitError

__all__ = [
    "BaseConnector",
    "BaseRule", 
    "BaseCrewAdapter",
    "ConnectorError",
    "AuthenticationError",
    "RateLimitError",
]