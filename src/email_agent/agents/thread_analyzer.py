"""Thread analysis agent for email conversations."""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from ..config import settings
from ..models import Email, EmailThread, EmailPriority, EmailCategory
from ..sdk.base import BaseAgent
from ..sdk.exceptions import AgentError

logger = logging.getLogger(__name__)


class ThreadAnalyzer(BaseAgent):
    """Analyzes email threads and conversation patterns."""
    
    def __init__(self):
        super().__init__()
        self.openai_client = None
        self.stats = {
            "threads_analyzed": 0,
            "conversations_tracked": 0,
            "participants_identified": 0,
            "resolution_patterns_found": 0
        }
        self._initialize_llm()
    
    def _initialize_llm(self) -> None:
        """Initialize OpenAI client for advanced thread analysis."""
        try:
            if settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
                import openai
                self.openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
                logger.info("Thread analyzer LLM initialized")
            else:
                logger.warning("OpenAI API key not configured for thread analysis")
        except Exception as e:
            logger.error(f"Failed to initialize thread analyzer LLM: {str(e)}")
    
    async def analyze_thread(self, emails: List[Email]) -> Dict[str, Any]:
        """Analyze an email thread for patterns and insights."""
        if not emails:
            return {}
        
        try:
            # Sort emails by date
            sorted_emails = sorted(emails, key=lambda e: e.date)
            
            # Basic thread analysis
            basic_analysis = self._analyze_thread_structure(sorted_emails)
            
            # Advanced analysis with LLM if available
            if self.openai_client and len(sorted_emails) > 1:
                advanced_analysis = await self._analyze_thread_with_llm(sorted_emails)
                basic_analysis.update(advanced_analysis)
            
            # Conversation flow analysis
            flow_analysis = self._analyze_conversation_flow(sorted_emails)
            basic_analysis.update(flow_analysis)
            
            self.stats["threads_analyzed"] += 1
            
            return basic_analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze thread: {str(e)}")
            return {}
    
    def _analyze_thread_structure(self, emails: List[Email]) -> Dict[str, Any]:
        """Analyze basic thread structure and metadata."""
        if not emails:
            return {}
        
        # Participants analysis
        participants = set()
        senders = []
        
        for email in emails:
            participants.add(email.sender.email)
            senders.append(email.sender.email)
            
            # Add recipients
            for recipient in email.recipients:
                participants.add(recipient.email)
        
        # Time analysis
        first_email = emails[0]
        last_email = emails[-1]
        duration = last_email.date - first_email.date
        
        # Response patterns
        response_times = []
        for i in range(1, len(emails)):
            response_time = emails[i].date - emails[i-1].date
            response_times.append(response_time.total_seconds() / 3600)  # Hours
        
        # Priority and category analysis
        priorities = [email.priority.value for email in emails]
        categories = [email.category.value for email in emails]
        
        # Subject evolution
        subjects = [email.subject for email in emails]
        subject_changes = len(set(subjects))
        
        return {
            "thread_id": first_email.thread_id or f"thread-{first_email.id}",
            "message_count": len(emails),
            "participants": list(participants),
            "participant_count": len(participants),
            "duration_hours": duration.total_seconds() / 3600,
            "first_message": first_email.date.isoformat(),
            "last_message": last_email.date.isoformat(),
            "avg_response_time_hours": sum(response_times) / len(response_times) if response_times else 0,
            "priority_distribution": {p: priorities.count(p) for p in set(priorities)},
            "category_distribution": {c: categories.count(c) for c in set(categories)},
            "subject_changes": subject_changes,
            "is_escalating": self._detect_escalation(emails),
            "conversation_type": self._classify_conversation_type(emails),
            "resolution_status": self._detect_resolution_status(emails)
        }
    
    async def _analyze_thread_with_llm(self, emails: List[Email]) -> Dict[str, Any]:
        """Advanced thread analysis using LLM."""
        try:
            # Create conversation summary for LLM
            conversation_text = self._format_conversation_for_llm(emails)
            
            prompt = f"""
Analyze this email conversation thread and provide insights:

{conversation_text}

Provide analysis in this format:
CONVERSATION_TYPE: [support_ticket/project_discussion/negotiation/social/information_request/other]
SENTIMENT_TREND: [improving/declining/stable/mixed]
KEY_TOPICS: [comma-separated list of main topics]
RESOLUTION_STATUS: [resolved/pending/escalated/abandoned]
URGENCY_LEVEL: [low/medium/high/critical]
NEXT_ACTION_NEEDED: [specific action or "none"]
MAIN_PARTICIPANTS: [list key participants by role if apparent]
CONVERSATION_SUMMARY: [brief 2-3 sentence summary]
INSIGHTS: [key insights or patterns observed]
"""
            
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing email conversations and identifying patterns, trends, and insights."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.2
            )
            
            content = response.choices[0].message.content.strip()
            return self._parse_thread_analysis_response(content)
            
        except Exception as e:
            logger.error(f"LLM thread analysis failed: {str(e)}")
            return {}
    
    def _format_conversation_for_llm(self, emails: List[Email]) -> str:
        """Format email thread for LLM analysis."""
        conversation_parts = []
        
        for i, email in enumerate(emails):
            timestamp = email.date.strftime("%Y-%m-%d %H:%M")
            sender = email.sender.email
            subject = email.subject
            body_preview = (email.body_text or "")[:300] + ("..." if len(email.body_text or "") > 300 else "")
            
            conversation_parts.append(f"""
Message {i+1} [{timestamp}]
From: {sender}
Subject: {subject}
Content: {body_preview}
""")
        
        return "\\n".join(conversation_parts)
    
    def _parse_thread_analysis_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM thread analysis response."""
        result = {
            "llm_conversation_type": "other",
            "llm_sentiment_trend": "stable",
            "llm_key_topics": [],
            "llm_resolution_status": "pending",
            "llm_urgency_level": "medium",
            "llm_next_action": "none",
            "llm_participants": [],
            "llm_summary": "",
            "llm_insights": []
        }
        
        try:
            lines = content.split('\\n')
            for line in lines:
                line = line.strip()
                if line.startswith('CONVERSATION_TYPE:'):
                    result["llm_conversation_type"] = line.replace('CONVERSATION_TYPE:', '').strip().lower()
                elif line.startswith('SENTIMENT_TREND:'):
                    result["llm_sentiment_trend"] = line.replace('SENTIMENT_TREND:', '').strip().lower()
                elif line.startswith('KEY_TOPICS:'):
                    topics = line.replace('KEY_TOPICS:', '').strip()
                    result["llm_key_topics"] = [t.strip() for t in topics.split(',') if t.strip()]
                elif line.startswith('RESOLUTION_STATUS:'):
                    result["llm_resolution_status"] = line.replace('RESOLUTION_STATUS:', '').strip().lower()
                elif line.startswith('URGENCY_LEVEL:'):
                    result["llm_urgency_level"] = line.replace('URGENCY_LEVEL:', '').strip().lower()
                elif line.startswith('NEXT_ACTION_NEEDED:'):
                    result["llm_next_action"] = line.replace('NEXT_ACTION_NEEDED:', '').strip()
                elif line.startswith('MAIN_PARTICIPANTS:'):
                    participants = line.replace('MAIN_PARTICIPANTS:', '').strip()
                    result["llm_participants"] = [p.strip() for p in participants.split(',') if p.strip()]
                elif line.startswith('CONVERSATION_SUMMARY:'):
                    result["llm_summary"] = line.replace('CONVERSATION_SUMMARY:', '').strip()
                elif line.startswith('INSIGHTS:'):
                    insights = line.replace('INSIGHTS:', '').strip()
                    result["llm_insights"] = [insights] if insights else []
        
        except Exception as e:
            logger.error(f"Failed to parse thread analysis response: {str(e)}")
        
        return result
    
    def _analyze_conversation_flow(self, emails: List[Email]) -> Dict[str, Any]:
        """Analyze conversation flow patterns."""
        if len(emails) < 2:
            return {}
        
        # Response pattern analysis
        response_patterns = []
        participant_activity = defaultdict(int)
        
        for email in emails:
            participant_activity[email.sender.email] += 1
        
        # Detect conversation patterns
        patterns = {
            "ping_pong": self._detect_ping_pong_pattern(emails),
            "broadcast": self._detect_broadcast_pattern(emails),
            "escalation": self._detect_escalation_pattern(emails),
            "information_gathering": self._detect_info_gathering_pattern(emails)
        }
        
        # Communication frequency analysis
        time_gaps = []
        for i in range(1, len(emails)):
            gap = emails[i].date - emails[i-1].date
            time_gaps.append(gap.total_seconds() / 3600)  # Hours
        
        return {
            "communication_patterns": patterns,
            "most_active_participant": max(participant_activity.items(), key=lambda x: x[1])[0],
            "participant_activity": dict(participant_activity),
            "avg_time_gap_hours": sum(time_gaps) / len(time_gaps) if time_gaps else 0,
            "max_time_gap_hours": max(time_gaps) if time_gaps else 0,
            "conversation_rhythm": self._classify_conversation_rhythm(time_gaps)
        }
    
    def _detect_ping_pong_pattern(self, emails: List[Email]) -> bool:
        """Detect if conversation is a back-and-forth between two participants."""
        if len(emails) < 4:
            return False
        
        participants = [email.sender.email for email in emails]
        unique_participants = set(participants)
        
        if len(unique_participants) != 2:
            return False
        
        # Check for alternating pattern
        alternating_count = 0
        for i in range(1, len(participants)):
            if participants[i] != participants[i-1]:
                alternating_count += 1
        
        return alternating_count / (len(participants) - 1) > 0.7  # 70% alternating
    
    def _detect_broadcast_pattern(self, emails: List[Email]) -> bool:
        """Detect if conversation is primarily one-to-many broadcasting."""
        if len(emails) < 3:
            return False
        
        # Count recipients in each email
        total_recipients = sum(len(email.recipients) for email in emails)
        avg_recipients = total_recipients / len(emails)
        
        # Check if one sender dominates
        senders = [email.sender.email for email in emails]
        sender_counts = defaultdict(int)
        for sender in senders:
            sender_counts[sender] += 1
        
        max_sender_count = max(sender_counts.values())
        
        return avg_recipients > 2 and max_sender_count / len(emails) > 0.6
    
    def _detect_escalation_pattern(self, emails: List[Email]) -> bool:
        """Detect if conversation shows escalation patterns."""
        if len(emails) < 2:
            return False
        
        # Check for increasing priority
        priorities = [email.priority for email in emails]
        priority_values = {"low": 1, "normal": 2, "high": 3, "urgent": 4}
        
        priority_trend = 0
        for i in range(1, len(priorities)):
            curr_val = priority_values.get(priorities[i].value, 2)
            prev_val = priority_values.get(priorities[i-1].value, 2)
            if curr_val > prev_val:
                priority_trend += 1
        
        # Check for escalation keywords
        escalation_keywords = ["escalate", "urgent", "emergency", "critical", "manager", "supervisor"]
        escalation_mentions = 0
        
        for email in emails:
            text = f"{email.subject} {email.body_text or ''}".lower()
            if any(keyword in text for keyword in escalation_keywords):
                escalation_mentions += 1
        
        return priority_trend > 0 or escalation_mentions > 0
    
    def _detect_info_gathering_pattern(self, emails: List[Email]) -> bool:
        """Detect if conversation is primarily information gathering."""
        question_indicators = ["?", "what", "how", "when", "where", "why", "who", "could you", "can you", "please provide"]
        
        question_count = 0
        for email in emails:
            text = f"{email.subject} {email.body_text or ''}".lower()
            if any(indicator in text for indicator in question_indicators):
                question_count += 1
        
        return question_count / len(emails) > 0.5
    
    def _classify_conversation_rhythm(self, time_gaps: List[float]) -> str:
        """Classify the rhythm of conversation based on time gaps."""
        if not time_gaps:
            return "unknown"
        
        avg_gap = sum(time_gaps) / len(time_gaps)
        
        if avg_gap < 1:  # Less than 1 hour
            return "rapid"
        elif avg_gap < 24:  # Less than 1 day
            return "active"
        elif avg_gap < 168:  # Less than 1 week
            return "moderate"
        else:
            return "slow"
    
    def _detect_escalation(self, emails: List[Email]) -> bool:
        """Detect if thread shows escalation patterns."""
        return self._detect_escalation_pattern(emails)
    
    def _classify_conversation_type(self, emails: List[Email]) -> str:
        """Classify the type of conversation based on patterns."""
        if not emails:
            return "unknown"
        
        # Analyze subjects and content for patterns
        subjects = [email.subject.lower() for email in emails]
        all_text = " ".join([f"{email.subject} {email.body_text or ''}" for email in emails]).lower()
        
        # Support ticket indicators
        support_keywords = ["issue", "problem", "error", "bug", "help", "support", "ticket", "request"]
        if any(keyword in all_text for keyword in support_keywords):
            return "support_ticket"
        
        # Project discussion indicators
        project_keywords = ["project", "meeting", "status", "update", "progress", "milestone", "deadline"]
        if any(keyword in all_text for keyword in project_keywords):
            return "project_discussion"
        
        # Information request indicators
        info_keywords = ["information", "details", "clarification", "question", "inquiry"]
        if any(keyword in all_text for keyword in info_keywords):
            return "information_request"
        
        # Social/informal indicators
        social_keywords = ["hi", "hello", "thanks", "thank you", "regards", "best", "cheers"]
        if any(keyword in all_text for keyword in social_keywords):
            return "social"
        
        return "general"
    
    def _detect_resolution_status(self, emails: List[Email]) -> str:
        """Detect if conversation appears to be resolved."""
        if not emails:
            return "unknown"
        
        last_emails = emails[-2:] if len(emails) >= 2 else emails
        recent_text = " ".join([f"{email.subject} {email.body_text or ''}" for email in last_emails]).lower()
        
        # Resolution indicators
        resolution_keywords = ["resolved", "fixed", "solved", "completed", "done", "closed", "thank you", "thanks"]
        if any(keyword in recent_text for keyword in resolution_keywords):
            return "resolved"
        
        # Pending indicators
        pending_keywords = ["pending", "waiting", "follow up", "will get back", "investigating"]
        if any(keyword in recent_text for keyword in pending_keywords):
            return "pending"
        
        # Check time since last message
        if emails:
            time_since_last = datetime.now() - emails[-1].date
            if time_since_last.days > 7:
                return "stale"
        
        return "active"
    
    async def find_related_threads(self, emails: List[Email]) -> List[Dict[str, Any]]:
        """Find emails that belong to the same conversation threads."""
        if not emails:
            return []
        
        # Group by thread_id first
        thread_groups = defaultdict(list)
        for email in emails:
            thread_id = email.thread_id or email.id
            thread_groups[thread_id].append(email)
        
        # Analyze each thread
        thread_analyses = []
        for thread_id, thread_emails in thread_groups.items():
            if len(thread_emails) > 1:  # Only analyze actual threads
                analysis = await self.analyze_thread(thread_emails)
                analysis["emails"] = thread_emails
                thread_analyses.append(analysis)
        
        return sorted(thread_analyses, key=lambda x: x.get("duration_hours", 0), reverse=True)
    
    async def get_status(self) -> Dict[str, Any]:
        """Get thread analyzer status."""
        return {
            "llm_available": self.openai_client is not None,
            "stats": self.stats.copy(),
            "analysis_capabilities": [
                "thread_structure", "conversation_flow", "participant_analysis",
                "escalation_detection", "resolution_tracking", "pattern_recognition"
            ]
        }
    
    async def shutdown(self) -> None:
        """Shutdown the thread analyzer."""
        try:
            if self.openai_client:
                await self.openai_client.close()
            logger.info("Thread analyzer shutdown completed")
        except Exception as e:
            logger.error(f"Error during thread analyzer shutdown: {str(e)}")
