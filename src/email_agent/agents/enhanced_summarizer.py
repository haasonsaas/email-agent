"""Enhanced Summarizer Agent with narrative-style daily briefs."""

import logging
from datetime import datetime, date, timedelta
from typing import Any, Dict, List
import json
import re

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

from ..models import Email, DailyBrief, EmailPriority
from ..sdk.base import BaseAgent

logger = logging.getLogger(__name__)


class EnhancedSummarizerAgent(BaseAgent):
    """Enhanced summarizer agent for narrative-style daily briefs."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the enhanced summarizer agent."""
        super().__init__(config or {})
        self.openai_client = OpenAI(api_key=self.config.get('openai_api_key')) if OpenAI else None
        self.target_reading_time = 60  # seconds
        self.words_per_minute = 200  # average reading speed
        self.max_words = int((self.target_reading_time / 60) * self.words_per_minute)  # ~200 words
        
        self.stats = {
            "briefs_generated": 0,
            "avg_reading_time": 0,
            "narrative_score": 0,
            "user_engagement": 0
        }
    
    async def generate_narrative_brief(
        self, 
        emails: List[Email], 
        target_date: date,
        context: Dict[str, Any] = None
    ) -> DailyBrief:
        """Generate a narrative-style daily brief optimized for <60 second reading."""
        if not emails:
            return self._create_empty_brief(target_date)
        
        try:
            # Analyze emails for narrative elements
            narrative_analysis = await self._analyze_for_narrative(emails)
            
            # Generate narrative content
            brief_content = await self._generate_narrative_content(emails, narrative_analysis, context or {})
            
            # Create enhanced brief object
            brief = DailyBrief(
                date=datetime.combine(target_date, datetime.min.time()),
                total_emails=len(emails),
                unread_emails=sum(1 for email in emails if not email.is_read),
                categories=narrative_analysis["categories"],
                priorities=narrative_analysis["priorities"],
                headline=brief_content["headline"],
                summary=brief_content["narrative_summary"],
                action_items=brief_content["action_items"],
                deadlines=brief_content["deadlines"],
                key_threads=brief_content.get("key_threads", []),
                model_used="enhanced_narrative",
                processing_time=brief_content.get("processing_time", 0.0)
            )
            
            # Store narrative-specific metadata in summary field as JSON
            import json
            narrative_metadata = {
                "narrative_score": brief_content.get("narrative_score", 0.8),
                "estimated_reading_time": brief_content.get("reading_time", 45),
                "story_arcs": brief_content.get("story_arcs", []),
                "key_characters": brief_content.get("key_characters", []),
                "themes": brief_content.get("themes", [])
            }
            
            # Append metadata to summary with delimiter
            brief.summary = brief_content["narrative_summary"] + "\n\n---NARRATIVE_METADATA---\n" + json.dumps(narrative_metadata)
            
            self.stats["briefs_generated"] += 1
            self.stats["avg_reading_time"] = brief_content.get("reading_time", 45)
            
            logger.info(f"Generated narrative brief for {target_date}: {brief_content.get('reading_time', 45)}s read")
            return brief
            
        except Exception as e:
            logger.error(f"Failed to generate narrative brief: {str(e)}")
            return self._create_error_brief(target_date, str(e))
    
    async def _analyze_for_narrative(self, emails: List[Email]) -> Dict[str, Any]:
        """Analyze emails to identify narrative elements."""
        analysis = {
            "total_emails": len(emails),
            "unread_emails": sum(1 for email in emails if not email.is_read),
            "categories": {},
            "priorities": {},
            "story_elements": {},
            "key_people": {},
            "themes": [],
            "temporal_flow": [],
            "emotional_tone": {},
            "urgency_clusters": []
        }
        
        # Basic categorization
        for email in emails:
            cat = email.category.value
            analysis["categories"][cat] = analysis["categories"].get(cat, 0) + 1
            
            pri = email.priority.value
            analysis["priorities"][pri] = analysis["priorities"].get(pri, 0) + 1
        
        # Identify key people (frequent senders/recipients)
        for email in emails:
            sender = email.sender.email
            analysis["key_people"][sender] = analysis["key_people"].get(sender, 0) + 1
        
        # Find story arcs (email threads and conversations)
        story_arcs = await self._identify_story_arcs(emails)
        analysis["story_elements"]["arcs"] = story_arcs
        
        # Analyze temporal flow
        analysis["temporal_flow"] = self._analyze_temporal_flow(emails)
        
        # Detect themes and topics
        if self.openai_client:
            themes = await self._extract_themes_with_ai(emails)
            analysis["themes"] = themes
        else:
            analysis["themes"] = self._extract_themes_rule_based(emails)
        
        # Analyze emotional tone
        analysis["emotional_tone"] = await self._analyze_emotional_tone(emails)
        
        # Identify urgency clusters
        analysis["urgency_clusters"] = self._identify_urgency_clusters(emails)
        
        return analysis
    
    async def _generate_narrative_content(
        self, 
        emails: List[Email], 
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate narrative-style content for the brief."""
        if self.openai_client:
            return await self._generate_narrative_with_ai(emails, analysis, context)
        else:
            return self._generate_narrative_rule_based(emails, analysis, context)
    
    async def _generate_narrative_with_ai(
        self, 
        emails: List[Email], 
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate narrative content using AI."""
        try:
            # Prepare narrative prompt
            prompt = self._create_narrative_prompt(emails, analysis, context)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": """You are an expert storyteller and executive assistant who creates engaging, narrative-style email summaries. 
                        Your goal is to transform email data into a compelling 60-second read that feels like a story rather than a report.
                        Focus on:
                        - Creating a narrative flow with beginning, middle, and end
                        - Identifying key characters (people) and their roles
                        - Highlighting conflicts, resolutions, and developments
                        - Using engaging language while remaining professional
                        - Maintaining accuracy while adding narrative structure"""
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.6  # Slightly higher for more creative narrative
            )
            
            content = response.choices[0].message.content
            parsed_content = self._parse_narrative_response(content)
            
            # Estimate reading time
            word_count = len(parsed_content["narrative_summary"].split())
            reading_time = max(30, min(90, (word_count / self.words_per_minute) * 60))
            parsed_content["reading_time"] = int(reading_time)
            
            return parsed_content
            
        except Exception as e:
            logger.error(f"AI narrative generation failed: {str(e)}")
            return self._generate_narrative_rule_based(emails, analysis, context)
    
    def _create_narrative_prompt(
        self, 
        emails: List[Email], 
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """Create a narrative-focused prompt for AI generation."""
        
        # Get top emails by priority/importance
        top_emails = sorted(emails, key=lambda x: (
            x.priority.value == 'urgent',
            x.priority.value == 'high',
            not x.is_read,
            x.date
        ), reverse=True)[:15]
        
        # Format key people
        key_people = sorted(analysis["key_people"].items(), key=lambda x: x[1], reverse=True)[:5]
        people_context = ", ".join([f"{email} ({count} emails)" for email, count in key_people])
        
        # Format themes
        themes_context = ", ".join(analysis["themes"][:5])
        
        # Format story arcs
        story_arcs = analysis["story_elements"].get("arcs", [])
        arcs_context = "; ".join([f"{arc['topic']} ({arc['email_count']} emails)" for arc in story_arcs[:3]])
        
        email_summaries = []
        for email in top_emails:
            body_preview = (email.body_text or "")[:150]
            email_summaries.append({
                "from": email.sender.email,
                "subject": email.subject,
                "priority": email.priority.value,
                "read": email.is_read,
                "time": email.date.strftime("%H:%M"),
                "preview": body_preview
            })
        
        return f"""
Create a narrative-style daily email brief that reads like an engaging story in under 60 seconds.

CONTEXT:
- Date: {datetime.now().strftime('%A, %B %d')}
- Total emails: {analysis['total_emails']}
- Key people: {people_context}
- Main themes: {themes_context}
- Story arcs: {arcs_context}
- Emotional tone: {analysis.get('emotional_tone', {}).get('dominant', 'neutral')}

TOP EMAILS:
{json.dumps(email_summaries, indent=2)}

Create a brief with this structure:

HEADLINE: [Engaging one-liner that captures the day's email story]

NARRATIVE: [A 150-200 word story that weaves together the day's emails into a compelling narrative. Think of it as "Today's inbox tells the story of..." Use narrative techniques like:
- Opening hook
- Character development (key email senders)
- Plot progression (how events unfolded)
- Conflict and resolution
- Future implications
Make it engaging but professional.]

ACTION_ITEMS: [3-5 specific actions in story context]

DEADLINES: [Time-sensitive items with narrative context]

CHARACTERS: [Key people and their roles in today's story]

THEMES: [2-3 main themes that emerged]

Focus on storytelling while maintaining accuracy. Make the reader feel engaged rather than overwhelmed.
"""
    
    def _parse_narrative_response(self, content: str) -> Dict[str, Any]:
        """Parse AI narrative response into structured data."""
        result = {
            "headline": "",
            "narrative_summary": "",
            "action_items": [],
            "deadlines": [],
            "key_characters": [],
            "themes": [],
            "narrative_score": 0.8,
            "story_arcs": []
        }
        
        try:
            lines = content.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith("HEADLINE:"):
                    result["headline"] = line.replace("HEADLINE:", "").strip()
                elif line.startswith("NARRATIVE:"):
                    current_section = "narrative"
                    result["narrative_summary"] = line.replace("NARRATIVE:", "").strip()
                elif line.startswith("ACTION_ITEMS:"):
                    current_section = "action_items"
                elif line.startswith("DEADLINES:"):
                    current_section = "deadlines"
                elif line.startswith("CHARACTERS:"):
                    current_section = "characters"
                elif line.startswith("THEMES:"):
                    current_section = "themes"
                elif line.startswith("- ") and current_section:
                    item = line[2:].strip()
                    if current_section == "action_items":
                        result["action_items"].append(item)
                    elif current_section == "deadlines":
                        result["deadlines"].append(item)
                    elif current_section == "characters":
                        result["key_characters"].append(item)
                    elif current_section == "themes":
                        result["themes"].append(item)
                elif current_section == "narrative" and not line.startswith(("ACTION", "DEADLINE", "CHARACTER", "THEME", "-")):
                    result["narrative_summary"] += " " + line
            
            # Clean up narrative summary
            result["narrative_summary"] = result["narrative_summary"].strip()
            
            # Calculate narrative score based on storytelling elements
            result["narrative_score"] = self._calculate_narrative_score(result)
            
        except Exception as e:
            logger.error(f"Failed to parse narrative response: {e}")
            # Fallback to basic parsing
            result["narrative_summary"] = content[:400] + "..."
        
        return result
    
    def _calculate_narrative_score(self, content: Dict[str, Any]) -> float:
        """Calculate how narrative/story-like the content is."""
        score = 0.5  # Base score
        
        narrative = content.get("narrative_summary", "")
        
        # Check for narrative elements
        narrative_words = [
            "story", "journey", "unfolded", "emerged", "developed", "revealed",
            "meanwhile", "however", "throughout", "ultimately", "began", "concluded"
        ]
        
        story_elements = sum(1 for word in narrative_words if word in narrative.lower())
        score += min(0.3, story_elements * 0.05)
        
        # Check for character development
        if content.get("key_characters"):
            score += 0.1
        
        # Check for theme identification
        if content.get("themes"):
            score += 0.1
        
        # Check for engaging headline
        headline = content.get("headline", "")
        if any(word in headline.lower() for word in ["story", "tale", "saga", "journey", "unfolds"]):
            score += 0.1
        
        return min(1.0, score)
    
    def _generate_narrative_rule_based(
        self, 
        emails: List[Email], 
        analysis: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate narrative content using rule-based approach."""
        
        # Create a basic narrative structure
        headline = self._create_rule_based_headline(emails, analysis)
        narrative = self._create_rule_based_narrative(emails, analysis)
        action_items = self._extract_action_items(emails)
        deadlines = self._extract_deadlines(emails)
        
        return {
            "headline": headline,
            "narrative_summary": narrative,
            "action_items": action_items,
            "deadlines": deadlines,
            "key_characters": list(analysis["key_people"].keys())[:5],
            "themes": analysis["themes"][:3],
            "narrative_score": 0.6,
            "reading_time": 45,
            "story_arcs": analysis["story_elements"].get("arcs", [])
        }
    
    def _create_rule_based_headline(self, emails: List[Email], analysis: Dict[str, Any]) -> str:
        """Create an engaging headline using rules."""
        total = analysis["total_emails"]
        unread = analysis["unread_emails"]
        urgent = analysis["priorities"].get("urgent", 0)
        
        if urgent > 0:
            return f"Today's inbox brings {urgent} urgent matters among {total} messages"
        elif unread > total * 0.7:
            return f"A busy day unfolds with {unread} new messages requiring attention"
        else:
            return f"Today's email story: {total} messages paint the day's picture"
    
    def _create_rule_based_narrative(self, emails: List[Email], analysis: Dict[str, Any]) -> str:
        """Create a narrative summary using rule-based approach."""
        total = analysis["total_emails"]
        key_people = list(analysis["key_people"].keys())[:3]
        themes = analysis["themes"][:2]
        
        # Start with temporal context
        narrative = f"Today's inbox tells a story of {total} communications "
        
        # Add character context
        if key_people:
            people_names = [email.split('@')[0].replace('.', ' ').title() for email in key_people[:2]]
            narrative += f"featuring conversations with {', '.join(people_names)} and others. "
        
        # Add thematic context
        if themes:
            narrative += f"The day's themes centered around {' and '.join(themes).lower()}. "
        
        # Add urgency/priority context
        urgent_count = analysis["priorities"].get("urgent", 0)
        high_count = analysis["priorities"].get("high", 0)
        
        if urgent_count > 0:
            narrative += f"{urgent_count} urgent matter{'s' if urgent_count > 1 else ''} demanded immediate attention, "
        if high_count > 0:
            narrative += f"while {high_count} high-priority item{'s' if high_count > 1 else ''} shaped the day's agenda. "
        
        # Add temporal flow
        morning_emails = [e for e in emails if e.date.hour < 12]
        afternoon_emails = [e for e in emails if 12 <= e.date.hour < 17]
        evening_emails = [e for e in emails if e.date.hour >= 17]
        
        if morning_emails and afternoon_emails:
            narrative += f"The conversation began with {len(morning_emails)} morning messages and continued through {len(afternoon_emails)} afternoon developments"
            if evening_emails:
                narrative += f", extending into {len(evening_emails)} evening communications."
            else:
                narrative += "."
        
        # Add conclusion
        unread = analysis["unread_emails"]
        if unread > 0:
            narrative += f" {unread} message{'s' if unread > 1 else ''} await{'s' if unread == 1 else ''} your response to complete today's email story."
        
        return narrative.strip()
    
    async def _identify_story_arcs(self, emails: List[Email]) -> List[Dict[str, Any]]:
        """Identify story arcs from email threads and conversations."""
        story_arcs = []
        
        # Group by thread_id or subject similarity
        thread_groups = {}
        for email in emails:
            if email.thread_id:
                key = f"thread_{email.thread_id}"
            else:
                # Group by similar subjects (remove Re:, Fwd:, etc.)
                clean_subject = re.sub(r'^(Re|Fwd|RE|FWD):\s*', '', email.subject, flags=re.IGNORECASE)
                key = f"subject_{clean_subject.lower()}"
            
            if key not in thread_groups:
                thread_groups[key] = []
            thread_groups[key].append(email)
        
        # Create story arcs for groups with multiple emails
        for key, group_emails in thread_groups.items():
            if len(group_emails) > 1:
                # Sort by date
                group_emails.sort(key=lambda x: x.date)
                
                arc = {
                    "topic": group_emails[0].subject,
                    "email_count": len(group_emails),
                    "timespan": (group_emails[-1].date - group_emails[0].date).days,
                    "participants": list(set([e.sender.email for e in group_emails])),
                    "status": "ongoing" if group_emails[-1].date > datetime.now() - timedelta(days=1) else "resolved"
                }
                story_arcs.append(arc)
        
        # Sort by email count (most active threads first)
        story_arcs.sort(key=lambda x: x["email_count"], reverse=True)
        
        return story_arcs[:5]  # Return top 5 story arcs
    
    def _analyze_temporal_flow(self, emails: List[Email]) -> Dict[str, Any]:
        """Analyze the temporal flow of emails throughout the day."""
        hourly_distribution = {}
        for email in emails:
            hour = email.date.hour
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1
        
        # Identify peak hours
        if hourly_distribution:
            peak_hour = max(hourly_distribution, key=hourly_distribution.get)
            peak_count = hourly_distribution[peak_hour]
        else:
            peak_hour = 9
            peak_count = 0
        
        return {
            "hourly_distribution": hourly_distribution,
            "peak_hour": peak_hour,
            "peak_count": peak_count,
            "morning_activity": sum(hourly_distribution.get(h, 0) for h in range(6, 12)),
            "afternoon_activity": sum(hourly_distribution.get(h, 0) for h in range(12, 18)),
            "evening_activity": sum(hourly_distribution.get(h, 0) for h in range(18, 24))
        }
    
    async def _extract_themes_with_ai(self, emails: List[Email]) -> List[str]:
        """Extract themes using AI analysis."""
        if not self.openai_client or not emails:
            return []
        
        try:
            # Sample email subjects and content for theme extraction
            sample_content = []
            for email in emails[:20]:  # Limit for token management
                content = f"Subject: {email.subject}"
                if email.body_text:
                    content += f"\nContent: {email.body_text[:200]}"
                sample_content.append(content)
            
            prompt = f"""
            Analyze the following emails and identify 3-5 main themes or topics.
            Return only a comma-separated list of themes (e.g., "project updates, meeting scheduling, budget discussions").
            
            Emails:
            {chr(10).join(sample_content[:10])}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.3
            )
            
            themes_text = response.choices[0].message.content.strip()
            themes = [theme.strip() for theme in themes_text.split(',')]
            return themes[:5]
            
        except Exception as e:
            logger.error(f"AI theme extraction failed: {e}")
            return self._extract_themes_rule_based(emails)
    
    def _extract_themes_rule_based(self, emails: List[Email]) -> List[str]:
        """Extract themes using rule-based keyword analysis."""
        theme_keywords = {
            "project management": ["project", "milestone", "deadline", "deliverable", "status", "progress"],
            "meetings": ["meeting", "call", "conference", "agenda", "schedule", "calendar"],
            "business operations": ["budget", "finance", "revenue", "cost", "proposal", "contract"],
            "team collaboration": ["team", "collaboration", "review", "feedback", "discussion", "decision"],
            "customer relations": ["client", "customer", "support", "issue", "requirement", "satisfaction"],
            "technical matters": ["development", "bug", "feature", "deployment", "system", "technical"],
            "administrative": ["policy", "procedure", "compliance", "documentation", "approval", "process"]
        }
        
        theme_scores = {}
        for email in emails:
            content = f"{email.subject} {email.body_text or ''}".lower()
            
            for theme, keywords in theme_keywords.items():
                score = sum(1 for keyword in keywords if keyword in content)
                theme_scores[theme] = theme_scores.get(theme, 0) + score
        
        # Return top themes
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)
        return [theme for theme, score in sorted_themes[:5] if score > 0]
    
    async def _analyze_emotional_tone(self, emails: List[Email]) -> Dict[str, Any]:
        """Analyze the emotional tone of emails."""
        if self.openai_client and emails:
            return await self._analyze_tone_with_ai(emails)
        else:
            return self._analyze_tone_rule_based(emails)
    
    async def _analyze_tone_with_ai(self, emails: List[Email]) -> Dict[str, Any]:
        """Analyze emotional tone using AI."""
        try:
            # Sample a few emails for tone analysis
            sample_emails = emails[:5]
            content_samples = []
            
            for email in sample_emails:
                if email.body_text:
                    content_samples.append(f"Subject: {email.subject}\nContent: {email.body_text[:200]}")
            
            if not content_samples:
                return {"dominant": "neutral", "distribution": {"neutral": 1.0}}
            
            prompt = f"""
            Analyze the emotional tone of these emails and respond with just one word from: 
            positive, negative, neutral, urgent, frustrated, excited, professional, casual
            
            Emails:
            {chr(10).join(content_samples)}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )
            
            tone = response.choices[0].message.content.strip().lower()
            return {"dominant": tone, "distribution": {tone: 1.0}}
            
        except Exception as e:
            logger.error(f"AI tone analysis failed: {e}")
            return self._analyze_tone_rule_based(emails)
    
    def _analyze_tone_rule_based(self, emails: List[Email]) -> Dict[str, Any]:
        """Analyze emotional tone using rule-based approach."""
        tone_indicators = {
            "urgent": ["urgent", "asap", "immediate", "critical", "emergency"],
            "positive": ["great", "excellent", "awesome", "fantastic", "pleased", "happy", "excited"],
            "negative": ["problem", "issue", "concern", "worried", "disappointed", "frustrated"],
            "professional": ["please", "thank you", "regards", "sincerely", "appreciate"],
            "casual": ["hey", "hi there", "cool", "awesome", "thanks!", "lol"]
        }
        
        tone_scores = {}
        total_content = ""
        
        for email in emails:
            content = f"{email.subject} {email.body_text or ''}".lower()
            total_content += content + " "
        
        for tone, indicators in tone_indicators.items():
            score = sum(total_content.count(indicator) for indicator in indicators)
            if score > 0:
                tone_scores[tone] = score
        
        if not tone_scores:
            return {"dominant": "neutral", "distribution": {"neutral": 1.0}}
        
        total_score = sum(tone_scores.values())
        distribution = {tone: score/total_score for tone, score in tone_scores.items()}
        dominant = max(tone_scores, key=tone_scores.get)
        
        return {"dominant": dominant, "distribution": distribution}
    
    def _identify_urgency_clusters(self, emails: List[Email]) -> List[Dict[str, Any]]:
        """Identify clusters of urgent or time-sensitive emails."""
        urgent_emails = [e for e in emails if e.priority in [EmailPriority.URGENT, EmailPriority.HIGH]]
        
        if not urgent_emails:
            return []
        
        # Group by time periods (within 2 hours of each other)
        clusters = []
        sorted_urgent = sorted(urgent_emails, key=lambda x: x.date)
        
        current_cluster = [sorted_urgent[0]]
        
        for email in sorted_urgent[1:]:
            time_diff = (email.date - current_cluster[-1].date).total_seconds() / 3600  # hours
            
            if time_diff <= 2:  # Within 2 hours
                current_cluster.append(email)
            else:
                if len(current_cluster) >= 2:  # Only clusters with 2+ emails
                    clusters.append({
                        "start_time": current_cluster[0].date,
                        "end_time": current_cluster[-1].date,
                        "email_count": len(current_cluster),
                        "topics": [e.subject for e in current_cluster]
                    })
                current_cluster = [email]
        
        # Don't forget the last cluster
        if len(current_cluster) >= 2:
            clusters.append({
                "start_time": current_cluster[0].date,
                "end_time": current_cluster[-1].date,
                "email_count": len(current_cluster),
                "topics": [e.subject for e in current_cluster]
            })
        
        return clusters
    
    def _extract_action_items(self, emails: List[Email]) -> List[str]:
        """Extract action items from emails."""
        action_items = []
        action_keywords = [
            "please", "need to", "action required", "follow up", "respond", 
            "review", "approve", "confirm", "schedule", "complete"
        ]
        
        for email in emails:
            if not email.is_read or email.priority in [EmailPriority.HIGH, EmailPriority.URGENT]:
                content = f"{email.subject} {email.body_text or ''}".lower()
                
                if any(keyword in content for keyword in action_keywords):
                    action_item = f"Respond to {email.sender.email}: {email.subject}"
                    action_items.append(action_item)
        
        return action_items[:10]  # Limit to top 10
    
    def _extract_deadlines(self, emails: List[Email]) -> List[str]:
        """Extract deadline information from emails."""
        deadlines = []
        deadline_patterns = [
            r"by (monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
            r"due (on )?([\w\s,]+)",
            r"deadline (is )?([\w\s,]+)",
            r"before ([\w\s,]+)",
            r"(january|february|march|april|may|june|july|august|september|october|november|december) \d{1,2}"
        ]
        
        for email in emails:
            content = f"{email.subject} {email.body_text or ''}".lower()
            
            for pattern in deadline_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = ' '.join(match).strip()
                    if match:
                        deadline = f"{email.subject}: {match}"
                        deadlines.append(deadline)
        
        return deadlines[:5]  # Limit to top 5
    
    def _create_empty_brief(self, target_date: date) -> DailyBrief:
        """Create an empty brief for days with no emails."""
        return DailyBrief(
            date=datetime.combine(target_date, datetime.min.time()),
            total_emails=0,
            unread_emails=0,
            categories={},
            priorities={},
            headline="A quiet day in your inbox",
            summary="No emails received today - a rare moment of peace in the digital world.",
            action_items=[],
            deadlines=[],
            key_threads=[],
            model_used="enhanced_narrative"
        )
    
    def _create_error_brief(self, target_date: date, error: str) -> DailyBrief:
        """Create an error brief when generation fails."""
        return DailyBrief(
            date=datetime.combine(target_date, datetime.min.time()),
            total_emails=0,
            unread_emails=0,
            categories={},
            priorities={},
            headline="Brief generation encountered an issue",
            summary=f"Unable to generate today's narrative brief due to: {error}",
            action_items=["Check system logs", "Retry brief generation"],
            deadlines=[],
            key_threads=[],
            model_used="error_fallback"
        )
    
    async def get_status(self) -> Dict[str, Any]:
        """Get the enhanced summarizer agent status."""
        return {
            "agent_type": "enhanced_summarizer",
            "target_reading_time": self.target_reading_time,
            "max_words": self.max_words,
            "openai_configured": self.openai_client is not None,
            "stats": self.stats
        }
