"""Triage agent for intelligent email screening and attention scoring."""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

from ..config import settings
from ..models import Email, EmailCategory, EmailPriority
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
            # This would query the database for user's sent emails and response times
            sender_scores = {}
            
            # Example calculation (would be based on real data):
            # - Fast response time = higher importance
            # - Frequent communication = higher importance  
            # - Work domain = higher importance
            # - Manual priority flags = higher importance
            
            # For now, use some defaults based on common patterns
            default_scores = {
                "boss@": 0.9,
                "manager@": 0.8,
                "team@": 0.7,
                "@company.com": 0.6,  # Work domain
                "noreply@": 0.1,
                "notification@": 0.2,
                "@facebook.com": 0.3,
                "@linkedin.com": 0.3,
                "@twitter.com": 0.2
            }
            
            return default_scores
            
        except Exception as e:
            logger.error(f"Failed to calculate sender importance: {str(e)}")
            return {}
    
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
            feedback = {
                "email_id": email_id,
                "correct_decision": correct_decision.value,
                "user_action": user_action,
                "timestamp": datetime.now().isoformat()
            }
            
            self.stats["accuracy_feedback"].append(feedback)
            
            # Update sender importance if this was a sender-related correction
            # Update urgency patterns if this was urgency-related
            # This would involve more sophisticated ML updates in a real implementation
            
            logger.info(f"Learning from feedback: email {email_id} should be {correct_decision.value}")
            
        except Exception as e:
            logger.error(f"Failed to process user feedback: {str(e)}")
    
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
