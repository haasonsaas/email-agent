"""Database management for Email Agent."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, asc, create_engine, desc, func, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..models import (
    ConnectorConfig,
    Email,
    EmailAddress,
    EmailAttachment,
    EmailCategory,
    EmailPriority,
    EmailRule,
)
from ..sdk.exceptions import StorageError
from .models import Base, ConnectorConfigORM, EmailORM, EmailRuleORM

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Database manager for Email Agent storage operations."""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.database_url
        self._engine = None
        self._session_factory = None
        self._setup_database()

    def _setup_database(self) -> None:
        """Set up database connection and create tables."""
        try:
            # Ensure data directory exists
            if self.database_url.startswith("sqlite:///"):
                db_path = Path(self.database_url.replace("sqlite:///", ""))
                db_path = db_path.expanduser()
                db_path.parent.mkdir(parents=True, exist_ok=True)
                self.database_url = f"sqlite:///{db_path}"

            # Create engine
            self._engine = create_engine(
                self.database_url,
                echo=settings.log_level.upper() == "DEBUG",
                pool_pre_ping=True,
            )

            # Create session factory
            self._session_factory = sessionmaker(bind=self._engine)

            # Create tables
            Base.metadata.create_all(self._engine)

            logger.info(f"Database initialized: {self.database_url}")

        except Exception as e:
            raise StorageError(f"Failed to initialize database: {str(e)}")

    def get_session(self) -> Session:
        """Get a new database session."""
        return self._session_factory()

    def close(self) -> None:
        """Close database connections."""
        if self._engine:
            self._engine.dispose()

    # Email operations

    def save_email(self, email: Email) -> bool:
        """Save an email to the database."""
        try:
            with self.get_session() as session:
                email_orm = self._email_to_orm(email)
                session.merge(email_orm)  # Use merge to handle updates
                session.commit()
                return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to save email {email.id}: {str(e)}")
            return False

    def save_emails(self, emails: List[Email]) -> int:
        """Save multiple emails to the database. Returns count of saved emails."""
        if not emails:
            return 0

        try:
            with self.get_session() as session:
                saved_count = 0
                for email in emails:
                    try:
                        email_orm = self._email_to_orm(email)
                        session.merge(email_orm)
                        saved_count += 1
                    except Exception as e:
                        logger.error(f"Failed to prepare email {email.id}: {str(e)}")
                        continue

                session.commit()
                logger.info(f"Saved {saved_count} of {len(emails)} emails")
                return saved_count

        except SQLAlchemyError as e:
            logger.error(f"Failed to save emails batch: {str(e)}")
            return 0

    def get_email(self, email_id: str) -> Optional[Email]:
        """Get an email by ID."""
        try:
            with self.get_session() as session:
                email_orm = (
                    session.query(EmailORM).filter(EmailORM.id == email_id).first()
                )
                return self._orm_to_email(email_orm) if email_orm else None
        except SQLAlchemyError as e:
            logger.error(f"Failed to get email {email_id}: {str(e)}")
            return None

    def get_emails(
        self,
        limit: int = 100,
        offset: int = 0,
        category: Optional[EmailCategory] = None,
        is_unread: Optional[bool] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        sender: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Email]:
        """Get emails with filtering and pagination."""
        try:
            with self.get_session() as session:
                query = session.query(EmailORM)

                # Apply filters
                if category:
                    query = query.filter(EmailORM.category == category.value)

                if is_unread is not None:
                    query = query.filter(EmailORM.is_read != is_unread)

                if since:
                    query = query.filter(EmailORM.date >= since)

                if until:
                    query = query.filter(EmailORM.date <= until)

                if sender:
                    query = query.filter(EmailORM.sender_email.ilike(f"%{sender}%"))

                if search:
                    search_filter = or_(
                        EmailORM.subject.ilike(f"%{search}%"),
                        EmailORM.body_text.ilike(f"%{search}%"),
                        EmailORM.sender_email.ilike(f"%{search}%"),
                    )
                    query = query.filter(search_filter)

                # Order by date (newest first)
                query = query.order_by(desc(EmailORM.date))

                # Apply pagination
                email_orms = query.offset(offset).limit(limit).all()

                return [self._orm_to_email(orm) for orm in email_orms]

        except SQLAlchemyError as e:
            logger.error(f"Failed to get emails: {str(e)}")
            return []

    def get_sent_emails(
        self, limit: int = 100, user_email: Optional[str] = None
    ) -> List[Email]:
        """Get sent emails for writing style analysis."""
        try:
            with self.get_session() as session:
                query = session.query(EmailORM)

                # Filter for sent emails (drafts or emails from specific sender)
                if user_email:
                    # If we know the user's email, filter by sender
                    query = query.filter(EmailORM.sender_email == user_email)
                else:
                    # Otherwise, look for drafts or emails from known personal domains
                    # This is a heuristic - in practice, you'd want to configure this
                    query = query.filter(
                        or_(
                            EmailORM.is_draft,
                            EmailORM.sender_email.like(
                                "%@gmail.com"
                            ),  # Common personal domains
                            EmailORM.sender_email.like("%@outlook.com"),
                            EmailORM.sender_email.like("%@yahoo.com"),
                            EmailORM.sender_email.like("%@icloud.com"),
                        )
                    )

                # Filter for substantial content (not auto-replies or very short emails)
                query = query.filter(
                    and_(
                        EmailORM.body_text.isnot(None),
                        func.length(EmailORM.body_text) > 50,  # At least 50 characters
                    )
                )

                # Order by date (newest first)
                query = query.order_by(desc(EmailORM.date))

                # Apply limit
                email_orms = query.limit(limit).all()

                return [self._orm_to_email(orm) for orm in email_orms]

        except SQLAlchemyError as e:
            logger.error(f"Failed to get sent emails: {str(e)}")
            return []

    def get_email_stats(self) -> Dict[str, Any]:
        """Get email statistics."""
        try:
            with self.get_session() as session:
                total = session.query(EmailORM).count()
                unread = session.query(EmailORM).filter(not EmailORM.is_read).count()
                flagged = session.query(EmailORM).filter(EmailORM.is_flagged).count()

                # Category counts
                category_counts = {}
                for category in EmailCategory:
                    count = (
                        session.query(EmailORM)
                        .filter(EmailORM.category == category.value)
                        .count()
                    )
                    category_counts[category.value] = count

                return {
                    "total": total,
                    "unread": unread,
                    "flagged": flagged,
                    "categories": category_counts,
                }

        except SQLAlchemyError as e:
            logger.error(f"Failed to get email stats: {str(e)}")
            return {}

    # Rule operations

    def save_rule(self, rule: EmailRule) -> bool:
        """Save an email rule."""
        try:
            with self.get_session() as session:
                rule_orm = self._rule_to_orm(rule)
                session.merge(rule_orm)
                session.commit()
                return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to save rule {rule.id}: {str(e)}")
            return False

    def get_rules(self, enabled_only: bool = True) -> List[EmailRule]:
        """Get email rules, optionally only enabled ones."""
        try:
            with self.get_session() as session:
                query = session.query(EmailRuleORM)
                if enabled_only:
                    query = query.filter(EmailRuleORM.enabled)

                query = query.order_by(asc(EmailRuleORM.priority))
                rule_orms = query.all()

                return [self._orm_to_rule(orm) for orm in rule_orms]

        except SQLAlchemyError as e:
            logger.error(f"Failed to get rules: {str(e)}")
            return []

    def delete_rule(self, rule_id: str) -> bool:
        """Delete an email rule."""
        try:
            with self.get_session() as session:
                rule = (
                    session.query(EmailRuleORM)
                    .filter(EmailRuleORM.id == rule_id)
                    .first()
                )
                if rule:
                    session.delete(rule)
                    session.commit()
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete rule {rule_id}: {str(e)}")
            return False

    # Connector operations

    def save_connector_config(self, config: ConnectorConfig) -> bool:
        """Save connector configuration."""
        try:
            with self.get_session() as session:
                config_orm = self._connector_config_to_orm(config)
                session.merge(config_orm)
                session.commit()
                return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to save connector config: {str(e)}")
            return False

    def get_connector_configs(self, enabled_only: bool = True) -> List[ConnectorConfig]:
        """Get connector configurations."""
        try:
            with self.get_session() as session:
                query = session.query(ConnectorConfigORM)
                if enabled_only:
                    query = query.filter(ConnectorConfigORM.enabled)

                config_orms = query.all()
                return [self._orm_to_connector_config(orm) for orm in config_orms]

        except SQLAlchemyError as e:
            logger.error(f"Failed to get connector configs: {str(e)}")
            return []

    # Utility methods

    def _email_to_orm(self, email: Email) -> EmailORM:
        """Convert Email model to ORM."""
        return EmailORM(
            id=email.id,
            message_id=email.message_id,
            thread_id=email.thread_id,
            subject=email.subject,
            sender_email=email.sender.email,
            sender_name=email.sender.name,
            recipients=[addr.model_dump() for addr in email.recipients],
            cc=[addr.model_dump() for addr in email.cc],
            bcc=[addr.model_dump() for addr in email.bcc],
            reply_to_email=email.reply_to.email if email.reply_to else None,
            reply_to_name=email.reply_to.name if email.reply_to else None,
            body_text=email.body_text,
            body_html=email.body_html,
            attachments=[att.model_dump() for att in email.attachments],
            date=email.date,
            received_date=email.received_date,
            is_read=email.is_read,
            is_flagged=email.is_flagged,
            is_draft=email.is_draft,
            category=email.category.value,
            priority=email.priority.value,
            tags=email.tags,
            processed_at=email.processed_at,
            summary=email.summary,
            action_items=email.action_items,
            raw_headers=email.raw_headers,
            connector_data=email.connector_data,
            connector_type=email.connector_data.get("connector_type", "unknown"),
        )

    def _orm_to_email(self, orm: EmailORM) -> Email:
        """Convert ORM to Email model."""
        return Email(
            id=orm.id,
            message_id=orm.message_id,
            thread_id=orm.thread_id,
            subject=orm.subject,
            sender=EmailAddress(email=orm.sender_email, name=orm.sender_name),
            recipients=[EmailAddress(**addr) for addr in (orm.recipients or [])],
            cc=[EmailAddress(**addr) for addr in (orm.cc or [])],
            bcc=[EmailAddress(**addr) for addr in (orm.bcc or [])],
            reply_to=(
                EmailAddress(email=orm.reply_to_email, name=orm.reply_to_name)
                if orm.reply_to_email
                else None
            ),
            body_text=orm.body_text,
            body_html=orm.body_html,
            attachments=[EmailAttachment(**att) for att in (orm.attachments or [])],
            date=orm.date,
            received_date=orm.received_date,
            is_read=orm.is_read,
            is_flagged=orm.is_flagged,
            is_draft=orm.is_draft,
            category=EmailCategory(orm.category),
            priority=EmailPriority(orm.priority),
            tags=orm.tags or [],
            processed_at=orm.processed_at,
            summary=orm.summary,
            action_items=orm.action_items or [],
            raw_headers=orm.raw_headers or {},
            connector_data=orm.connector_data or {},
        )

    def _rule_to_orm(self, rule: EmailRule) -> EmailRuleORM:
        """Convert EmailRule to ORM."""
        return EmailRuleORM(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            conditions=[cond.model_dump() for cond in rule.conditions],
            actions=rule.actions,
            enabled=rule.enabled,
            priority=rule.priority,
            created_at=rule.created_at,
            updated_at=rule.last_modified,
        )

    def _orm_to_rule(self, orm: EmailRuleORM) -> EmailRule:
        """Convert ORM to EmailRule."""
        from ..models import RuleCondition

        return EmailRule(
            id=orm.id,
            name=orm.name,
            description=orm.description,
            conditions=[RuleCondition(**cond) for cond in orm.conditions],
            actions=orm.actions,
            enabled=orm.enabled,
            priority=orm.priority,
            created_at=orm.created_at,
            last_modified=orm.updated_at,
        )

    def _connector_config_to_orm(self, config: ConnectorConfig) -> ConnectorConfigORM:
        """Convert ConnectorConfig to ORM."""
        return ConnectorConfigORM(
            type=config.type,
            name=config.name,
            enabled=config.enabled,
            config=config.config,
            auth_data=config.auth_data,
            last_sync=config.last_sync,
            sync_frequency=config.sync_frequency,
            max_emails=config.max_emails,
        )

    def _orm_to_connector_config(self, orm: ConnectorConfigORM) -> ConnectorConfig:
        """Convert ORM to ConnectorConfig."""
        return ConnectorConfig(
            type=orm.type,
            name=orm.name,
            enabled=orm.enabled,
            config=orm.config or {},
            auth_data=orm.auth_data or {},
            last_sync=orm.last_sync,
            sync_frequency=orm.sync_frequency,
            max_emails=orm.max_emails,
        )
