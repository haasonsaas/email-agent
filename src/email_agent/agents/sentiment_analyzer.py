"""Sentiment analysis agent for emails."""

import logging
from typing import Dict, Any, List

from ..config import settings
from ..models import Email
from ..sdk.base import BaseAgent

logger = logging.getLogger(__name__)


class SentimentAnalyzer(BaseAgent):
    """Analyzes email sentiment and emotional context."""
    
    def __init__(self):
        super().__init__()
        self.openai_client = None
        self.stats = {
            "emails_analyzed": 0,
            "positive_sentiment": 0,
            "negative_sentiment": 0,
            "neutral_sentiment": 0,
            "urgent_escalations": 0
        }
        self._initialize_llm()
    
    def _initialize_llm(self) -> None:
        """Initialize OpenAI client for sentiment analysis."""
        try:
            if settings.openai_api_key and settings.openai_api_key != "your_openai_api_key_here":
                import openai
                self.openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
                logger.info("Sentiment analyzer LLM initialized")
            else:
                logger.warning("OpenAI API key not configured for sentiment analysis")
        except Exception as e:
            logger.error(f"Failed to initialize sentiment analyzer LLM: {str(e)}")
    
    async def analyze_sentiment(self, email: Email) -> Dict[str, Any]:
        """Analyze the sentiment and emotional context of an email."""
        try:
            if not email.body_text:
                return self._get_neutral_sentiment()
            
            if self.openai_client:
                return await self._analyze_with_llm(email)
            else:
                return await self._analyze_with_rules(email)
                
        except Exception as e:
            logger.error(f"Failed to analyze sentiment for email {email.id}: {str(e)}")
            return self._get_neutral_sentiment()
    
    async def _analyze_with_llm(self, email: Email) -> Dict[str, Any]:
        """Analyze sentiment using OpenAI LLM."""
        try:
            prompt = f"""
Analyze the sentiment and emotional context of this email:

Subject: {email.subject}
From: {email.sender.email}
Body: {email.body_text[:1500]}

Provide analysis in this format:
SENTIMENT: [positive/negative/neutral]
CONFIDENCE: [0.0-1.0]
EMOTION: [happy/angry/frustrated/excited/worried/neutral/etc]
URGENCY: [low/medium/high]
TONE: [professional/casual/formal/aggressive/friendly]
ESCALATION_RISK: [low/medium/high]
KEY_PHRASES: [list key emotional phrases]
SUMMARY: [brief explanation of the sentiment analysis]
"""
            
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at analyzing email sentiment and emotional context. Be precise and professional."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            self.stats["emails_analyzed"] += 1
            
            sentiment_data = self._parse_sentiment_response(content)
            
            # Update sentiment stats
            sentiment = sentiment_data.get("sentiment", "neutral")
            if sentiment == "positive":
                self.stats["positive_sentiment"] += 1
            elif sentiment == "negative":
                self.stats["negative_sentiment"] += 1
            else:
                self.stats["neutral_sentiment"] += 1
            
            # Track urgent escalations
            if sentiment_data.get("escalation_risk") == "high":
                self.stats["urgent_escalations"] += 1
            
            return sentiment_data
            
        except Exception as e:
            logger.error(f"LLM sentiment analysis failed: {str(e)}")
            return await self._analyze_with_rules(email)
    
    async def _analyze_with_rules(self, email: Email) -> Dict[str, Any]:
        """Analyze sentiment using rule-based approach."""
        try:
            text = f"{email.subject} {email.body_text or ''}".lower()
            
            # Positive indicators
            positive_words = [
                "thank", "thanks", "appreciate", "great", "excellent", "wonderful",
                "pleased", "happy", "love", "perfect", "amazing", "fantastic",
                "congratulations", "well done", "success", "achievement"
            ]
            
            # Negative indicators
            negative_words = [
                "urgent", "emergency", "problem", "issue", "error", "failed", "failure",
                "disappointed", "frustrated", "angry", "complaint", "terrible", "awful",
                "wrong", "mistake", "critical", "serious", "immediate", "asap"
            ]
            
            # Urgency indicators
            urgency_words = [
                "urgent", "asap", "immediately", "emergency", "critical", "deadline",
                "rush", "priority", "escalate", "now", "today", "tonight"
            ]
            
            # Professional tone indicators
            professional_words = [
                "please", "kindly", "regarding", "pursuant", "furthermore", "however",
                "sincerely", "respectfully", "cordially", "best regards"
            ]
            
            positive_count = sum(1 for word in positive_words if word in text)
            negative_count = sum(1 for word in negative_words if word in text)
            urgency_count = sum(1 for word in urgency_words if word in text)
            professional_count = sum(1 for word in professional_words if word in text)
            
            # Determine sentiment
            if positive_count > negative_count:
                sentiment = "positive"
                confidence = min(0.9, 0.5 + (positive_count * 0.1))
                emotion = "happy" if positive_count > 2 else "pleased"
            elif negative_count > positive_count:
                sentiment = "negative"
                confidence = min(0.9, 0.5 + (negative_count * 0.1))
                emotion = "frustrated" if urgency_count > 0 else "disappointed"
            else:
                sentiment = "neutral"
                confidence = 0.5
                emotion = "neutral"
            
            # Determine urgency
            if urgency_count >= 3:
                urgency = "high"
            elif urgency_count >= 1:
                urgency = "medium"
            else:
                urgency = "low"
            
            # Determine tone
            if professional_count >= 2:
                tone = "professional"
            elif "!" in text or text.isupper():
                tone = "aggressive" if sentiment == "negative" else "excited"
            else:
                tone = "casual"
            
            # Escalation risk
            escalation_risk = "high" if (negative_count >= 2 and urgency_count >= 1) else "low"
            
            self.stats["emails_analyzed"] += 1
            if sentiment == "positive":
                self.stats["positive_sentiment"] += 1
            elif sentiment == "negative":
                self.stats["negative_sentiment"] += 1
            else:
                self.stats["neutral_sentiment"] += 1
            
            if escalation_risk == "high":
                self.stats["urgent_escalations"] += 1
            
            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "emotion": emotion,
                "urgency": urgency,
                "tone": tone,
                "escalation_risk": escalation_risk,
                "key_phrases": self._extract_key_phrases(text, negative_words, positive_words, urgency_words),
                "summary": f"Rule-based analysis: {sentiment} sentiment with {urgency} urgency",
                "analysis_method": "rules"
            }
            
        except Exception as e:
            logger.error(f"Rule-based sentiment analysis failed: {str(e)}")
            return self._get_neutral_sentiment()
    
    def _parse_sentiment_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM sentiment analysis response."""
        result = {
            "sentiment": "neutral",
            "confidence": 0.5,
            "emotion": "neutral",
            "urgency": "low",
            "tone": "professional",
            "escalation_risk": "low",
            "key_phrases": [],
            "summary": "",
            "analysis_method": "llm"
        }
        
        try:
            lines = content.split('\\n')
            for line in lines:
                line = line.strip()
                if line.startswith('SENTIMENT:'):
                    sentiment = line.replace('SENTIMENT:', '').strip().lower()
                    if sentiment in ['positive', 'negative', 'neutral']:
                        result["sentiment"] = sentiment
                elif line.startswith('CONFIDENCE:'):
                    try:
                        confidence = float(line.replace('CONFIDENCE:', '').strip())
                        result["confidence"] = max(0.0, min(1.0, confidence))
                    except ValueError:
                        pass
                elif line.startswith('EMOTION:'):
                    result["emotion"] = line.replace('EMOTION:', '').strip().lower()
                elif line.startswith('URGENCY:'):
                    urgency = line.replace('URGENCY:', '').strip().lower()
                    if urgency in ['low', 'medium', 'high']:
                        result["urgency"] = urgency
                elif line.startswith('TONE:'):
                    result["tone"] = line.replace('TONE:', '').strip().lower()
                elif line.startswith('ESCALATION_RISK:'):
                    risk = line.replace('ESCALATION_RISK:', '').strip().lower()
                    if risk in ['low', 'medium', 'high']:
                        result["escalation_risk"] = risk
                elif line.startswith('KEY_PHRASES:'):
                    phrases_text = line.replace('KEY_PHRASES:', '').strip()
                    result["key_phrases"] = [p.strip() for p in phrases_text.split(',') if p.strip()]
                elif line.startswith('SUMMARY:'):
                    result["summary"] = line.replace('SUMMARY:', '').strip()
        
        except Exception as e:
            logger.error(f"Failed to parse sentiment response: {str(e)}")
        
        return result
    
    def _extract_key_phrases(self, text: str, negative_words: List[str], 
                           positive_words: List[str], urgency_words: List[str]) -> List[str]:
        """Extract key emotional phrases from text."""
        phrases = []
        
        # Find emotional words in context
        words = text.split()
        for i, word in enumerate(words):
            if word in negative_words or word in positive_words or word in urgency_words:
                # Get surrounding context
                start = max(0, i - 2)
                end = min(len(words), i + 3)
                phrase = ' '.join(words[start:end])
                phrases.append(phrase)
        
        return phrases[:5]  # Limit to top 5 phrases
    
    def _get_neutral_sentiment(self) -> Dict[str, Any]:
        """Return neutral sentiment analysis."""
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "emotion": "neutral",
            "urgency": "low",
            "tone": "professional",
            "escalation_risk": "low",
            "key_phrases": [],
            "summary": "Unable to analyze sentiment",
            "analysis_method": "fallback"
        }
    
    async def analyze_email_batch(self, emails: List[Email]) -> Dict[str, Dict[str, Any]]:
        """Analyze sentiment for a batch of emails."""
        results = {}
        
        for email in emails:
            try:
                sentiment_data = await self.analyze_sentiment(email)
                results[email.id] = sentiment_data
            except Exception as e:
                logger.error(f"Failed to analyze email {email.id}: {str(e)}")
                results[email.id] = self._get_neutral_sentiment()
        
        return results
    
    async def get_sentiment_insights(self, emails: List[Email]) -> Dict[str, Any]:
        """Generate overall sentiment insights from email batch."""
        if not emails:
            return {}
        
        # Analyze all emails
        sentiment_results = await self.analyze_email_batch(emails)
        
        # Calculate aggregated insights
        sentiments = [result["sentiment"] for result in sentiment_results.values()]
        urgencies = [result["urgency"] for result in sentiment_results.values()]
        escalation_risks = [result["escalation_risk"] for result in sentiment_results.values()]
        
        insights = {
            "total_analyzed": len(emails),
            "sentiment_distribution": {
                "positive": sentiments.count("positive"),
                "negative": sentiments.count("negative"),
                "neutral": sentiments.count("neutral")
            },
            "urgency_distribution": {
                "high": urgencies.count("high"),
                "medium": urgencies.count("medium"),
                "low": urgencies.count("low")
            },
            "escalation_risks": {
                "high": escalation_risks.count("high"),
                "medium": escalation_risks.count("medium"),
                "low": escalation_risks.count("low")
            },
            "recommendations": self._generate_recommendations(sentiment_results, emails)
        }
        
        return insights
    
    def _generate_recommendations(self, sentiment_results: Dict[str, Dict[str, Any]], 
                                emails: List[Email]) -> List[str]:
        """Generate actionable recommendations based on sentiment analysis."""
        recommendations = []
        
        # High escalation risk emails
        high_risk_emails = [
            email for email in emails 
            if sentiment_results.get(email.id, {}).get("escalation_risk") == "high"
        ]
        
        if high_risk_emails:
            recommendations.append(f"🚨 {len(high_risk_emails)} emails have high escalation risk - review immediately")
        
        # Negative sentiment emails
        negative_emails = [
            email for email in emails
            if sentiment_results.get(email.id, {}).get("sentiment") == "negative"
        ]
        
        if len(negative_emails) > len(emails) * 0.3:  # More than 30% negative
            recommendations.append("⚠️ High volume of negative sentiment emails - consider proactive communication")
        
        # Urgent emails
        urgent_emails = [
            email for email in emails
            if sentiment_results.get(email.id, {}).get("urgency") == "high"
        ]
        
        if urgent_emails:
            recommendations.append(f"⏰ {len(urgent_emails)} emails marked as high urgency")
        
        # Positive sentiment
        positive_emails = [
            email for email in emails
            if sentiment_results.get(email.id, {}).get("sentiment") == "positive"
        ]
        
        if len(positive_emails) > len(emails) * 0.5:  # More than 50% positive
            recommendations.append("✅ Good overall sentiment - maintain current engagement level")
        
        return recommendations
    
    async def get_status(self) -> Dict[str, Any]:
        """Get sentiment analyzer status."""
        return {
            "llm_available": self.openai_client is not None,
            "stats": self.stats.copy(),
            "analysis_methods": ["llm", "rules", "fallback"]
        }
    
    async def shutdown(self) -> None:
        """Shutdown the sentiment analyzer."""
        try:
            if self.openai_client:
                await self.openai_client.close()
            logger.info("Sentiment analyzer shutdown completed")
        except Exception as e:
            logger.error(f"Error during sentiment analyzer shutdown: {str(e)}")
