"""Exceptions for Email Agent SDK."""


class EmailAgentException(Exception):
    """Base exception for Email Agent."""

    pass


class ConnectorError(EmailAgentException):
    """Error in email connector operation."""

    pass


class AuthenticationError(ConnectorError):
    """Authentication failure in connector."""

    pass


class RateLimitError(ConnectorError):
    """Rate limit exceeded in connector."""

    pass


class StorageError(EmailAgentException):
    """Error in storage operations."""

    pass


class RuleError(EmailAgentException):
    """Error in rule processing."""

    pass


class AgentError(EmailAgentException):
    """Error in agent operations."""

    pass
