"""Categorizer agent for email organization and rule processing."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import Email, EmailRule, EmailCategory
from ..rules import RulesEngine, BuiltinRules
from ..sdk.exceptions import RuleError

logger = logging.getLogger(__name__)


class CategorizerAgent:
    """Agent responsible for categorizing emails using rules and ML."""
    
    def __init__(self):
        self.rules_engine = RulesEngine()
        self.stats: Dict[str, Any] = {
            "emails_processed": 0,
            "rules_applied": 0,
            "categorization_accuracy": 0.0,
            "last_processing": None
        }
        self._initialize_builtin_rules()
    
    def _initialize_builtin_rules(self):
        """Initialize with built-in categorization rules."""
        try:
            builtin_rules = BuiltinRules.get_all_rules()
            self.rules_engine.load_rules(builtin_rules)
            logger.info(f"Loaded {len(builtin_rules)} built-in rules")
        except Exception as e:
            logger.error(f"Failed to load built-in rules: {str(e)}")
    
    async def categorize_emails(
        self, 
        emails: List[Email], 
        custom_rules: Optional[List[EmailRule]] = None
    ) -> List[Email]:
        """Categorize a list of emails using rules engine."""
        if not emails:
            return []
        
        # Update rules if custom rules provided
        if custom_rules:
            all_rules = BuiltinRules.get_all_rules() + custom_rules
            self.rules_engine.load_rules(all_rules)
        
        # Process emails through rules engine
        categorized_emails = []
        rules_applied_count = 0
        
        for email in emails:
            try:
                # Apply rules to categorize email
                processed_email = self.rules_engine.process_email(email)
                
                # Count how many rules were applied
                matching_rules = self.rules_engine.get_matching_rules(processed_email)
                rules_applied_count += len(matching_rules)
                
                # Additional ML-based categorization could go here
                processed_email = await self._apply_ml_categorization(processed_email)
                
                categorized_emails.append(processed_email)
                
            except Exception as e:
                logger.error(f"Failed to categorize email {email.id}: {str(e)}")
                # Add original email if categorization fails
                categorized_emails.append(email)
        
        # Update stats
        self.stats["emails_processed"] += len(emails)
        self.stats["rules_applied"] += rules_applied_count
        self.stats["last_processing"] = datetime.now()
        
        logger.info(f"Categorized {len(categorized_emails)} emails with {rules_applied_count} rule applications")
        return categorized_emails
    
    async def _apply_ml_categorization(self, email: Email) -> Email:
        """Apply ML-based categorization (placeholder for future ML integration)."""
        # This is where we would integrate with ML models for categorization
        # For now, we'll use simple heuristics
        
        try:
            # Simple heuristic: if no category was set by rules, try to infer
            if email.category == EmailCategory.PRIMARY:
                email.category = self._infer_category_from_content(email)
            
            return email
            
        except Exception as e:
            logger.error(f"ML categorization failed for email {email.id}: {str(e)}")
            return email
    
    def _infer_category_from_content(self, email: Email) -> EmailCategory:
        """Infer category from email content using simple heuristics."""
        subject_lower = email.subject.lower()
        sender_domain = email.sender.email.split("@")[-1].lower() if "@" in email.sender.email else ""
        
        # Social media domains
        social_domains = ["facebook.com", "twitter.com", "linkedin.com", "instagram.com"]
        if any(domain in sender_domain for domain in social_domains):
            return EmailCategory.SOCIAL
        
        # Common promotional keywords
        promo_keywords = ["sale", "discount", "offer", "deal", "promotion", "coupon"]
        if any(keyword in subject_lower for keyword in promo_keywords):
            return EmailCategory.PROMOTIONS
        
        # Newsletter/update indicators
        update_keywords = ["newsletter", "digest", "update", "news"]
        if any(keyword in subject_lower for keyword in update_keywords):
            return EmailCategory.UPDATES
        
        # Forum indicators
        if subject_lower.startswith("[") or "forum" in subject_lower or "community" in subject_lower:
            return EmailCategory.FORUMS
        
        return EmailCategory.PRIMARY
    
    async def add_rule(self, rule: EmailRule) -> bool:
        """Add a new categorization rule."""
        try:
            success = self.rules_engine.add_rule(rule)
            if success:
                logger.info(f"Added rule: {rule.name}")
            return success
        except Exception as e:
            logger.error(f"Failed to add rule {rule.name}: {str(e)}")
            return False
    
    async def remove_rule(self, rule_id: str) -> bool:
        """Remove a categorization rule."""
        try:
            success = self.rules_engine.remove_rule(rule_id)
            if success:
                logger.info(f"Removed rule: {rule_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to remove rule {rule_id}: {str(e)}")
            return False
    
    async def test_rule(self, rule: EmailRule, test_emails: List[Email]) -> Dict[str, Any]:
        """Test a rule against a set of emails."""
        results: Dict[str, Any] = {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "total_emails": len(test_emails),
            "matching_emails": 0,
            "sample_matches": [],
            "performance": {}
        }
        
        try:
            start_time = datetime.now()
            
            for email in test_emails:
                test_result = self.rules_engine.test_rule(rule, email)
                
                if test_result["applies"]:
                    results["matching_emails"] += 1
                    
                    # Add sample matches (up to 5)
                    if len(results["sample_matches"]) < 5:
                        results["sample_matches"].append({
                            "email_id": email.id,
                            "subject": email.subject,
                            "sender": email.sender.email,
                            "conditions_met": test_result["conditions_met"]
                        })
            
            # Calculate performance metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            results["performance"] = {
                "processing_time_seconds": processing_time,
                "emails_per_second": len(test_emails) / processing_time if processing_time > 0 else 0,
                "match_percentage": (results["matching_emails"] / len(test_emails)) * 100 if test_emails else 0
            }
            
        except Exception as e:
            results["error"] = str(e)
            logger.error(f"Rule testing failed: {str(e)}")
        
        return results
    
    async def get_category_stats(self, emails: List[Email]) -> Dict[str, Any]:
        """Get categorization statistics for a set of emails."""
        if not emails:
            return {}
        
        category_counts: Dict[str, int] = {}
        for category in EmailCategory:
            category_counts[category.value] = 0
        
        for email in emails:
            category_counts[email.category.value] += 1
        
        return {
            "total_emails": len(emails),
            "categories": category_counts,
            "most_common_category": max(category_counts.keys(), key=lambda k: category_counts[k]) if category_counts else None,
            "categorization_distribution": {
                cat: (count / len(emails)) * 100 
                for cat, count in category_counts.items()
            }
        }
    
    async def suggest_rules(self, emails: List[Email]) -> List[Dict[str, Any]]:
        """Suggest new rules based on email patterns."""
        suggestions = []
        
        # Analyze sender domains
        domain_counts = {}
        for email in emails:
            if "@" in email.sender.email:
                domain = email.sender.email.split("@")[-1].lower()
                domain_counts[domain] = domain_counts.get(domain, 0) + 1
        
        # Suggest rules for frequent domains
        for domain, count in domain_counts.items():
            if count >= 5:  # At least 5 emails from this domain
                suggestion = {
                    "type": "domain_rule",
                    "domain": domain,
                    "email_count": count,
                    "suggested_category": self._suggest_category_for_domain(domain),
                    "confidence": min(count / 10, 1.0)  # Higher confidence with more emails
                }
                suggestions.append(suggestion)
        
        # Analyze subject patterns
        subject_keywords = {}
        for email in emails:
            words = email.subject.lower().split()
            for word in words:
                if len(word) > 3:  # Skip short words
                    subject_keywords[word] = subject_keywords.get(word, 0) + 1
        
        # Suggest rules for frequent keywords
        for keyword, count in subject_keywords.items():
            if count >= 3:  # At least 3 emails with this keyword
                suggestion = {
                    "type": "keyword_rule",
                    "keyword": keyword,
                    "email_count": count,
                    "suggested_category": self._suggest_category_for_keyword(keyword),
                    "confidence": min(count / 5, 1.0)
                }
                suggestions.append(suggestion)
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        
        return suggestions[:10]  # Return top 10 suggestions
    
    def _suggest_category_for_domain(self, domain: str) -> str:
        """Suggest category based on domain."""
        social_domains = ["facebook.com", "twitter.com", "linkedin.com", "instagram.com"]
        if domain in social_domains:
            return EmailCategory.SOCIAL.value
        
        if "newsletter" in domain or "news" in domain:
            return EmailCategory.UPDATES.value
        
        return EmailCategory.PRIMARY.value
    
    def _suggest_category_for_keyword(self, keyword: str) -> str:
        """Suggest category based on keyword."""
        promo_keywords = ["sale", "discount", "offer", "deal", "promotion"]
        if keyword in promo_keywords:
            return EmailCategory.PROMOTIONS.value
        
        update_keywords = ["newsletter", "digest", "update", "news"]
        if keyword in update_keywords:
            return EmailCategory.UPDATES.value
        
        return EmailCategory.PRIMARY.value
    
    async def get_status(self) -> Dict[str, Any]:
        """Get categorizer agent status."""
        engine_stats = self.rules_engine.get_stats()
        
        return {
            "rules_loaded": engine_stats["total_rules"],
            "enabled_rules": engine_stats["enabled_rules"],
            "rule_types": engine_stats["rule_types"],
            "stats": self.stats.copy()
        }
    
    async def shutdown(self) -> None:
        """Shutdown the categorizer agent."""
        try:
            # Clear rules engine
            self.rules_engine.rules.clear()
            logger.info("Categorizer agent shutdown completed")
        except Exception as e:
            logger.error(f"Error during categorizer shutdown: {str(e)}")