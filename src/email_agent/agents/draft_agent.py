"""AI Draft Suggestions Agent for analyzing user writing style and generating email drafts."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import re
import statistics

from openai import OpenAI

from ..models import Email
from ..sdk.base import BaseAgent


logger = logging.getLogger(__name__)


@dataclass
class WritingStyle:
    """User's writing style profile."""
    avg_length: int = 0  # Average email length in words
    formality_score: float = 0.5  # 0=casual, 1=formal
    greeting_style: str = "Hi"  # Most common greeting
    closing_style: str = "Best"  # Most common closing
    tone_keywords: List[str] = field(default_factory=list)  # Common words/phrases
    sentence_complexity: float = 0.5  # 0=simple, 1=complex
    punctuation_style: Dict[str, float] = field(default_factory=dict)
    common_phrases: List[str] = field(default_factory=list)
    response_patterns: Dict[str, str] = field(default_factory=dict)  # Context -> typical response
    
    # Temporal patterns
    response_speed: str = "medium"  # fast, medium, slow
    preferred_times: List[int] = field(default_factory=list)  # Hours of day
    
    # Contextual patterns
    work_style: Dict[str, Any] = field(default_factory=dict)
    personal_style: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DraftSuggestion:
    """A suggested email draft."""
    subject: str
    body: str
    confidence: float  # 0.0-1.0 confidence in the suggestion
    reasoning: str  # Why this draft was generated
    style_match: float  # How well it matches user's style (0.0-1.0)
    suggested_tone: str  # formal, casual, urgent, friendly, etc.
    key_points: List[str]  # Main points to address
    estimated_length: str  # short, medium, long
    
    # Optional metadata
    template_used: Optional[str] = None
    context_analysis: Dict[str, Any] = field(default_factory=dict)


