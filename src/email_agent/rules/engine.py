"""Rules engine for email categorization."""

import logging
import re
from typing import Any, Dict, List, Optional

from ..models import Email, EmailRule, RuleCondition
from ..sdk.base import BaseRule
from .processors import create_rule_processor

logger = logging.getLogger(__name__)


class RulesEngine:
    """Engine for processing email categorization rules."""
    
    def __init__(self):
        self.rules: List[BaseRule] = []
        self._rule_processors: Dict[str, BaseRule] = {}
    
    def load_rules(self, rules: List[EmailRule]) -> None:
        """Load rules into the engine."""
        self.rules.clear()
        self._rule_processors.clear()
        
        for rule_config in rules:
            if rule_config.enabled:
                try:
                    processor = create_rule_processor(rule_config)
                    self.rules.append(processor)
                    self._rule_processors[rule_config.id] = processor
                except Exception as e:
                    logger.error(f"Failed to load rule {rule_config.id}: {str(e)}")
        
        # Sort rules by priority (lower number = higher priority)
        self.rules.sort(key=lambda r: r.priority)
        logger.info(f"Loaded {len(self.rules)} rules")
    
    def process_email(self, email: Email) -> Email:
        """Process an email through all rules."""
        processed_email = email.model_copy(deep=True)
        
        for rule in self.rules:
            try:
                if rule.applies(processed_email):
                    processed_email = rule.execute(processed_email)
                    logger.debug(f"Applied rule {rule.rule_config.name} to email {email.id}")
            except Exception as e:
                logger.error(f"Error applying rule {rule.rule_config.name}: {str(e)}")
                continue
        
        return processed_email
    
    def process_emails(self, emails: List[Email]) -> List[Email]:
        """Process multiple emails through all rules."""
        processed_emails = []
        
        for email in emails:
            try:
                processed_email = self.process_email(email)
                processed_emails.append(processed_email)
            except Exception as e:
                logger.error(f"Error processing email {email.id}: {str(e)}")
                processed_emails.append(email)  # Add original on error
        
        return processed_emails
    
    def add_rule(self, rule_config: EmailRule) -> bool:
        """Add a new rule to the engine."""
        try:
            processor = create_rule_processor(rule_config)
            self.rules.append(processor)
            self._rule_processors[rule_config.id] = processor
            
            # Re-sort rules by priority
            self.rules.sort(key=lambda r: r.priority)
            logger.info(f"Added rule {rule_config.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add rule {rule_config.name}: {str(e)}")
            return False
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule from the engine."""
        if rule_id in self._rule_processors:
            processor = self._rule_processors[rule_id]
            self.rules.remove(processor)
            del self._rule_processors[rule_id]
            logger.info(f"Removed rule {rule_id}")
            return True
        return False
    
    def get_matching_rules(self, email: Email) -> List[str]:
        """Get list of rule IDs that match the email."""
        matching_rules = []
        
        for rule in self.rules:
            try:
                if rule.applies(email):
                    matching_rules.append(rule.rule_config.id)
            except Exception as e:
                logger.error(f"Error checking rule {rule.rule_config.name}: {str(e)}")
        
        return matching_rules
    
    def test_rule(self, rule_config: EmailRule, email: Email) -> Dict[str, Any]:
        """Test a rule against an email and return detailed results."""
        try:
            processor = create_rule_processor(rule_config)
            
            # Test if rule applies
            applies = processor.applies(email)
            
            result = {
                "rule_id": rule_config.id,
                "rule_name": rule_config.name,
                "applies": applies,
                "conditions_met": [],
                "actions": rule_config.actions if applies else {},
                "error": None
            }
            
            # Test individual conditions
            for i, condition in enumerate(rule_config.conditions):
                try:
                    condition_result = self._test_condition(condition, email)
                    result["conditions_met"].append({
                        "index": i,
                        "field": condition.field,
                        "operator": condition.operator,
                        "value": condition.value,
                        "matches": condition_result
                    })
                except Exception as e:
                    result["conditions_met"].append({
                        "index": i,
                        "field": condition.field,
                        "operator": condition.operator,
                        "value": condition.value,
                        "matches": False,
                        "error": str(e)
                    })
            
            return result
            
        except Exception as e:
            return {
                "rule_id": rule_config.id,
                "rule_name": rule_config.name,
                "applies": False,
                "conditions_met": [],
                "actions": {},
                "error": str(e)
            }
    
    def _test_condition(self, condition: RuleCondition, email: Email) -> bool:
        """Test a single condition against an email."""
        # Get field value from email
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
            except re.error:
                return False
        elif condition.operator == "not_equals":
            return field_str != condition_value
        elif condition.operator == "not_contains":
            return condition_value not in field_str
        else:
            logger.warning(f"Unknown operator: {condition.operator}")
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
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules if r.enabled]),
            "rule_types": self._get_rule_type_counts()
        }
    
    def _get_rule_type_counts(self) -> Dict[str, int]:
        """Get count of each rule type."""
        type_counts = {}
        for rule in self.rules:
            rule_type = type(rule).__name__
            type_counts[rule_type] = type_counts.get(rule_type, 0) + 1
        return type_counts