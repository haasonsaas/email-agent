"""Rule processors for different rule types."""

import re
import logging
from typing import Any, Optional

from ..models import Email, EmailRule, EmailCategory, EmailPriority, RuleCondition
from ..sdk.base import BaseRule

logger = logging.getLogger(__name__)


def create_rule_processor(rule_config: EmailRule) -> BaseRule:
    """Factory function to create appropriate rule processor."""
    # Analyze conditions to determine best processor type
    has_regex = any(cond.operator == "regex" for cond in rule_config.conditions)
    has_domain = any(cond.field == "sender_domain" for cond in rule_config.conditions)
    has_subject = any(cond.field == "subject" for cond in rule_config.conditions)
    has_sender = any(cond.field in ["sender", "sender_name"] for cond in rule_config.conditions)
    
    # Choose most specific processor
    if has_regex:
        return RegexRule(rule_config)
    elif has_domain:
        return DomainRule(rule_config)
    elif has_subject:
        return SubjectRule(rule_config)
    elif has_sender:
        return SenderRule(rule_config)
    else:
        return GenericRule(rule_config)


class GenericRule(BaseRule):
    """Generic rule processor for any condition type."""
    
    def applies(self, email: Email) -> bool:
        """Check if rule applies to email."""
        # All conditions must be true (AND logic)
        for condition in self.rule_config.conditions:
            if not self._evaluate_condition(condition, email):
                return False
        return True
    
    def execute(self, email: Email) -> Email:
        """Execute rule actions on email."""
        actions = self.rule_config.actions
        
        # Apply category change
        if "category" in actions:
            try:
                email.category = EmailCategory(actions["category"])
            except ValueError:
                logger.warning(f"Invalid category in rule {self.rule_config.name}: {actions['category']}")
        
        # Apply priority change
        if "priority" in actions:
            try:
                email.priority = EmailPriority(actions["priority"])
            except ValueError:
                logger.warning(f"Invalid priority in rule {self.rule_config.name}: {actions['priority']}")
        
        # Add tags
        if "add_tags" in actions:
            tags_to_add = actions["add_tags"]
            if isinstance(tags_to_add, str):
                tags_to_add = [tags_to_add]
            for tag in tags_to_add:
                if tag not in email.tags:
                    email.tags.append(tag)
        
        # Remove tags
        if "remove_tags" in actions:
            tags_to_remove = actions["remove_tags"]
            if isinstance(tags_to_remove, str):
                tags_to_remove = [tags_to_remove]
            for tag in tags_to_remove:
                if tag in email.tags:
                    email.tags.remove(tag)
        
        # Mark as read/unread
        if "mark_read" in actions:
            email.is_read = bool(actions["mark_read"])
        
        # Mark as flagged/unflagged
        if "mark_flagged" in actions:
            email.is_flagged = bool(actions["mark_flagged"])
        
        return email
    
    def _evaluate_condition(self, condition: RuleCondition, email: Email) -> bool:
        """Evaluate a single condition."""
        field_value = self._get_field_value(email, condition.field)
        if field_value is None:
            return False
        
        # Convert to string for comparison
        field_str = str(field_value)
        if not condition.case_sensitive:
            field_str = field_str.lower()
            condition_value = condition.value.lower()
        else:
            condition_value = condition.value
        
        # Apply operator
        if condition.operator == "equals":
            return field_str == condition_value
        elif condition.operator == "contains":
            return condition_value in field_str
        elif condition.operator == "starts_with":
            return field_str.startswith(condition_value)
        elif condition.operator == "ends_with":
            return field_str.endswith(condition_value)
        elif condition.operator == "regex":
            try:
                pattern = re.compile(condition_value, re.IGNORECASE if not condition.case_sensitive else 0)
                return bool(pattern.search(field_str))
            except re.error as e:
                logger.error(f"Invalid regex in rule {self.rule_config.name}: {str(e)}")
                return False
        elif condition.operator == "not_equals":
            return field_str != condition_value
        elif condition.operator == "not_contains":
            return condition_value not in field_str
        else:
            logger.warning(f"Unknown operator in rule {self.rule_config.name}: {condition.operator}")
            return False
    
    def _get_field_value(self, email: Email, field: str) -> Optional[Any]:
        """Get field value from email object."""
        field_map = {
            "subject": email.subject,
            "sender": email.sender.email,
            "sender_name": email.sender.name or "",
            "sender_domain": email.sender.email.split("@")[-1] if "@" in email.sender.email else "",
            "body": email.body_text or "",
            "body_html": email.body_html or "",
            "recipients": ", ".join([addr.email for addr in email.recipients]),
            "cc": ", ".join([addr.email for addr in email.cc]),
            "is_read": email.is_read,
            "is_flagged": email.is_flagged,
            "category": email.category.value,
            "priority": email.priority.value,
            "tags": ", ".join(email.tags),
            "has_attachments": len(email.attachments) > 0,
            "attachment_count": len(email.attachments),
        }
        
        return field_map.get(field)


