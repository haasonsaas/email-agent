"""Storage layer for Email Agent."""

from .database import DatabaseManager
from .models import ConnectorConfigORM, EmailORM, EmailRuleORM, EmailThreadORM

__all__ = [
    "DatabaseManager",
    "EmailORM",
    "EmailThreadORM",
    "EmailRuleORM",
    "ConnectorConfigORM",
]
