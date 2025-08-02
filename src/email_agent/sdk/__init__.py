"""SDK interfaces for Email Agent extensibility."""

from .base import BaseConnector, BaseCrewAdapter, BaseRule
from .exceptions import AuthenticationError, ConnectorError, RateLimitError

__all__ = [
    "BaseConnector",
    "BaseRule",
    "BaseCrewAdapter",
    "ConnectorError",
    "AuthenticationError",
    "RateLimitError",
]
