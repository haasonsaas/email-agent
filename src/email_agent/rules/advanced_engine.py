"""Advanced email rules engine with ML and pattern learning."""

import logging
import re
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter

from ..models import Email, EmailRule, RuleCondition
from .engine import RulesEngine

logger = logging.getLogger(__name__)


class AdvancedRuleEngine(RulesEngine):
    """Advanced rules engine with ML capabilities and pattern learning."""
    
    def __init__(self):
        super().__init__()
        self.pattern_cache = {}
        self.learning_enabled = True
        self.confidence_threshold = 0.7
        self.learned_patterns = defaultdict(list)
        self.rule_performance = defaultdict(lambda: {"matches": 0, "accuracy": 0.0})
        self.auto_generated_rules = []
    
    async def learn_from_emails(self, emails: List[Email], user_feedback: Dict[str, Any] = None):
        """Learn patterns from email data and user feedback."""
        if not self.learning_enabled or not emails:
            return
        
        logger.info(f"Learning patterns from {len(emails)} emails")
        
        # Analyze sender patterns
        await self._learn_sender_patterns(emails)
        
        # Analyze subject patterns
        await self._learn_subject_patterns(emails)
        
        # Analyze content patterns
        await self._learn_content_patterns(emails)
        
        # Analyze temporal patterns
        await self._learn_temporal_patterns(emails)
        
        # Generate new rules from learned patterns
        await self._generate_rules_from_patterns()
        
        # Update rule performance metrics
        await self._update_rule_performance(emails, user_feedback)
        
        logger.info(f"Pattern learning completed. Generated {len(self.auto_generated_rules)} new rules")
    
    async def _learn_sender_patterns(self, emails: List[Email]):
        """Learn patterns from email senders."""
        sender_categories = defaultdict(Counter)
        sender_priorities = defaultdict(Counter)
        
        for email in emails:
            sender = email.sender.email
            category = email.category.value
            priority = email.priority.value
            
            sender_categories[sender][category] += 1
            sender_priorities[sender][priority] += 1
        
        # Find senders with consistent patterns
        for sender, category_counts in sender_categories.items():
            total_emails = sum(category_counts.values())
            if total_emails >= 3:  # Minimum threshold
                most_common_category, count = category_counts.most_common(1)[0]
                confidence = count / total_emails
                
                if confidence >= self.confidence_threshold:
                    pattern = {
                        "type": "sender_category",
                        "sender": sender,
                        "category": most_common_category,
                        "confidence": confidence,
                        "sample_size": total_emails
                    }
                    self.learned_patterns["sender_patterns"].append(pattern)
    
    async def _learn_subject_patterns(self, emails: List[Email]):
        """Learn patterns from email subjects."""
        subject_keywords = defaultdict(lambda: defaultdict(Counter))
        
        for email in emails:
            # Extract keywords from subject
            keywords = self._extract_keywords(email.subject)
            category = email.category.value
            priority = email.priority.value
            
            for keyword in keywords:
                subject_keywords[keyword]["categories"][category] += 1
                subject_keywords[keyword]["priorities"][priority] += 1
        
        # Find keywords with strong predictive power
        for keyword, data in subject_keywords.items():
            total_occurrences = sum(data["categories"].values())
            if total_occurrences >= 5:  # Minimum threshold
                
                # Check category prediction strength
                most_common_category, count = data["categories"].most_common(1)[0]
                category_confidence = count / total_occurrences
                
                if category_confidence >= self.confidence_threshold:
                    pattern = {
                        "type": "subject_keyword_category",
                        "keyword": keyword,
                        "category": most_common_category,
                        "confidence": category_confidence,
                        "sample_size": total_occurrences
                    }
                    self.learned_patterns["subject_patterns"].append(pattern)
                
                # Check priority prediction strength
                most_common_priority, count = data["priorities"].most_common(1)[0]
                priority_confidence = count / total_occurrences
                
                if priority_confidence >= self.confidence_threshold:
                    pattern = {
                        "type": "subject_keyword_priority",
                        "keyword": keyword,
                        "priority": most_common_priority,
                        "confidence": priority_confidence,
                        "sample_size": total_occurrences
                    }
                    self.learned_patterns["subject_patterns"].append(pattern)
    
    async def _learn_content_patterns(self, emails: List[Email]):
        """Learn patterns from email content."""
        content_patterns = defaultdict(lambda: defaultdict(Counter))
        
        for email in emails:
            if not email.body_text:
                continue
            
            # Extract content features
            features = self._extract_content_features(email.body_text)
            category = email.category.value
            
            for feature, value in features.items():
                if isinstance(value, bool) and value:
                    content_patterns[feature]["categories"][category] += 1
                elif isinstance(value, (int, float)) and value > 0:
                    # Bin numerical features
                    binned_value = self._bin_numerical_feature(feature, value)
                    content_patterns[f"{feature}_{binned_value}"]["categories"][category] += 1
        
        # Find content features with predictive power
        for feature, data in content_patterns.items():
            total_occurrences = sum(data["categories"].values())
            if total_occurrences >= 3:
                most_common_category, count = data["categories"].most_common(1)[0]
                confidence = count / total_occurrences
                
                if confidence >= self.confidence_threshold:
                    pattern = {
                        "type": "content_feature",
                        "feature": feature,
                        "category": most_common_category,
                        "confidence": confidence,
                        "sample_size": total_occurrences
                    }
                    self.learned_patterns["content_patterns"].append(pattern)
    
    async def _learn_temporal_patterns(self, emails: List[Email]):
        """Learn temporal patterns from emails."""
        temporal_patterns = defaultdict(lambda: defaultdict(Counter))
        
        for email in emails:
            # Extract temporal features
            hour = email.date.hour
            day_of_week = email.date.weekday()  # 0=Monday, 6=Sunday
            
            category = email.category.value
            priority = email.priority.value
            
            # Hour patterns
            temporal_patterns[f"hour_{hour}"]["categories"][category] += 1
            temporal_patterns[f"hour_{hour}"]["priorities"][priority] += 1
            
            # Day of week patterns
            temporal_patterns[f"day_{day_of_week}"]["categories"][category] += 1
            temporal_patterns[f"day_{day_of_week}"]["priorities"][priority] += 1
            
            # Time ranges
            if 9 <= hour <= 17:  # Business hours
                temporal_patterns["business_hours"]["categories"][category] += 1
            elif hour >= 18 or hour <= 6:  # After hours
                temporal_patterns["after_hours"]["categories"][category] += 1
        
        # Find temporal patterns with predictive power
        for time_feature, data in temporal_patterns.items():
            for metric_type in ["categories", "priorities"]:
                total_occurrences = sum(data[metric_type].values())
                if total_occurrences >= 10:  # Higher threshold for temporal patterns
                    most_common, count = data[metric_type].most_common(1)[0]
                    confidence = count / total_occurrences
                    
                    if confidence >= 0.6:  # Lower threshold for temporal patterns
                        pattern = {
                            "type": f"temporal_{metric_type[:-1]}",  # Remove 's'
                            "time_feature": time_feature,
                            metric_type[:-1]: most_common,
                            "confidence": confidence,
                            "sample_size": total_occurrences
                        }
                        self.learned_patterns["temporal_patterns"].append(pattern)
    
    async def _generate_rules_from_patterns(self):
        """Generate email rules from learned patterns."""
        generated_rules = []
        
        # Generate rules from sender patterns
        for pattern in self.learned_patterns["sender_patterns"]:
            if pattern["confidence"] >= 0.8:  # High confidence threshold
                rule = self._create_sender_rule(pattern)
                if rule:
                    generated_rules.append(rule)
        
        # Generate rules from subject patterns
        for pattern in self.learned_patterns["subject_patterns"]:
            if pattern["confidence"] >= 0.8:
                rule = self._create_subject_rule(pattern)
                if rule:
                    generated_rules.append(rule)
        
        # Generate rules from content patterns
        for pattern in self.learned_patterns["content_patterns"]:
            if pattern["confidence"] >= 0.85:  # Higher threshold for content
                rule = self._create_content_rule(pattern)
                if rule:
                    generated_rules.append(rule)
        
        # Add to auto-generated rules
        self.auto_generated_rules.extend(generated_rules)
        
        # Add high-confidence rules to active rules
        high_confidence_rules = [
            rule for rule in generated_rules 
            if self._get_rule_confidence(rule) >= 0.9
        ]
        
        self.rules.extend(high_confidence_rules)
        logger.info(f"Generated {len(generated_rules)} rules, {len(high_confidence_rules)} added to active set")
    
    def _create_sender_rule(self, pattern: Dict[str, Any]) -> Optional[EmailRule]:
        """Create a rule from sender pattern."""
        try:
            rule_id = f"auto_sender_{pattern['sender'].replace('@', '_at_').replace('.', '_')}"
            
            condition = RuleCondition(
                field="from",
                operator="equals",
                value=pattern["sender"],
                case_sensitive=False
            )
            
            action_key = "set_category" if "category" in pattern else "set_priority"
            action_value = pattern.get("category") or pattern.get("priority")
            
            rule = EmailRule(
                id=rule_id,
                name=f"Auto: {pattern['sender']} → {action_value}",
                description=f"Auto-generated rule based on sender pattern (confidence: {pattern['confidence']:.2f})",
                conditions=[condition],
                actions={action_key: action_value},
                enabled=True,
                priority=100,  # Lower priority for auto-generated rules
                metadata={
                    "auto_generated": True,
                    "confidence": pattern["confidence"],
                    "sample_size": pattern["sample_size"],
                    "pattern_type": "sender"
                }
            )
            
            return rule
            
        except Exception as e:
            logger.error(f"Failed to create sender rule: {str(e)}")
            return None
    
    def _create_subject_rule(self, pattern: Dict[str, Any]) -> Optional[EmailRule]:
        """Create a rule from subject pattern."""
        try:
            rule_id = f"auto_subject_{pattern['keyword'].replace(' ', '_')}"
            
            condition = RuleCondition(
                field="subject",
                operator="contains",
                value=pattern["keyword"],
                case_sensitive=False
            )
            
            action_key = "set_category" if "category" in pattern else "set_priority"
            action_value = pattern.get("category") or pattern.get("priority")
            
            rule = EmailRule(
                id=rule_id,
                name=f"Auto: Subject '{pattern['keyword']}' → {action_value}",
                description=f"Auto-generated rule based on subject keyword (confidence: {pattern['confidence']:.2f})",
                conditions=[condition],
                actions={action_key: action_value},
                enabled=True,
                priority=101,
                metadata={
                    "auto_generated": True,
                    "confidence": pattern["confidence"],
                    "sample_size": pattern["sample_size"],
                    "pattern_type": "subject"
                }
            )
            
            return rule
            
        except Exception as e:
            logger.error(f"Failed to create subject rule: {str(e)}")
            return None
    
    def _create_content_rule(self, pattern: Dict[str, Any]) -> Optional[EmailRule]:
        """Create a rule from content pattern."""
        try:
            # Content rules are more complex and require careful mapping
            feature = pattern["feature"]
            
            # Skip complex features for now
            if "_" in feature and not feature.startswith("has_"):
                return None
            
            rule_id = f"auto_content_{feature}"
            
            # Create appropriate condition based on feature type
            if feature.startswith("has_"):
                # Boolean feature
                keyword = feature.replace("has_", "").replace("_", " ")
                condition = RuleCondition(
                    field="body",
                    operator="contains",
                    value=keyword,
                    case_sensitive=False
                )
            else:
                # Skip other feature types for now
                return None
            
            rule = EmailRule(
                id=rule_id,
                name=f"Auto: Content '{feature}' → {pattern['category']}",
                description=f"Auto-generated rule based on content pattern (confidence: {pattern['confidence']:.2f})",
                conditions=[condition],
                actions={"set_category": pattern["category"]},
                enabled=True,
                priority=102,
                metadata={
                    "auto_generated": True,
                    "confidence": pattern["confidence"],
                    "sample_size": pattern["sample_size"],
                    "pattern_type": "content"
                }
            )
            
            return rule
            
        except Exception as e:
            logger.error(f"Failed to create content rule: {str(e)}")
            return None
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Remove common stop words and extract meaningful terms
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "this", "that", "is", "are", "was", "were", "be",
            "been", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "can", "from", "up", "about", "into",
            "through", "during", "before", "after", "above", "below", "over", "under"
        }
        
        # Extract words, convert to lowercase, filter stop words
        words = re.findall(r'\\b\\w+\\b', text.lower())
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # Also extract common phrases
        phrases = []
        for i in range(len(keywords) - 1):
            phrase = f"{keywords[i]} {keywords[i+1]}"
            if len(phrase) <= 20:  # Reasonable phrase length
                phrases.append(phrase)
        
        return keywords + phrases
    
    def _extract_content_features(self, text: str) -> Dict[str, Any]:
        """Extract features from email content."""
        features = {}
        
        # Length features
        features["char_count"] = len(text)
        features["word_count"] = len(text.split())
        features["line_count"] = len(text.split('\\n'))
        
        # Formatting features
        features["has_html"] = "<" in text and ">" in text
        features["has_links"] = "http" in text.lower()
        features["has_attachments"] = "attachment" in text.lower()
        
        # Urgency indicators
        urgency_words = ["urgent", "asap", "immediate", "emergency", "critical", "rush"]
        features["has_urgency"] = any(word in text.lower() for word in urgency_words)
        
        # Question indicators
        features["has_questions"] = "?" in text
        features["question_count"] = text.count("?")
        
        # Emotional indicators
        positive_words = ["thank", "great", "excellent", "pleased", "happy"]
        negative_words = ["problem", "issue", "error", "failed", "wrong", "disappointed"]
        
        features["has_positive_sentiment"] = any(word in text.lower() for word in positive_words)
        features["has_negative_sentiment"] = any(word in text.lower() for word in negative_words)
        
        # Professional indicators
        professional_words = ["please", "kindly", "regarding", "sincerely", "respectfully"]
        features["has_professional_tone"] = any(word in text.lower() for word in professional_words)
        
        # All caps (shouting)
        features["has_all_caps"] = any(word.isupper() and len(word) > 3 for word in text.split())
        
        return features
    
    def _bin_numerical_feature(self, feature: str, value: float) -> str:
        """Bin numerical features into categories."""
        if "count" in feature:
            if value <= 50:
                return "low"
            elif value <= 200:
                return "medium"
            else:
                return "high"
        else:
            # Default binning
            if value <= 1:
                return "very_low"
            elif value <= 5:
                return "low"
            elif value <= 20:
                return "medium"
            else:
                return "high"
    
    def _get_rule_confidence(self, rule: EmailRule) -> float:
        """Get confidence score for a rule."""
        metadata = getattr(rule, "metadata", {})
        return metadata.get("confidence", 0.5)
    
    async def _update_rule_performance(self, emails: List[Email], user_feedback: Dict[str, Any] = None):
        """Update rule performance metrics."""
        if not emails:
            return
        
        for rule in self.rules:
            matches = 0
            correct_predictions = 0
            
            for email in emails:
                if self.matches_conditions(email, rule.conditions):
                    matches += 1
                    
                    # Check if rule would have made correct prediction
                    if "set_category" in rule.actions:
                        predicted_category = rule.actions["set_category"]
                        if email.category.value == predicted_category:
                            correct_predictions += 1
                    
                    if "set_priority" in rule.actions:
                        predicted_priority = rule.actions["set_priority"]
                        if email.priority.value == predicted_priority:
                            correct_predictions += 1
            
            # Update performance metrics
            self.rule_performance[rule.id]["matches"] += matches
            if matches > 0:
                accuracy = correct_predictions / matches
                self.rule_performance[rule.id]["accuracy"] = accuracy
    
    async def suggest_rule_improvements(self) -> List[Dict[str, Any]]:
        """Suggest improvements to existing rules."""
        suggestions = []
        
        for rule_id, performance in self.rule_performance.items():
            if performance["matches"] >= 10:  # Enough data
                if performance["accuracy"] < 0.6:  # Poor performance
                    rule = next((r for r in self.rules if r.id == rule_id), None)
                    if rule:
                        suggestion = {
                            "rule_id": rule_id,
                            "rule_name": rule.name,
                            "current_accuracy": performance["accuracy"],
                            "matches": performance["matches"],
                            "suggestion": "Consider disabling or modifying this rule due to low accuracy",
                            "type": "low_accuracy"
                        }
                        suggestions.append(suggestion)
                
                elif performance["accuracy"] > 0.9 and not rule.enabled:  # High performance but disabled
                    suggestion = {
                        "rule_id": rule_id,
                        "rule_name": rule.name,
                        "current_accuracy": performance["accuracy"],
                        "matches": performance["matches"],
                        "suggestion": "Consider enabling this high-performing rule",
                        "type": "enable_suggestion"
                    }
                    suggestions.append(suggestion)
        
        return suggestions
    
    async def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights from the learning process."""
        return {
            "learned_patterns": {
                pattern_type: len(patterns)
                for pattern_type, patterns in self.learned_patterns.items()
            },
            "auto_generated_rules": len(self.auto_generated_rules),
            "rule_performance": dict(self.rule_performance),
            "high_confidence_patterns": [
                pattern for patterns in self.learned_patterns.values()
                for pattern in patterns
                if pattern.get("confidence", 0) >= 0.9
            ],
            "learning_enabled": self.learning_enabled,
            "confidence_threshold": self.confidence_threshold
        }
    
    def set_learning_parameters(self, enabled: bool = None, confidence_threshold: float = None):
        """Update learning parameters."""
        if enabled is not None:
            self.learning_enabled = enabled
        
        if confidence_threshold is not None:
            self.confidence_threshold = max(0.5, min(1.0, confidence_threshold))
        
        logger.info(f"Learning parameters updated: enabled={self.learning_enabled}, threshold={self.confidence_threshold}")
    
    async def export_learned_rules(self) -> List[Dict[str, Any]]:
        """Export auto-generated rules for review."""
        return [
            {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "conditions": [cond.model_dump() for cond in rule.conditions],
                "actions": rule.actions,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "metadata": getattr(rule, "metadata", {}),
                "performance": self.rule_performance.get(rule.id, {})
            }
            for rule in self.auto_generated_rules
        ]
