"""Built-in rules inspired by Gmail's categorization system."""

import re
from typing import List

from ..models import EmailRule, RuleCondition, EmailCategory, EmailPriority


class BuiltinRules:
    """Factory for creating built-in email categorization rules."""
    
    @staticmethod
    def get_all_rules() -> List[EmailRule]:
        """Get all built-in rules."""
        return [
            BuiltinRules.social_media_rule(),
            BuiltinRules.newsletters_rule(),
            BuiltinRules.notifications_rule(),
            BuiltinRules.promotions_rule(),
            BuiltinRules.forums_rule(),
            BuiltinRules.automated_emails_rule(),
            BuiltinRules.urgent_emails_rule(),
            BuiltinRules.spam_indicators_rule(),
        ]
    
    @staticmethod
    def social_media_rule() -> EmailRule:
        """Rule for social media emails."""
        return EmailRule(
            id="builtin_social_media",
            name="Social Media",
            description="Categorize emails from social media platforms",
            conditions=[
                RuleCondition(
                    field="sender_domain",
                    operator="regex",
                    value=r"(facebook|twitter|linkedin|instagram|tiktok|snapchat|discord|slack|teams)\.com$",
                    case_sensitive=False
                ),
            ],
            actions={
                "category": EmailCategory.SOCIAL.value,
                "add_tags": ["social_media"]
            },
            priority=10
        )
    
    @staticmethod
    def newsletters_rule() -> EmailRule:
        """Rule for newsletter emails."""
        return EmailRule(
            id="builtin_newsletters",
            name="Newsletters & Updates",
            description="Categorize newsletter and update emails",
            conditions=[
                RuleCondition(
                    field="subject",
                    operator="regex",
                    value=r"(newsletter|digest|weekly|monthly|update|bulletin)",
                    case_sensitive=False
                ),
            ],
            actions={
                "category": EmailCategory.UPDATES.value,
                "add_tags": ["newsletter"]
            },
            priority=20
        )
    
    @staticmethod
    def notifications_rule() -> EmailRule:
        """Rule for notification emails."""
        return EmailRule(
            id="builtin_notifications",
            name="Notifications",
            description="Categorize system and service notifications",
            conditions=[
                RuleCondition(
                    field="subject",
                    operator="regex",
                    value=r"(notification|alert|reminder|noreply|no-reply)",
                    case_sensitive=False
                ),
            ],
            actions={
                "category": EmailCategory.UPDATES.value,
                "add_tags": ["notification"]
            },
            priority=30
        )
    
    @staticmethod
    def promotions_rule() -> EmailRule:
        """Rule for promotional emails."""
        return EmailRule(
            id="builtin_promotions",
            name="Promotions & Marketing",
            description="Categorize promotional and marketing emails",
            conditions=[
                RuleCondition(
                    field="subject",
                    operator="regex",
                    value=r"(sale|discount|offer|promo|deal|coupon|% off|free shipping|limited time)",
                    case_sensitive=False
                ),
            ],
            actions={
                "category": EmailCategory.PROMOTIONS.value,
                "add_tags": ["promotion", "marketing"]
            },
            priority=15
        )
    
    @staticmethod
    def forums_rule() -> EmailRule:
        """Rule for forum and community emails."""
        return EmailRule(
            id="builtin_forums",
            name="Forums & Communities",
            description="Categorize emails from forums and online communities",
            conditions=[
                RuleCondition(
                    field="subject",
                    operator="regex",
                    value=r"(\[.*\]|forum|community|discussion|replied to|mentioned you)",
                    case_sensitive=False
                ),
            ],
            actions={
                "category": EmailCategory.FORUMS.value,
                "add_tags": ["forum", "community"]
            },
            priority=25
        )
    
    @staticmethod
    def automated_emails_rule() -> EmailRule:
        """Rule for automated system emails."""
        return EmailRule(
            id="builtin_automated",
            name="Automated Emails",
            description="Categorize automated system emails",
            conditions=[
                RuleCondition(
                    field="sender",
                    operator="regex",
                    value=r"(noreply|no-reply|donotreply|automated|system|daemon)@",
                    case_sensitive=False
                ),
            ],
            actions={
                "category": EmailCategory.UPDATES.value,
                "add_tags": ["automated", "system"],
                "priority": EmailPriority.LOW.value
            },
            priority=40
        )
    
    @staticmethod
    def urgent_emails_rule() -> EmailRule:
        """Rule for urgent emails."""
        return EmailRule(
            id="builtin_urgent",
            name="Urgent Emails",
            description="Mark emails as urgent based on subject keywords",
            conditions=[
                RuleCondition(
                    field="subject",
                    operator="regex",
                    value=r"(urgent|asap|emergency|critical|immediate|deadline|expires)",
                    case_sensitive=False
                ),
            ],
            actions={
                "priority": EmailPriority.URGENT.value,
                "add_tags": ["urgent"],
                "mark_flagged": True
            },
            priority=5  # High priority to catch urgent emails first
        )
    
    @staticmethod
    def spam_indicators_rule() -> EmailRule:
        """Rule for potential spam indicators."""
        return EmailRule(
            id="builtin_spam_indicators",
            name="Spam Indicators",
            description="Flag emails with common spam indicators",
            conditions=[
                RuleCondition(
                    field="subject",
                    operator="regex",
                    value=r"(RE: RE: RE:|FW: FW: FW:|WINNER|CONGRATULATIONS|CLAIM YOUR|ACT NOW|CASH PRIZE)",
                    case_sensitive=False
                ),
            ],
            actions={
                "add_tags": ["potential_spam"],
                "priority": EmailPriority.LOW.value
            },
            priority=50
        )
    
    @staticmethod
    def create_domain_rule(domain: str, category: EmailCategory, tags: List[str] = None) -> EmailRule:
        """Create a custom domain-based rule."""
        rule_id = f"domain_{domain.replace('.', '_')}"
        tags = tags or [domain.split('.')[0]]
        
        return EmailRule(
            id=rule_id,
            name=f"Domain: {domain}",
            description=f"Categorize emails from {domain}",
            conditions=[
                RuleCondition(
                    field="sender_domain",
                    operator="equals",
                    value=domain,
                    case_sensitive=False
                ),
            ],
            actions={
                "category": category.value,
                "add_tags": tags
            },
            priority=100  # Lower priority for custom rules
        )
    
    @staticmethod
    def create_sender_rule(sender: str, category: EmailCategory, tags: List[str] = None) -> EmailRule:
        """Create a custom sender-based rule."""
        rule_id = f"sender_{sender.replace('@', '_at_').replace('.', '_')}"
        tags = tags or ["custom_sender"]
        
        return EmailRule(
            id=rule_id,
            name=f"Sender: {sender}",
            description=f"Categorize emails from {sender}",
            conditions=[
                RuleCondition(
                    field="sender",
                    operator="equals",
                    value=sender,
                    case_sensitive=False
                ),
            ],
            actions={
                "category": category.value,
                "add_tags": tags
            },
            priority=90  # Higher priority than domain rules
        )
    
    @staticmethod
    def create_keyword_rule(keywords: List[str], category: EmailCategory, field: str = "subject") -> EmailRule:
        """Create a custom keyword-based rule."""
        keyword_pattern = "|".join(re.escape(keyword) for keyword in keywords)
        rule_id = f"keywords_{field}_{hash(keyword_pattern) % 10000}"
        
        return EmailRule(
            id=rule_id,
            name=f"Keywords in {field}: {', '.join(keywords[:3])}{'...' if len(keywords) > 3 else ''}",
            description=f"Categorize emails with specific keywords in {field}",
            conditions=[
                RuleCondition(
                    field=field,
                    operator="regex",
                    value=f"({keyword_pattern})",
                    case_sensitive=False
                ),
            ],
            actions={
                "category": category.value,
                "add_tags": ["keyword_match"]
            },
            priority=80
        )