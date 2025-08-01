"""Categorizer agent for email organization and rule processing."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from ..config import settings
from ..models import Email, EmailRule, EmailCategory
from ..rules import RulesEngine, BuiltinRules
from ..sdk.exceptions import RuleError

logger = logging.getLogger(__name__)


class CategorizerAgent:
    """Agent responsible for categorizing emails using rules and ML."""
    
    def __init__(self):
        self.rules_engine = RulesEngine()
        self.openai_client: Optional[AsyncOpenAI] = None
        self.stats: Dict[str, Any] = {
            "emails_processed": 0,
            "rules_applied": 0,
            "ai_categorizations": 0,
            "categorization_accuracy": 0.0,
            "last_processing": None
        }
        self._initialize_builtin_rules()
        self._initialize_ai_client()
    
    def _initialize_builtin_rules(self):
        """Initialize with built-in categorization rules."""
        try:
            builtin_rules = BuiltinRules.get_all_rules()
            self.rules_engine.load_rules(builtin_rules)
            logger.info(f"Loaded {len(builtin_rules)} built-in rules")
        except Exception as e:
            logger.error(f"Failed to load built-in rules: {str(e)}")
    
    def _initialize_ai_client(self) -> None:
        """Initialize OpenAI client for AI categorization."""
        try:
            if AsyncOpenAI and settings.openai_api_key:
                self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
                logger.info("OpenAI client initialized for categorization")
            else:
                logger.warning("No OpenAI API key provided - AI categorization disabled")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    
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
        """Apply AI-based categorization using OpenAI."""
        try:
            # If OpenAI is available, use AI for intelligent categorization
            if self.openai_client and (email.category == EmailCategory.PRIMARY or not email.category):
                ai_category = await self._categorize_with_ai(email)
                if ai_category:
                    email.category = ai_category
                    self.stats["ai_categorizations"] += 1
            
            # Fallback to rule-based categorization
            elif email.category == EmailCategory.PRIMARY:
                email.category = self._infer_category_from_content(email)
            
            return email
            
        except Exception as e:
            logger.error(f"ML categorization failed for email {email.id}: {str(e)}")
            return email
    
    async def _categorize_with_ai(self, email: Email) -> Optional[EmailCategory]:
        """Categorize email using OpenAI."""
        try:
            # Prepare email data for analysis
            email_content = {
                "subject": email.subject,
                "sender": email.sender.email,
                "body_preview": (email.body_text or "")[:500] + "..." if email.body_text else ""
            }
            
            # Create categorization prompt
            prompt = self._create_categorization_prompt(email_content)
            
            # Call OpenAI API
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert email categorization system. Analyze emails and assign them to the most appropriate category."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip().lower()
            
            # Parse the AI response
            category = self._parse_ai_category_response(content)
            
            if category:
                logger.debug(f"AI categorized email {email.id} as {category.value}")
                return category
            
        except Exception as e:
            logger.error(f"AI categorization failed for email {email.id}: {str(e)}")
        
        return None
    
    def _create_categorization_prompt(self, email_content: Dict[str, str]) -> str:
        """Create prompt for AI categorization."""
        categories = [cat.value for cat in EmailCategory]
        
        return f"""
Categorize this email into one of the following categories: {', '.join(categories)}

Email Details:
- Subject: {email_content['subject']}
- From: {email_content['sender']}
- Preview: {email_content['body_preview']}

Categories:
- primary: Important personal or business emails that require attention
- social: Social media notifications, friend updates, social platforms
- promotions: Marketing emails, sales, offers, advertisements
- updates: Newsletters, automated updates, news subscriptions
- forums: Forum notifications, community discussions, mailing lists
- spam: Unwanted or suspicious emails

Return only the category name (e.g., "primary", "social", "promotions", etc.).
"""
    
    def _parse_ai_category_response(self, response: str) -> Optional[EmailCategory]:
        """Parse AI response and return EmailCategory."""
        response = response.strip().lower()
        
        # Try to match exact category names
        for category in EmailCategory:
            if category.value in response:
                return category
        
        # Try to match common variations
        category_mappings = {
            "business": EmailCategory.PRIMARY,
            "work": EmailCategory.PRIMARY,
            "personal": EmailCategory.PRIMARY,
            "important": EmailCategory.PRIMARY,
            "marketing": EmailCategory.PROMOTIONS,
            "advertisement": EmailCategory.PROMOTIONS,
            "sales": EmailCategory.PROMOTIONS,
            "newsletter": EmailCategory.UPDATES,
            "news": EmailCategory.UPDATES,
            "notification": EmailCategory.UPDATES,
            "forum": EmailCategory.FORUMS,
            "discussion": EmailCategory.FORUMS,
            "community": EmailCategory.FORUMS,
            "facebook": EmailCategory.SOCIAL,
            "twitter": EmailCategory.SOCIAL,
            "linkedin": EmailCategory.SOCIAL,
        }
        
        for keyword, category in category_mappings.items():
            if keyword in response:
                return category
        
        return None
    
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
            "ai_enabled": self.openai_client is not None,
            "ai_model": settings.openai_model if self.openai_client else None,
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