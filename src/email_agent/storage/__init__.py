"""Storage layer for Email Agent."""

from .database import DatabaseManager
from .models import EmailORM, EmailThreadORM, EmailRuleORM, ConnectorConfigORM

__all__ = [
    "DatabaseManager",
    "EmailORM",
    "EmailThreadORM", 
    "EmailRuleORM",
    "ConnectorConfigORM",
]