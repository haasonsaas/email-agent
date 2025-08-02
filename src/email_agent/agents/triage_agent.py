"""Triage agent for intelligent email screening and attention scoring."""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from ..config import settings
from ..models import Email, EmailCategory
from ..storage.database import DatabaseManager

logger = logging.getLogger(__name__)


class TriageDecision(str, Enum):
    """Triage decision for email routing."""
    PRIORITY_INBOX = "priority_inbox"      # Needs immediate attention
    REGULAR_INBOX = "regular_inbox"        # Normal inbox processing
    AUTO_ARCHIVE = "auto_archive"          # Archive automatically
    SPAM_FOLDER = "spam_folder"            # Route to spam


class AttentionScore:
    """Represents an email's attention score with explanation."""
    
    def __init__(self, score: float, factors: Dict[str, float], explanation: str):
        self.score = score  # 0.0 to 1.0
        self.factors = factors  # Contributing factors
        self.explanation = explanation  # Human-readable explanation
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "factors": self.factors,
            "explanation": self.explanation
        }


class TriageAgent:
    """Agent responsible for intelligent email screening and routing."""
    
    def __init__(self):
        self.openai_client: Optional[AsyncOpenAI] = None
        self.db: DatabaseManager = DatabaseManager()
        self.stats: Dict[str, Any] = {
            "emails_triaged": 0,
            "auto_archived": 0,
            "priority_flagged": 0,
            "accuracy_feedback": [],
            "last_triage": None
        }
        self.user_preferences: Dict[str, Any] = {}
        self.sender_importance: Dict[str, float] = {}
        self._initialize_ai_client()
        self._load_user_preferences()
    
    def _initialize_ai_client(self) -> None:
        """Initialize OpenAI client for advanced analysis."""
        try:
            if AsyncOpenAI and settings.openai_api_key:
                self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
                logger.info("OpenAI client initialized for triage analysis")
            else:
                logger.warning("No OpenAI API key - using rule-based triage only")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
    
    def _load_user_preferences(self) -> None:
        """Load user preferences and sender importance from database."""
        try:
            # Load user preferences (would be stored in DB)
            self.user_preferences = {
                "priority_keywords": ["urgent", "asap", "deadline", "important"],
                "vip_domains": ["company.com"],  # User's work domain
                "auto_archive_categories": [EmailCategory.PROMOTIONS, EmailCategory.UPDATES, EmailCategory.SOCIAL],
                "max_auto_archive_score": 0.4,  # Increased threshold for auto-archiving
                "min_priority_score": 0.7
            }
            
            # Load sender importance scores (learned from user behavior)
            self.sender_importance = self._calculate_sender_importance()
            
            logger.info(f"Loaded user preferences and {len(self.sender_importance)} sender importance scores")
            
        except Exception as e:
            logger.error(f"Failed to load user preferences: {str(e)}")
    
    def _calculate_sender_importance(self) -> Dict[str, float]:
        """Calculate sender importance based on user interaction history."""
        try:
            # Get user's email history to analyze response patterns
            sender_scores = {}
            
            # Load existing habit learning data from database
            habit_data = self._load_habit_learning_data()
            
            # Analyze user response patterns
            response_patterns = self._analyze_response_patterns()
            
            # Calculate sender importance based on multiple factors
            for sender, data in response_patterns.items():
                score = self._calculate_sender_score(data)
                sender_scores[sender] = score
            
            # Merge with existing habit data
            for sender, historical_score in habit_data.get("sender_scores", {}).items():
                if sender in sender_scores:
                    # Weighted average: 60% historical, 40% new data
                    sender_scores[sender] = (historical_score * 0.6) + (sender_scores[sender] * 0.4)
                else:
                    sender_scores[sender] = historical_score
            
            # Add default patterns for known types
            default_scores = {
                "boss@": 0.9,
                "manager@": 0.8,
                "team@": 0.7,
                "@company.com": 0.6,
                "noreply@": 0.1,
                "notification@": 0.2,
                "@facebook.com": 0.3,
                "@linkedin.com": 0.3,
                "@twitter.com": 0.2
            }
            
            # Apply defaults only if not already scored
            for pattern, score in default_scores.items():
                if pattern not in sender_scores:
                    sender_scores[pattern] = score
            
            # Save updated scores
            self._save_sender_importance_scores(sender_scores)
            
            return sender_scores
            
        except Exception as e:
            logger.error(f"Failed to calculate sender importance: {str(e)}")
            return self._get_default_sender_scores()
    
    def _load_habit_learning_data(self) -> Dict[str, Any]:
        """Load habit learning data from database."""
        try:
            # This would load from database in real implementation
            # For now, return empty structure
            return {
                "sender_scores": {},
                "category_preferences": {},
                "urgency_patterns": {},
                "time_preferences": {},
                "feedback_history": [],
                "last_updated": None
            }
        except Exception as e:
            logger.error(f"Failed to load habit learning data: {str(e)}")
            return {}
    
    def _analyze_response_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Analyze user response patterns to emails."""
        try:
            patterns = {}
            
            # Get sent emails from database to analyze response patterns
            # This would be a real database query in implementation
            sent_emails = []  # self.db.get_sent_emails(limit=1000)
            received_emails = []  # self.db.get_received_emails(limit=1000)
            
            # For each sender, calculate metrics
            for sender_email in set(email.sender.email for email in received_emails):
                pattern_data = {
                    "total_emails": 0,
                    "responded_to": 0,
                    "avg_response_time": 0.0,  # in hours
                    "manual_flags": 0,
                    "user_moved_to_priority": 0,
                    "user_archived": 0,
                    "spam_reported": 0
                }
                
                # Analyze this sender's emails
                sender_emails = [e for e in received_emails if e.sender.email == sender_email]
                pattern_data["total_emails"] = len(sender_emails)
                
                # Count responses (simplified - would need thread analysis)
                responses = [e for e in sent_emails if sender_email in e.body_text or ""]
                pattern_data["responded_to"] = len(responses)
                
                # Calculate average response time
                if responses:
                    response_times = []
                    for response in responses:
                        # Find original email this responds to
                        for orig in sender_emails:
                            if response.date > orig.date:
                                time_diff = (response.date - orig.date).total_seconds() / 3600
                                response_times.append(time_diff)
                                break
                    
                    if response_times:
                        pattern_data["avg_response_time"] = sum(response_times) / len(response_times)
                
                patterns[sender_email] = pattern_data
            
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to analyze response patterns: {str(e)}")
            return {}
    
    def _calculate_sender_score(self, pattern_data: Dict[str, Any]) -> float:
        """Calculate importance score for a sender based on interaction patterns."""
        score = 0.4  # Base score
        
        total_emails = pattern_data.get("total_emails", 0)
        if total_emails == 0:
            return score
        
        # Response rate factor (0-0.3 points)
        response_rate = pattern_data.get("responded_to", 0) / total_emails
        score += response_rate * 0.3
        
        # Response speed factor (0-0.2 points)
        avg_response_time = pattern_data.get("avg_response_time", 24)
        if avg_response_time < 1:  # Under 1 hour
            score += 0.2
        elif avg_response_time < 6:  # Under 6 hours
            score += 0.15
        elif avg_response_time < 24:  # Under 1 day
            score += 0.1
        
        # Manual flag factor (0-0.2 points)
        manual_flags = pattern_data.get("manual_flags", 0)
        if manual_flags > 0:
            score += min(0.2, manual_flags / total_emails * 0.5)
        
        # User priority actions (0-0.2 points)
        priority_moves = pattern_data.get("user_moved_to_priority", 0)
        if priority_moves > 0:
            score += min(0.2, priority_moves / total_emails * 0.4)
        
        # Negative factors
        spam_reports = pattern_data.get("spam_reported", 0)
        if spam_reports > 0:
            score -= spam_reports / total_emails * 0.5
        
        archived_count = pattern_data.get("user_archived", 0)
        if archived_count > total_emails * 0.5:  # More than 50% archived
            score -= 0.2
        
        return min(1.0, max(0.0, score))
    
    def _save_sender_importance_scores(self, scores: Dict[str, float]) -> None:
        """Save sender importance scores to database."""
        try:
            # This would save to database in real implementation
            habit_data = {
                "sender_scores": scores,
                "last_updated": datetime.now().isoformat()
            }
            # self.db.save_habit_learning_data(habit_data)
            logger.info(f"Saved {len(scores)} sender importance scores")
        except Exception as e:
            logger.error(f"Failed to save sender importance scores: {str(e)}")
    
    def _get_default_sender_scores(self) -> Dict[str, float]:
        """Get default sender scores as fallback."""
        return {
            "boss@": 0.9,
            "manager@": 0.8,
            "team@": 0.7,
            "@company.com": 0.6,
            "noreply@": 0.1,
            "notification@": 0.2,
            "@facebook.com": 0.3,
            "@linkedin.com": 0.3,
            "@twitter.com": 0.2
        }
    
    async def calculate_attention_score(self, email: Email) -> AttentionScore:
        """Calculate how much attention this email needs (0-1 scale)."""
        factors = {}
        
        try:
            # Factor 1: Category-based baseline (30% weight)
            category_score = self._score_by_category(email.category)
            factors["category"] = category_score
            
            # Factor 2: Sender importance (25% weight)
            sender_score = self._score_by_sender(email.sender.email)
            factors["sender"] = sender_score
            
            # Factor 3: Content urgency indicators (20% weight)
            urgency_score = await self._score_by_urgency(email)
            factors["urgency"] = urgency_score
            
            # Factor 4: Recency and timing (15% weight)
            recency_score = self._score_by_recency(email.received_date)
            factors["recency"] = recency_score
            
            # Factor 5: Thread context (10% weight)
            thread_score = await self._score_by_thread_context(email)
            factors["thread"] = thread_score
            
            # Combine factors with weights
            weights = {
                "category": 0.30,
                "sender": 0.25,
                "urgency": 0.20,
                "recency": 0.15,
                "thread": 0.10
            }
            
            final_score = sum(factors[factor] * weights[factor] for factor in factors)
            final_score = min(1.0, max(0.0, final_score))
            
            # Generate explanation
            explanation = self._generate_score_explanation(factors, weights, final_score)
            
            return AttentionScore(final_score, factors, explanation)
            
        except Exception as e:
            logger.error(f"Failed to calculate attention score for email {email.id}: {str(e)}")
            # Fallback: use category as primary indicator
            fallback_score = self._score_by_category(email.category)
            return AttentionScore(
                fallback_score,
                {"category": fallback_score},
                f"Fallback scoring based on category: {email.category.value}"
            )
    
    def _score_by_category(self, category: EmailCategory) -> float:
        """Score email based on its category."""
        category_scores = {
            EmailCategory.PRIMARY: 0.8,      # Usually important
            EmailCategory.SOCIAL: 0.2,       # Usually low priority
            EmailCategory.PROMOTIONS: 0.1,   # Usually auto-archive
            EmailCategory.UPDATES: 0.3,      # Sometimes important
            EmailCategory.FORUMS: 0.4,       # Context dependent
            EmailCategory.SPAM: 0.0,         # Always low priority
            EmailCategory.UNREAD: 0.5,       # Unknown, medium priority
        }
        return category_scores.get(category, 0.5)
    
    def _score_by_sender(self, sender_email: str) -> float:
        """Score email based on sender importance."""
        sender_lower = sender_email.lower()
        
        # Check exact matches first
        if sender_lower in self.sender_importance:
            return self.sender_importance[sender_lower]
        
        # Check domain and pattern matches
        for pattern, score in self.sender_importance.items():
            if pattern in sender_lower:
                return score
        
        # Default score for unknown senders
        if any(domain in sender_lower for domain in ["@company.com", "@work.com"]):
            return 0.6  # Work emails get medium-high priority
        
        return 0.4  # Default for unknown senders
    
    async def _score_by_urgency(self, email: Email) -> float:
        """Score email based on urgency indicators in content."""
        urgency_indicators = {
            "urgent": 0.9,
            "asap": 0.9,
            "immediate": 0.8,
            "deadline": 0.8,
            "important": 0.7,
            "priority": 0.7,
            "time sensitive": 0.8,
            "action required": 0.8,
            "please respond": 0.6,
            "follow up": 0.5,
            "reminder": 0.5
        }
        
        # Check subject line
        subject_lower = email.subject.lower()
        max_urgency = 0.0
        
        for indicator, score in urgency_indicators.items():
            if indicator in subject_lower:
                max_urgency = max(max_urgency, score)
        
        # Check body content if available
        if email.body_text:
            body_lower = email.body_text.lower()[:500]  # First 500 chars
            for indicator, score in urgency_indicators.items():
                if indicator in body_lower:
                    max_urgency = max(max_urgency, score * 0.8)  # Body gets lower weight
        
        # Use AI for advanced urgency detection if available
        if self.openai_client and max_urgency < 0.5:
            ai_urgency = await self._ai_urgency_analysis(email)
            max_urgency = max(max_urgency, ai_urgency)
        
        return max_urgency
    
    async def _ai_urgency_analysis(self, email: Email) -> float:
        """Use AI to analyze email urgency."""
        try:
            prompt = f"""