class RegexRule(GenericRule):
    """Optimized rule processor for regex-based conditions."""
    
    def __init__(self, rule_config: EmailRule):
        super().__init__(rule_config)
        self._compiled_patterns = {}
        self._compile_regex_patterns()
    
    def _compile_regex_patterns(self):
        """Pre-compile regex patterns for performance."""
        for i, condition in enumerate(self.rule_config.conditions):
            if condition.operator == "regex":
                try:
                    flags = re.IGNORECASE if not condition.case_sensitive else 0
                    self._compiled_patterns[i] = re.compile(condition.value, flags)
                except re.error as e:
                    logger.error(f"Invalid regex in rule {self.rule_config.name}: {str(e)}")
    
    def _evaluate_condition(self, condition: RuleCondition, email: Email) -> bool:
        """Evaluate condition with pre-compiled regex."""
        condition_index = self.rule_config.conditions.index(condition)
        
        if condition.operator == "regex" and condition_index in self._compiled_patterns:
            field_value = self._get_field_value(email, condition.field)
            if field_value is None:
                return False
            
            pattern = self._compiled_patterns[condition_index]
            return bool(pattern.search(str(field_value)))
        
        return super()._evaluate_condition(condition, email)


class DomainRule(GenericRule):
    """Optimized rule processor for domain-based conditions."""
    
    def __init__(self, rule_config: EmailRule):
        super().__init__(rule_config)
        self._domain_conditions = []
        self._extract_domain_conditions()
    
    def _extract_domain_conditions(self):
        """Extract and optimize domain conditions."""
        for condition in self.rule_config.conditions:
            if condition.field == "sender_domain":
                domain_value = condition.value.lower() if not condition.case_sensitive else condition.value
                self._domain_conditions.append((condition.operator, domain_value))
    
    def applies(self, email: Email) -> bool:
        """Optimized domain checking."""
        sender_domain = email.sender.email.split("@")[-1].lower() if "@" in email.sender.email else ""
        
        # Quick domain checks first
        for operator, domain_value in self._domain_conditions:
            if operator == "equals" and sender_domain == domain_value:
                continue
            elif operator == "contains" and domain_value in sender_domain:
                continue
            elif operator == "ends_with" and sender_domain.endswith(domain_value):
                continue
            else:
                return False
        
        # Fall back to generic evaluation for non-domain conditions
        return super().applies(email)


class SubjectRule(GenericRule):
    """Optimized rule processor for subject-based conditions."""
    
    def __init__(self, rule_config: EmailRule):
        super().__init__(rule_config)
        self._subject_keywords = set()
        self._extract_subject_keywords()
    
    def _extract_subject_keywords(self):
        """Extract keywords from subject conditions."""
        for condition in self.rule_config.conditions:
            if condition.field == "subject" and condition.operator == "contains":
                keyword = condition.value.lower() if not condition.case_sensitive else condition.value
                self._subject_keywords.add(keyword)
    
    def applies(self, email: Email) -> bool:
        """Optimized subject checking."""
        subject = email.subject.lower()
        
        # Quick keyword check first
        if self._subject_keywords:
            has_keyword = any(keyword in subject for keyword in self._subject_keywords)
            if not has_keyword:
                return False
        
        return super().applies(email)


class SenderRule(GenericRule):
    """Optimized rule processor for sender-based conditions."""
    
    def __init__(self, rule_config: EmailRule):
        super().__init__(rule_config)
        self._sender_emails = set()
        self._sender_domains = set()
        self._extract_sender_info()
    
    def _extract_sender_info(self):
        """Extract sender emails and domains."""
        for condition in self.rule_config.conditions:
            if condition.field == "sender" and condition.operator == "equals":
                sender = condition.value.lower() if not condition.case_sensitive else condition.value
                self._sender_emails.add(sender)
                if "@" in sender:
                    domain = sender.split("@")[-1]
                    self._sender_domains.add(domain)
    
    def applies(self, email: Email) -> bool:
        """Optimized sender checking."""
        sender_email = email.sender.email.lower()
        
        # Quick email/domain check first
        if self._sender_emails and sender_email not in self._sender_emails:
            return False
        
        return super().applies(email)


class MLRule(GenericRule):
    """Machine learning based rule processor."""
    
    def __init__(self, rule_config: EmailRule):
        super().__init__(rule_config)
        self._model = None
        self._load_ml_model()
    
    def _load_ml_model(self):
        """Load ML model for categorization."""
        # Placeholder for ML model loading
        # In a real implementation, this would load a trained model
        pass
    
    def applies(self, email: Email) -> bool:
        """Use ML model to determine if rule applies."""
        if not self._model:
            return super().applies(email)
        
        # Placeholder for ML prediction
        # In a real implementation, this would use the model to predict
        return super().applies(email)