class DraftAgent(BaseAgent):
    """AI agent for analyzing writing style and generating draft suggestions."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the draft agent."""
        super().__init__(config or {})
        self.openai_client = OpenAI(api_key=self.config.get('openai_api_key'))
        self.writing_style: Optional[WritingStyle] = None
        self.min_emails_for_analysis = 10  # Minimum sent emails needed
        self.style_cache_expiry = timedelta(days=7)  # Refresh style analysis weekly
        self.last_style_update: Optional[datetime] = None
        
    def analyze_writing_style(self, sent_emails: List[Email]) -> WritingStyle:
        """Analyze user's writing style from sent emails."""
        if len(sent_emails) < self.min_emails_for_analysis:
            logger.warning(f"Only {len(sent_emails)} sent emails available. Need {self.min_emails_for_analysis} for accurate analysis.")
            # Still proceed with analysis but with reduced confidence
        
        if not sent_emails:
            return WritingStyle()
        
        logger.info(f"Analyzing writing style from {len(sent_emails)} sent emails")
        
        # Extract text content from emails
        email_texts = []
        for email in sent_emails:
            text = email.body_text or self._html_to_text(email.body_html or "")
            if text and len(text.strip()) > 20:  # Filter out very short emails
                email_texts.append(text)
        
        if not email_texts:
            logger.warning("No substantial email content found for style analysis")
            return WritingStyle()
        
        # Analyze various style metrics
        style = WritingStyle()
        
        # Length analysis
        word_counts = [len(text.split()) for text in email_texts]
        style.avg_length = int(statistics.mean(word_counts))
        
        # Greeting and closing patterns
        style.greeting_style = self._analyze_greetings(email_texts)
        style.closing_style = self._analyze_closings(email_texts)
        
        # Formality analysis
        style.formality_score = self._analyze_formality(email_texts)
        
        # Sentence complexity
        style.sentence_complexity = self._analyze_sentence_complexity(email_texts)
        
        # Common phrases and patterns
        style.common_phrases = self._extract_common_phrases(email_texts)
        style.tone_keywords = self._extract_tone_keywords(email_texts)
        
        # Punctuation style
        style.punctuation_style = self._analyze_punctuation(email_texts)
        
        # Temporal patterns from email metadata
        style.preferred_times = self._analyze_sending_times(sent_emails)
        
        # Use AI to enhance analysis
        try:
            style = self._enhance_with_ai_analysis(email_texts, style)
        except Exception as e:
            logger.warning(f"AI enhancement failed: {e}")
        
        self.writing_style = style
        self.last_style_update = datetime.now()
        logger.info("Writing style analysis completed")
        
        return style
    
    def generate_draft_suggestions(
        self, 
        original_email: Email, 
        context: str = "reply",
        num_suggestions: int = 3
    ) -> List[DraftSuggestion]:
        """Generate draft suggestions for responding to an email."""
        if not self.writing_style:
            logger.warning("Writing style not analyzed. Using default patterns.")
            self.writing_style = WritingStyle()
        
        logger.info(f"Generating {num_suggestions} draft suggestions for email: {original_email.subject}")
        
        # Analyze the original email context
        context_analysis = self._analyze_email_context(original_email)
        
        suggestions = []
        
        # Generate different types of drafts
        draft_types = [
            ("quick_response", "Quick, concise response"),
            ("detailed_response", "Detailed, thorough response"),
            ("formal_response", "Formal, professional response")
        ]
        
        if num_suggestions > 3:
            draft_types.extend([
                ("casual_response", "Casual, friendly response"),
                ("urgent_response", "Urgent, action-oriented response")
            ])
        
        for i, (draft_type, description) in enumerate(draft_types[:num_suggestions]):
            try:
                suggestion = self._generate_single_draft(
                    original_email, 
                    context_analysis, 
                    draft_type,
                    description
                )
                suggestions.append(suggestion)
            except Exception as e:
                logger.error(f"Failed to generate {draft_type}: {e}")
        
        # Sort by confidence and style match
        suggestions.sort(key=lambda x: (x.confidence + x.style_match) / 2, reverse=True)
        
        logger.info(f"Generated {len(suggestions)} draft suggestions")
        return suggestions
    
    def _analyze_greetings(self, email_texts: List[str]) -> str:
        """Extract most common greeting pattern."""
        greetings = []
        greeting_patterns = [
            (r'^(Hi|Hello|Hey|Dear|Good morning|Good afternoon)', 1),
            (r'^(Hi there|Hello there)', 1),
            (r'^([A-Z][a-z]+),', 1)  # Name with comma
        ]
        
        for text in email_texts:
            first_line = text.split('\n')[0].strip()
            for pattern, group_num in greeting_patterns:
                match = re.search(pattern, first_line, re.IGNORECASE)
                if match:
                    greetings.append(match.group(group_num))
                    break
        
        if greetings:
            # Return most common greeting
            return max(set(greetings), key=greetings.count)
        return "Hi"
    
    def _analyze_closings(self, email_texts: List[str]) -> str:
        """Extract most common closing pattern."""
        closings = []
        closing_patterns = [
            r'(Best|Best regards|Regards|Sincerely|Thanks|Thank you|Cheers|Talk soon|Take care)[\s,]*$',
            r'(Best wishes|Kind regards|Warm regards|Looking forward)[\s,]*$'
        ]
        
        for text in email_texts:
            last_lines = text.split('\n')[-3:]  # Check last 3 lines
            for line in last_lines:
                line = line.strip()
                for pattern in closing_patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        closings.append(match.group(1))
                        break
        
        if closings:
            return max(set(closings), key=closings.count)
        return "Best"
    
    def _analyze_formality(self, email_texts: List[str]) -> float:
        """Analyze formality level (0=casual, 1=formal)."""
        formal_indicators = [
            r'\b(please|kindly|would you|could you|sincerely|regards)\b',
            r'\b(furthermore|moreover|therefore|consequently)\b',
            r'\b(I would like to|I am writing to|I hope this email finds you)\b'
        ]
        
        casual_indicators = [
            r'\b(hey|hi there|thanks!|cool|awesome|lol|btw)\b',
            r'[!]{2,}',  # Multiple exclamation marks
            r'\b(gonna|wanna|gotta)\b'
        ]
        
        formal_score = 0
        casual_score = 0
        
        for text in email_texts:
            text_lower = text.lower()
            
            for pattern in formal_indicators:
                formal_score += len(re.findall(pattern, text_lower))
            
            for pattern in casual_indicators:
                casual_score += len(re.findall(pattern, text_lower))
        
        total_score = formal_score + casual_score
        if total_score == 0:
            return 0.5  # Neutral
        
        return formal_score / total_score
    
    def _analyze_sentence_complexity(self, email_texts: List[str]) -> float:
        """Analyze sentence complexity (0=simple, 1=complex)."""
        all_sentences = []
        
        for text in email_texts:
            sentences = re.split(r'[.!?]+', text)
            all_sentences.extend([s.strip() for s in sentences if s.strip()])
        
        if not all_sentences:
            return 0.5
        
        complexity_scores = []
        
        for sentence in all_sentences:
            words = sentence.split()
            word_count = len(words)
            
            # Factors that increase complexity
            complex_words = len([w for w in words if len(w) > 6])
            subordinate_clauses = len(re.findall(r'\b(although|because|since|while|whereas|if|unless)\b', sentence.lower()))
            commas = sentence.count(',')
            
            # Simple complexity score
            score = min(1.0, (word_count + complex_words * 2 + subordinate_clauses * 3 + commas) / 20)
            complexity_scores.append(score)
        
        return statistics.mean(complexity_scores)
    
    def _extract_common_phrases(self, email_texts: List[str]) -> List[str]:
        """Extract commonly used phrases."""
        # Common business/email phrases to look for
        phrase_patterns = [
            r'thanks for [\w\s]+',
            r'please let me know [\w\s]+',
            r'I hope [\w\s]+',
            r'looking forward to [\w\s]+',
            r'feel free to [\w\s]+',
            r'let me know if [\w\s]+',
            r'I would [\w\s]+ to',
            r'happy to [\w\s]+'
        ]
        
        found_phrases = []
        
        for text in email_texts:
            text_lower = text.lower()
            for pattern in phrase_patterns:
                matches = re.findall(pattern, text_lower)
                found_phrases.extend(matches)
        
        # Return most common phrases (appearing at least twice)
        phrase_counts = {}
        for phrase in found_phrases:
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
        
        common_phrases = [phrase for phrase, count in phrase_counts.items() if count >= 2]
        return sorted(common_phrases, key=lambda x: phrase_counts[x], reverse=True)[:10]
    
    def _extract_tone_keywords(self, email_texts: List[str]) -> List[str]:
        """Extract keywords that indicate tone."""
        # Words that indicate different tones
        tone_words = [
            'excited', 'thrilled', 'pleased', 'happy', 'great', 'excellent',
            'urgent', 'important', 'critical', 'asap', 'immediately',
            'concerned', 'worried', 'issue', 'problem', 'unfortunately',
            'appreciate', 'grateful', 'thank', 'thanks', 'wonderful'
        ]
        
        found_words = []
        
        for text in email_texts:
            words = re.findall(r'\b\w+\b', text.lower())
            for word in words:
                if word in tone_words:
                    found_words.append(word)
        
        # Return most frequent tone words
        word_counts = {}
        for word in found_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        return sorted(word_counts.keys(), key=lambda x: word_counts[x], reverse=True)[:10]
    
    def _analyze_punctuation(self, email_texts: List[str]) -> Dict[str, float]:
        """Analyze punctuation usage patterns."""
        punctuation_counts = {
            'exclamation': 0,
            'question': 0,
            'ellipsis': 0,
            'comma_density': 0,
            'dash_usage': 0
        }
        
        total_chars = 0
        
        for text in email_texts:
            total_chars += len(text)
            punctuation_counts['exclamation'] += text.count('!')
            punctuation_counts['question'] += text.count('?')
            punctuation_counts['ellipsis'] += text.count('...')
            punctuation_counts['comma_density'] += text.count(',')
            punctuation_counts['dash_usage'] += text.count('--') + text.count('—')
        
        if total_chars > 0:
            # Normalize by text length
            for key in punctuation_counts:
                punctuation_counts[key] = punctuation_counts[key] / total_chars * 1000  # Per 1000 chars
        
        return punctuation_counts
    
    def _analyze_sending_times(self, sent_emails: List[Email]) -> List[int]:
        """Analyze preferred sending times."""
        hours = [email.date.hour for email in sent_emails]
        
        # Find the most common hours (peaks)
        hour_counts = {}
        for hour in hours:
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        # Return hours that appear more frequently than average
        avg_count = len(hours) / 24 if hours else 0
        preferred = [hour for hour, count in hour_counts.items() if count > avg_count * 1.5]
        
        return sorted(preferred)
    
    def _enhance_with_ai_analysis(self, email_texts: List[str], style: WritingStyle) -> WritingStyle:
        """Use AI to enhance writing style analysis."""
        # Sample a few emails for AI analysis (to stay within token limits)
        sample_texts = email_texts[:5] if len(email_texts) > 5 else email_texts
        combined_text = "\n\n---\n\n".join(sample_texts)
        
        prompt = f"""
        Analyze the following email writing style and provide insights in JSON format:
        
        {combined_text}
        
        Please analyze and return JSON with:
        - tone_analysis: overall tone (professional, casual, friendly, etc.)
        - communication_style: direct, diplomatic, collaborative, etc.
        - personality_traits: list of traits evident in writing
        - preferred_structure: how emails are typically structured
        - decision_making_style: how decisions/requests are presented
        
        Keep response concise and focused on actionable insights.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.3
            )
            
            ai_analysis = response.choices[0].message.content
            logger.info("AI style analysis completed")
            
            # Store AI insights in style object
            style.context_analysis = {"ai_insights": ai_analysis}
            
        except Exception as e:
            logger.error(f"AI style analysis failed: {e}")
        
        return style
    
    def _analyze_email_context(self, email: Email) -> Dict[str, Any]:
        """Analyze the context of the email to inform draft generation."""
        context = {
            "sender_relationship": "unknown",
            "urgency_level": "normal",
            "topic_category": "general",
            "response_type_needed": "acknowledgment",
            "key_points_to_address": [],
            "tone_to_match": "professional"
        }
        
        # Analyze subject line
        subject_lower = email.subject.lower()
        
        # Urgency indicators
        urgent_keywords = ['urgent', 'asap', 'immediate', 'emergency', 'critical']
        if any(keyword in subject_lower for keyword in urgent_keywords):
            context["urgency_level"] = "high"
        
        # Question indicators
        if '?' in email.subject or 'question' in subject_lower:
            context["response_type_needed"] = "answer"
        
        # Meeting/scheduling indicators
        if any(word in subject_lower for word in ['meeting', 'schedule', 'calendar', 'call']):
            context["topic_category"] = "scheduling"
            context["response_type_needed"] = "scheduling"
        
        # Analyze body content if available
        body_text = email.body_text or self._html_to_text(email.body_html or "")
        if body_text:
            # Extract questions
            questions = re.findall(r'[^.!?]*\?[^.!?]*', body_text)
            if questions:
                context["key_points_to_address"] = questions[:3]  # Top 3 questions
                context["response_type_needed"] = "answer"
        
        return context
    
    def _generate_single_draft(
        self, 
        original_email: Email, 
        context_analysis: Dict[str, Any],
        draft_type: str,
        description: str
    ) -> DraftSuggestion:
        """Generate a single draft suggestion using AI."""
        # Prepare the prompt based on writing style and context
        style_prompt = self._build_style_prompt()
        context_prompt = self._build_context_prompt(original_email, context_analysis)
        
        prompt = f"""
        Generate an email {draft_type} with the following requirements:
        
        ORIGINAL EMAIL:
        From: {original_email.sender}
        Subject: {original_email.subject}
        Body: {original_email.body_text or self._html_to_text(original_email.body_html or "")}
        
        WRITING STYLE TO MATCH:
        {style_prompt}
        
        CONTEXT ANALYSIS:
        {context_prompt}
        
        DRAFT REQUIREMENTS:
        - Type: {description}
        - Match the user's established writing style
        - Address key points from the original email
        - Maintain appropriate tone and formality level
        
        Please provide:
        1. Subject line (if replying, use "Re: " prefix appropriately)
        2. Email body
        3. Brief explanation of approach taken
        
        Format as:
        SUBJECT: [subject line]
        BODY: [email body]
        APPROACH: [explanation]
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=800,
                temperature=0.4
            )
            
            content = response.choices[0].message.content
            
            # Parse the response
            subject_match = re.search(r'SUBJECT:\s*(.+)', content)
            body_match = re.search(r'BODY:\s*(.*?)\s*APPROACH:', content, re.DOTALL)
            approach_match = re.search(r'APPROACH:\s*(.+)', content, re.DOTALL)
            
            subject = subject_match.group(1).strip() if subject_match else f"Re: {original_email.subject}"
            body = body_match.group(1).strip() if body_match else "Draft generation failed"
            reasoning = approach_match.group(1).strip() if approach_match else "AI-generated response"
            
            # Calculate confidence and style match scores
            confidence = self._calculate_draft_confidence(body, context_analysis)
            style_match = self._calculate_style_match(body)
            
            # Determine suggested tone and length
            suggested_tone = self._determine_tone(body)
            estimated_length = self._estimate_length(body)
            
            return DraftSuggestion(
                subject=subject,
                body=body,
                confidence=confidence,
                reasoning=reasoning,
                style_match=style_match,
                suggested_tone=suggested_tone,
                key_points=context_analysis.get("key_points_to_address", []),
                estimated_length=estimated_length,
                template_used=draft_type,
                context_analysis=context_analysis
            )
            
        except Exception as e:
            logger.error(f"Failed to generate draft: {e}")
            # Return a fallback draft
            return DraftSuggestion(
                subject=f"Re: {original_email.subject}",
                body=f"Thank you for your email. I'll review this and get back to you soon.\n\n{self.writing_style.closing_style}",
                confidence=0.3,
                reasoning="Fallback template due to AI generation failure",
                style_match=0.5,
                suggested_tone="professional",
                key_points=[],
                estimated_length="short"
            )
    
    def _build_style_prompt(self) -> str:
        """Build a prompt describing the user's writing style."""
        if not self.writing_style:
            return "Professional, concise business communication style."
        
        style_elements = []
        
        style_elements.append(f"- Average email length: {self.writing_style.avg_length} words")
        style_elements.append(f"- Formality level: {self.writing_style.formality_score:.1f}/1.0 (0=casual, 1=formal)")
        style_elements.append(f"- Typical greeting: '{self.writing_style.greeting_style}'")
        style_elements.append(f"- Typical closing: '{self.writing_style.closing_style}'")
        
        if self.writing_style.common_phrases:
            style_elements.append(f"- Common phrases: {', '.join(self.writing_style.common_phrases[:3])}")
        
        if self.writing_style.tone_keywords:
            style_elements.append(f"- Tone indicators: {', '.join(self.writing_style.tone_keywords[:3])}")
        
        return "\n".join(style_elements)
    
    def _build_context_prompt(self, email: Email, context: Dict[str, Any]) -> str:
        """Build a prompt describing the email context."""
        context_elements = []
        
        context_elements.append(f"- Urgency level: {context.get('urgency_level', 'normal')}")
        context_elements.append(f"- Response type needed: {context.get('response_type_needed', 'acknowledgment')}")
        context_elements.append(f"- Topic category: {context.get('topic_category', 'general')}")
        
        if context.get('key_points_to_address'):
            context_elements.append(f"- Key points to address: {'; '.join(context['key_points_to_address'])}")
        
        return "\n".join(context_elements)
    
    def _calculate_draft_confidence(self, draft_body: str, context: Dict[str, Any]) -> float:
        """Calculate confidence score for a draft."""
        confidence = 0.7  # Base confidence
        
        # Check if draft addresses key points
        key_points = context.get('key_points_to_address', [])
        if key_points:
            addressed_points = sum(1 for point in key_points if any(word in draft_body.lower() for word in point.lower().split()[:3]))
            confidence += 0.2 * (addressed_points / len(key_points))
        
        # Check length appropriateness
        word_count = len(draft_body.split())
        if self.writing_style and self.writing_style.avg_length > 0:
            length_ratio = word_count / self.writing_style.avg_length
            if 0.5 <= length_ratio <= 2.0:  # Within reasonable range
                confidence += 0.1
        
        return min(1.0, confidence)
    
    def _calculate_style_match(self, draft_body: str) -> float:
        """Calculate how well the draft matches the user's style."""
        if not self.writing_style:
            return 0.5
        
        style_score = 0.5  # Base score
        
        # Check greeting/closing match
        if self.writing_style.greeting_style.lower() in draft_body.lower():
            style_score += 0.1
        if self.writing_style.closing_style.lower() in draft_body.lower():
            style_score += 0.1
        
        # Check common phrases
        for phrase in self.writing_style.common_phrases[:5]:
            if phrase.lower() in draft_body.lower():
                style_score += 0.05
        
        # Check tone keywords
        for keyword in self.writing_style.tone_keywords[:5]:
            if keyword.lower() in draft_body.lower():
                style_score += 0.02
        
        return min(1.0, style_score)
    
    def _determine_tone(self, draft_body: str) -> str:
        """Determine the tone of the draft."""
        body_lower = draft_body.lower()
        
        formal_indicators = ['please', 'kindly', 'sincerely', 'regards', 'would you']
        casual_indicators = ['hi', 'hey', 'thanks!', 'cool', 'awesome']
        urgent_indicators = ['urgent', 'asap', 'immediately', 'critical', 'important']
        friendly_indicators = ['hope', 'excited', 'happy', 'pleased', 'great']
        
        scores = {
            'formal': sum(1 for word in formal_indicators if word in body_lower),
            'casual': sum(1 for word in casual_indicators if word in body_lower),
            'urgent': sum(1 for word in urgent_indicators if word in body_lower),
            'friendly': sum(1 for word in friendly_indicators if word in body_lower)
        }
        
        return max(scores, key=scores.get) if any(scores.values()) else 'professional'
    
    def _estimate_length(self, draft_body: str) -> str:
        """Estimate the length category of the draft."""
        word_count = len(draft_body.split())
        
        if word_count < 50:
            return "short"
        elif word_count < 150:
            return "medium"
        else:
            return "long"
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (simple version)."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        # Decode common HTML entities
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        return text.strip()
    
    def get_style_summary(self) -> Dict[str, Any]:
        """Get a summary of the current writing style analysis."""
        if not self.writing_style:
            return {"status": "not_analyzed", "message": "Writing style not yet analyzed"}
        
        return {
            "status": "analyzed",
            "last_updated": self.last_style_update.isoformat() if self.last_style_update else None,
            "avg_length": self.writing_style.avg_length,
            "formality_score": self.writing_style.formality_score,
            "greeting_style": self.writing_style.greeting_style,
            "closing_style": self.writing_style.closing_style,
            "common_phrases_count": len(self.writing_style.common_phrases),
            "tone_keywords_count": len(self.writing_style.tone_keywords),
            "sentence_complexity": self.writing_style.sentence_complexity,
            "preferred_times": self.writing_style.preferred_times
        }
    
    def should_refresh_style(self) -> bool:
        """Check if writing style analysis should be refreshed."""
        if not self.last_style_update:
            return True
        
        return datetime.now() - self.last_style_update > self.style_cache_expiry
    
    async def get_status(self) -> Dict[str, Any]:
        """Get the draft agent status."""
        return {
            "agent_type": "draft_agent",
            "writing_style_analyzed": self.writing_style is not None,
            "last_style_update": self.last_style_update.isoformat() if self.last_style_update else None,
            "min_emails_for_analysis": self.min_emails_for_analysis,
            "style_cache_expiry_days": self.style_cache_expiry.days,
            "openai_configured": bool(self.config.get('openai_api_key')),
            "stats": self.stats
        }