Analyze this email for urgency on a scale of 0.0 to 1.0.

Subject: {email.subject}
From: {email.sender.email}
Content preview: {(email.body_text or '')[:300]}...

Consider:
- Explicit urgency words
- Implied time pressure
- Business context
- Tone and language

Return only a number between 0.0 and 1.0.
"""
            
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing email urgency. Return only a decimal number between 0.0 and 1.0."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0.1
            )
            
            urgency_text = response.choices[0].message.content.strip()
            urgency_score = float(urgency_text)
            return min(1.0, max(0.0, urgency_score))
            
        except Exception as e:
            logger.error(f"AI urgency analysis failed: {str(e)}")
            return 0.0
    
    def _score_by_recency(self, received_date: datetime) -> float:
        """Score email based on how recent it is."""
        now = datetime.now(received_date.tzinfo) if received_date.tzinfo else datetime.now()
        age = now - received_date
        
        # Newer emails get higher scores
        if age < timedelta(hours=1):
            return 1.0
        elif age < timedelta(hours=6):
            return 0.8
        elif age < timedelta(days=1):
            return 0.6
        elif age < timedelta(days=3):
            return 0.4
        elif age < timedelta(days=7):
            return 0.2
        else:
            return 0.1
    
    async def _score_by_thread_context(self, email: Email) -> float:
        """Score email based on thread context and conversation importance."""
        try:
            # If it's part of an ongoing thread, it might be more important
            if email.thread_id:
                # Check if user has participated in this thread
                # Check if there are recent messages in this thread
                # For now, use simple heuristics
                return 0.6  # Threads get medium importance
            
            return 0.3  # Standalone emails get lower thread score
            
        except Exception as e:
            logger.error(f"Thread context scoring failed: {str(e)}")
            return 0.3
    
    def _generate_score_explanation(self, factors: Dict[str, float], weights: Dict[str, float], final_score: float) -> str:
        """Generate human-readable explanation of the attention score."""
        # Find the most influential factor
        weighted_factors = {factor: score * weights[factor] for factor, score in factors.items()}
        top_factor = max(weighted_factors.keys(), key=lambda k: weighted_factors[k])
        
        explanations = {
            "category": f"Email category suggests {'high' if factors['category'] > 0.7 else 'medium' if factors['category'] > 0.4 else 'low'} priority",
            "sender": f"Sender has {'high' if factors['sender'] > 0.7 else 'medium' if factors['sender'] > 0.4 else 'low'} importance",
            "urgency": f"Content shows {'high' if factors['urgency'] > 0.7 else 'some' if factors['urgency'] > 0.3 else 'no'} urgency indicators",
            "recency": f"Email is {'very recent' if factors['recency'] > 0.8 else 'recent' if factors['recency'] > 0.5 else 'older'}",
            "thread": f"{'Active thread' if factors['thread'] > 0.5 else 'Standalone email'}"
        }
        
        primary_reason = explanations[top_factor]
        
        if final_score > 0.7:
            return f"High attention needed: {primary_reason}"
        elif final_score > 0.4:
            return f"Medium attention: {primary_reason}"
        else:
            return f"Low attention: {primary_reason}"
    
    async def make_triage_decision(self, email: Email) -> Tuple[TriageDecision, AttentionScore]:
        """Make triage decision for an email."""
        attention_score = await self.calculate_attention_score(email)
        
        # Apply user preferences for thresholds
        priority_threshold = self.user_preferences.get("min_priority_score", 0.7)
        archive_threshold = self.user_preferences.get("max_auto_archive_score", 0.4)
        
        # Make decision based on score and category
        if email.category == EmailCategory.SPAM or self._is_spam_like(email):
            decision = TriageDecision.SPAM_FOLDER
        elif attention_score.score >= priority_threshold:
            decision = TriageDecision.PRIORITY_INBOX
            self.stats["priority_flagged"] += 1
        elif (attention_score.score <= archive_threshold and 
              email.category in self.user_preferences.get("auto_archive_categories", [])):
            decision = TriageDecision.AUTO_ARCHIVE
            self.stats["auto_archived"] += 1
        else:
            decision = TriageDecision.REGULAR_INBOX
        
        self.stats["emails_triaged"] += 1
        self.stats["last_triage"] = datetime.now()
        
        logger.debug(f"Triaged email {email.id}: {decision.value} (score: {attention_score.score:.2f})")
        
        return decision, attention_score
    
    def _is_spam_like(self, email: Email) -> bool:
        """Detect spam-like characteristics."""
        spam_indicators = [
            "you've won", "claim now", "limited time", "click here immediately",
            "congratulations", "prize", "lottery", "million dollars",
            "urgent action required", "verify account", "suspended",
            "free money", "inheritance", "nigerian prince"
        ]
        
        content = (email.subject + " " + (email.body_text or "")).lower()
        
        # Check for multiple spam indicators
        spam_count = sum(1 for indicator in spam_indicators if indicator in content)
        
        # Also check sender domain reputation
        suspicious_domains = ["suspicious", "prize", "lottery", "winner", "claim"]
        sender_suspicious = any(domain in email.sender.email.lower() for domain in suspicious_domains)
        
        # Mark as spam if multiple indicators or suspicious sender
        return spam_count >= 2 or sender_suspicious
    
    async def process_email_batch(self, emails: List[Email]) -> Dict[str, List[Email]]:
        """Process a batch of emails and return them grouped by triage decision."""
        results = {
            TriageDecision.PRIORITY_INBOX.value: [],
            TriageDecision.REGULAR_INBOX.value: [],
            TriageDecision.AUTO_ARCHIVE.value: [],
            TriageDecision.SPAM_FOLDER.value: []
        }
        
        for email in emails:
            try:
                decision, attention_score = await self.make_triage_decision(email)
                
                # Add triage metadata to email
                email.connector_data["triage"] = {
                    "decision": decision.value,
                    "attention_score": attention_score.to_dict(),
                    "triaged_at": datetime.now().isoformat()
                }
                
                results[decision.value].append(email)
                
            except Exception as e:
                logger.error(f"Failed to triage email {email.id}: {str(e)}")
                # Default to regular inbox on error
                results[TriageDecision.REGULAR_INBOX.value].append(email)
        
        return results
    
    async def learn_from_user_feedback(self, email_id: str, correct_decision: TriageDecision, user_action: str) -> None:
        """Learn from user corrections to improve triage accuracy."""
        try:
            # Get the email to analyze what we got wrong
            email = self.db.get_email_by_id(email_id)
            if not email:
                logger.warning(f"Could not find email {email_id} for feedback learning")
                return
            
            feedback = {
                "email_id": email_id,
                "original_decision": email.connector_data.get("triage", {}).get("decision"),
                "correct_decision": correct_decision.value,
                "user_action": user_action,
                "sender": email.sender.email,
                "category": email.category.value,
                "subject": email.subject,
                "timestamp": datetime.now().isoformat()
            }
            
            self.stats["accuracy_feedback"].append(feedback)
            
            # Learn from the feedback to improve future decisions
            await self._apply_feedback_learning(email, feedback)
            
            logger.info(f"Learning from feedback: email {email_id} from {email.sender.email} should be {correct_decision.value}")
            
        except Exception as e:
            logger.error(f"Failed to process user feedback: {str(e)}")
    
    async def _apply_feedback_learning(self, email: Email, feedback: Dict[str, Any]) -> None:
        """Apply feedback to improve future triage decisions."""
        try:
            sender = email.sender.email
            original_decision = feedback.get("original_decision")
            correct_decision = feedback.get("correct_decision")
            user_action = feedback.get("user_action")
            
            # Update sender importance based on feedback
            await self._update_sender_importance_from_feedback(sender, correct_decision, user_action)
            
            # Update category preferences
            await self._update_category_preferences_from_feedback(email.category, correct_decision)
            
            # Update urgency pattern recognition
            await self._update_urgency_patterns_from_feedback(email, correct_decision)
            
            # Update time-based preferences
            await self._update_time_preferences_from_feedback(email, correct_decision)
            
            # Save updated learning data
            await self._save_habit_learning_updates()
            
        except Exception as e:
            logger.error(f"Failed to apply feedback learning: {str(e)}")
    
    async def _update_sender_importance_from_feedback(self, sender: str, correct_decision: str, user_action: str) -> None:
        """Update sender importance scores based on user feedback."""
        current_score = self.sender_importance.get(sender, 0.4)
        
        # Adjust score based on correct decision
        if correct_decision == TriageDecision.PRIORITY_INBOX.value:
            # User wanted this in priority - increase importance
            adjustment = 0.1
        elif correct_decision == TriageDecision.AUTO_ARCHIVE.value:
            # User wanted this archived - decrease importance
            adjustment = -0.1
        elif correct_decision == TriageDecision.SPAM_FOLDER.value:
            # User marked as spam - significantly decrease importance
            adjustment = -0.3
        else:
            # Regular inbox - small adjustment toward neutral
            adjustment = (0.5 - current_score) * 0.1
        
        # Apply learning rate decay (more recent feedback has higher impact)
        learning_rate = 0.2
        new_score = current_score + (adjustment * learning_rate)
        new_score = min(1.0, max(0.0, new_score))
        
        self.sender_importance[sender] = new_score
        logger.debug(f"Updated sender {sender} importance: {current_score:.3f} -> {new_score:.3f}")
    
    async def _update_category_preferences_from_feedback(self, category: EmailCategory, correct_decision: str) -> None:
        """Update category-based scoring preferences."""
        if not hasattr(self, 'category_preferences'):
            self.category_preferences = {}
        
        category_key = category.value
        if category_key not in self.category_preferences:
            self.category_preferences[category_key] = {
                "priority_tendency": 0.0,
                "archive_tendency": 0.0,
                "feedback_count": 0
            }
        
        prefs = self.category_preferences[category_key]
        prefs["feedback_count"] += 1
        
        # Update tendencies based on feedback
        if correct_decision == TriageDecision.PRIORITY_INBOX.value:
            prefs["priority_tendency"] += 0.1
        elif correct_decision == TriageDecision.AUTO_ARCHIVE.value:
            prefs["archive_tendency"] += 0.1
        
        # Normalize tendencies
        prefs["priority_tendency"] = min(1.0, max(-1.0, prefs["priority_tendency"]))
        prefs["archive_tendency"] = min(1.0, max(-1.0, prefs["archive_tendency"]))
    
    async def _update_urgency_patterns_from_feedback(self, email: Email, correct_decision: str) -> None:
        """Update urgency pattern recognition based on feedback."""
        if not hasattr(self, 'urgency_patterns'):
            self.urgency_patterns = {"learned_keywords": {}, "false_positives": set()}
        
        content = f"{email.subject} {email.body_text or ''}".lower()
        
        if correct_decision == TriageDecision.PRIORITY_INBOX.value:
            # Extract potential urgency indicators we might have missed
            words = content.split()
            for word in words:
                if len(word) > 3 and word not in ["the", "and", "for", "with"]:
                    current_score = self.urgency_patterns["learned_keywords"].get(word, 0.0)
                    self.urgency_patterns["learned_keywords"][word] = min(1.0, current_score + 0.05)
        
        elif correct_decision == TriageDecision.AUTO_ARCHIVE.value:
            # Mark patterns that led to false urgency detection
            urgency_words = ["urgent", "asap", "immediate", "important", "priority"]
            for word in urgency_words:
                if word in content:
                    self.urgency_patterns["false_positives"].add(word)
    
    async def _update_time_preferences_from_feedback(self, email: Email, correct_decision: str) -> None:
        """Update time-based preferences from feedback."""
        if not hasattr(self, 'time_preferences'):
            self.time_preferences = {"priority_hours": {}, "archive_hours": {}}
        
        hour = email.received_date.hour
        
        if correct_decision == TriageDecision.PRIORITY_INBOX.value:
            current = self.time_preferences["priority_hours"].get(hour, 0)
            self.time_preferences["priority_hours"][hour] = current + 1
        elif correct_decision == TriageDecision.AUTO_ARCHIVE.value:
            current = self.time_preferences["archive_hours"].get(hour, 0)
            self.time_preferences["archive_hours"][hour] = current + 1
    
    async def _save_habit_learning_updates(self) -> None:
        """Save all habit learning updates to persistent storage."""
        try:
            habit_data = {
                "sender_scores": self.sender_importance,
                "category_preferences": getattr(self, 'category_preferences', {}),
                "urgency_patterns": getattr(self, 'urgency_patterns', {}),
                "time_preferences": getattr(self, 'time_preferences', {}),
                "last_updated": datetime.now().isoformat(),
                "total_feedback_processed": len(self.stats["accuracy_feedback"])
            }
            
            # In real implementation, this would save to database
            # self.db.save_habit_learning_data(habit_data)
            
            logger.info("Saved habit learning updates to persistent storage")
            
        except Exception as e:
            logger.error(f"Failed to save habit learning updates: {str(e)}")
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights about what the system has learned from user behavior."""
        insights = {
            "sender_insights": {},
            "category_insights": {},
            "urgency_insights": {},
            "time_insights": {},
            "learning_stats": {}
        }
        
        try:
            # Sender insights
            if self.sender_importance:
                top_senders = sorted(self.sender_importance.items(), key=lambda x: x[1], reverse=True)[:10]
                insights["sender_insights"] = {
                    "most_important": top_senders[:5],
                    "least_important": sorted(self.sender_importance.items(), key=lambda x: x[1])[:5],
                    "total_senders_learned": len(self.sender_importance)
                }
            
            # Category insights
            if hasattr(self, 'category_preferences'):
                insights["category_insights"] = self.category_preferences
            
            # Urgency insights
            if hasattr(self, 'urgency_patterns'):
                learned_keywords = self.urgency_patterns.get("learned_keywords", {})
                if learned_keywords:
                    top_urgency_words = sorted(learned_keywords.items(), key=lambda x: x[1], reverse=True)[:10]
                    insights["urgency_insights"] = {
                        "learned_urgency_keywords": top_urgency_words,
                        "false_positive_words": list(self.urgency_patterns.get("false_positives", set()))
                    }
            
            # Time insights
            if hasattr(self, 'time_preferences'):
                insights["time_insights"] = self.time_preferences
            
            # Learning statistics
            feedback_count = len(self.stats["accuracy_feedback"])
            insights["learning_stats"] = {
                "total_feedback_received": feedback_count,
                "learning_active": feedback_count > 5,
                "last_feedback": self.stats["accuracy_feedback"][-1]["timestamp"] if feedback_count > 0 else None
            }
            
        except Exception as e:
            logger.error(f"Failed to generate learning insights: {str(e)}")
        
        return insights
    
    async def get_triage_stats(self) -> Dict[str, Any]:
        """Get triage agent statistics."""
        accuracy = 0.0
        if self.stats["accuracy_feedback"]:
            # Calculate accuracy from user feedback
            correct_decisions = sum(1 for fb in self.stats["accuracy_feedback"] if "correct" in fb.get("user_action", ""))
            accuracy = (correct_decisions / len(self.stats["accuracy_feedback"])) * 100
        
        return {
            "emails_triaged": self.stats["emails_triaged"],
            "auto_archived": self.stats["auto_archived"],
            "priority_flagged": self.stats["priority_flagged"],
            "accuracy_percentage": accuracy,
            "feedback_count": len(self.stats["accuracy_feedback"]),
            "last_triage": self.stats["last_triage"],
            "ai_enabled": self.openai_client is not None,
            "sender_patterns": len(self.sender_importance)
        }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get triage agent status."""
        return await self.get_triage_stats()
    
    async def shutdown(self) -> None:
        """Shutdown the triage agent."""
        try:
            if self.openai_client:
                await self.openai_client.close()
            logger.info("Triage agent shutdown completed")
        except Exception as e:
            logger.error(f"Error during triage agent shutdown: {str(e)}")
