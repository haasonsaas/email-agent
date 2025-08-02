"""Summarizer agent for generating daily briefs and email summaries."""

import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional

try:
    import openai
    from openai import AsyncOpenAI
except ImportError:
    openai = None
    AsyncOpenAI = None

from ..config import settings
from ..models import Email, DailyBrief, EmailCategory, EmailPriority

logger = logging.getLogger(__name__)


class SummarizerAgent:
    """Agent responsible for generating summaries and daily briefs."""
    
    def __init__(self):
        self.openai_client: Optional[AsyncOpenAI] = None
        self.stats: Dict[str, Any] = {
            "briefs_generated": 0,
            "emails_summarized": 0,
            "total_tokens_used": 0,
            "last_generation": None
        }
        self._initialize_llm()
    
    def _initialize_llm(self) -> None:
        """Initialize LLM client."""
        try:
            if AsyncOpenAI and settings.openai_api_key:
                self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
                logger.info("OpenAI client initialized")
            else:
                logger.warning("No OpenAI API key provided or OpenAI not installed - summarization will be limited")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {str(e)}")
    
    async def generate_brief(self, emails: List[Email], target_date: date) -> DailyBrief:
        """Generate a daily brief from emails."""
        if not emails:
            return self._create_empty_brief(target_date)
        
        try:
            # Analyze emails
            analysis = self._analyze_emails(emails)
            
            # Generate content using LLM
            brief_content = await self._generate_brief_content(emails, analysis)
            
            # Create brief object
            brief = DailyBrief(
                date=datetime.combine(target_date, datetime.min.time()),
                total_emails=len(emails),
                unread_emails=sum(1 for email in emails if not email.is_read),
                categories=analysis["categories"],
                priorities=analysis["priorities"],
                headline=brief_content["headline"],
                summary=brief_content["summary"],
                action_items=brief_content["action_items"],
                deadlines=brief_content["deadlines"],
                key_threads=[],  # Would be populated with actual thread analysis
                model_used=settings.openai_model if self.openai_client else "rule_based",
                processing_time=0.0  # Would track actual processing time
            )
            
            self.stats["briefs_generated"] += 1
            self.stats["last_generation"] = datetime.now()
            
            logger.info(f"Generated daily brief for {target_date} with {len(emails)} emails")
            return brief
            
        except Exception as e:
            logger.error(f"Failed to generate brief: {str(e)}")
            return self._create_error_brief(target_date, str(e))
    
    async def _generate_brief_content(self, emails: List[Email], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate brief content using LLM or fallback logic."""
        if self.openai_client:
            return await self._generate_with_llm(emails, analysis)
        else:
            return self._generate_with_rules(emails, analysis)
    
    async def _generate_with_llm(self, emails: List[Email], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate brief content using LLM."""
        try:
            # Prepare email data for LLM
            email_summaries = []
            for email in emails[:20]:  # Limit to top 20 emails to manage token usage
                email_summary = {
                    "subject": email.subject,
                    "sender": email.sender.email,
                    "category": email.category.value,
                    "priority": email.priority.value,
                    "is_read": email.is_read,
                    "body_preview": (email.body_text or "")[:200] + "..." if email.body_text else ""
                }
                email_summaries.append(email_summary)
            
            # Create prompt
            prompt = self._create_brief_prompt(email_summaries, analysis)
            
            # Call OpenAI API
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert email assistant that creates concise daily email briefs."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            # Parse response
            content = response.choices[0].message.content
            self.stats["total_tokens_used"] += response.usage.total_tokens
            
            return self._parse_llm_response(content)
            
        except Exception as e:
            logger.error(f"LLM generation failed: {str(e)}")
            return self._generate_with_rules(emails, analysis)
    
    def _create_brief_prompt(self, email_summaries: List[Dict], analysis: Dict[str, Any]) -> str:
        """Create prompt for LLM brief generation."""
        return f"""
Create a concise daily email brief based on the following emails:

STATISTICS:
- Total emails: {analysis['total_emails']}
- Unread emails: {analysis['unread_emails']}
- Categories: {analysis['categories']}
- Priorities: {analysis['priorities']}

EMAILS:
{self._format_emails_for_prompt(email_summaries)}

Please provide a brief in the following format:

HEADLINE: [One line summary of the day's emails]

SUMMARY: [2-3 sentence overview of key themes and important messages]

ACTION ITEMS:
- [List specific actions needed based on the emails]

DEADLINES:
- [List any time-sensitive items or deadlines mentioned]

Keep the brief concise but informative. Focus on actionable insights.
"""
    
    def _format_emails_for_prompt(self, email_summaries: List[Dict]) -> str:
        """Format emails for LLM prompt."""
        formatted = []
        for i, email in enumerate(email_summaries, 1):
            formatted.append(f"""
{i}. FROM: {email['sender']}
   SUBJECT: {email['subject']}
   CATEGORY: {email['category']} | PRIORITY: {email['priority']} | READ: {email['is_read']}
   PREVIEW: {email['body_preview']}
""")
        return "\n".join(formatted)
    
    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """Parse LLM response into structured data."""
        sections = {
            "headline": "",
            "summary": "",
            "action_items": [],
            "deadlines": []
        }
        
        try:
            lines = content.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith("HEADLINE:"):
                    sections["headline"] = line.replace("HEADLINE:", "").strip()
                elif line.startswith("SUMMARY:"):
                    sections["summary"] = line.replace("SUMMARY:", "").strip()
                elif line.upper().startswith("ACTION ITEMS"):
                    current_section = "action_items"
                elif line.upper().startswith("DEADLINES"):
                    current_section = "deadlines"
                elif line.startswith("- ") and current_section:
                    sections[current_section].append(line[2:].strip())
                elif current_section == "summary" and not line.startswith(("-", "ACTION", "DEADLINE")):
                    sections["summary"] += " " + line
        
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
        
        return sections
    
    def _generate_with_rules(self, emails: List[Email], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate brief content using rule-based logic."""
        # Generate headline
        headline = self._generate_rule_based_headline(analysis)
        
        # Generate summary
        summary = self._generate_rule_based_summary(emails, analysis)
        
        # Extract action items
        action_items = self._extract_action_items(emails)
        
        # Extract deadlines
        deadlines = self._extract_deadlines(emails)
        
        return {
            "headline": headline,
            "summary": summary,
            "action_items": action_items,
            "deadlines": deadlines
        }
    
    def _generate_rule_based_headline(self, analysis: Dict[str, Any]) -> str:
        """Generate headline using rules."""
        total = analysis["total_emails"]
        unread = analysis["unread_emails"]
        
        if unread == 0:
            return f"All caught up! {total} emails processed."
        elif unread == total:
            return f"{total} new emails to review."
        else:
            return f"{unread} unread emails out of {total} total."
    
    def _generate_rule_based_summary(self, emails: List[Email], analysis: Dict[str, Any]) -> str:
        """Generate summary using rules."""
        summaries = []
        
        # Category breakdown
        categories = analysis["categories"]
        if categories.get("primary", 0) > 0:
            summaries.append(f"{categories['primary']} primary emails")
        if categories.get("social", 0) > 0:
            summaries.append(f"{categories['social']} social notifications")
        if categories.get("promotions", 0) > 0:
            summaries.append(f"{categories['promotions']} promotional emails")
        
        # Priority breakdown
        priorities = analysis["priorities"]
        if priorities.get("urgent", 0) > 0:
            summaries.append(f"{priorities['urgent']} urgent messages requiring attention")
        
        # Top senders
        sender_counts = {}
        for email in emails:
            sender = email.sender.email
            sender_counts[sender] = sender_counts.get(sender, 0) + 1
        
        top_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_senders:
            sender_info = ", ".join([f"{count} from {sender}" for sender, count in top_senders])
            summaries.append(f"Most active senders: {sender_info}")
        
        return ". ".join(summaries) + "."
    
    def _extract_action_items(self, emails: List[Email]) -> List[str]:
        """Extract action items from emails using keyword matching."""
        action_keywords = [
            "please", "action required", "respond", "reply", "review", "approve",
            "complete", "submit", "confirm", "deadline", "due", "urgent"
        ]
        
        action_items = []
        
        for email in emails:
            subject_lower = email.subject.lower()
            body_lower = (email.body_text or "").lower()
            
            # Check for action keywords
            has_action_keyword = any(keyword in subject_lower or keyword in body_lower 
                                   for keyword in action_keywords)
            
            if has_action_keyword or email.priority == EmailPriority.URGENT:
                action_item = f"Review email from {email.sender.email}: {email.subject}"
                if action_item not in action_items:
                    action_items.append(action_item)
        
        return action_items[:10]  # Limit to top 10
    
    def _extract_deadlines(self, emails: List[Email]) -> List[str]:
        """Extract deadlines from emails using keyword matching."""
        deadline_keywords = [
            "deadline", "due date", "expires", "expiring", "by end of",
            "before", "until", "no later than"
        ]
        
        deadlines = []
        
        for email in emails:
            subject_lower = email.subject.lower()
            body_lower = (email.body_text or "").lower()
            
            # Check for deadline keywords
            for keyword in deadline_keywords:
                if keyword in subject_lower or keyword in body_lower:
                    deadline = f"Check deadline in email from {email.sender.email}: {email.subject}"
                    if deadline not in deadlines:
                        deadlines.append(deadline)
                    break
        
        return deadlines[:5]  # Limit to top 5
    
    def _analyze_emails(self, emails: List[Email]) -> Dict[str, Any]:
        """Analyze emails to extract statistics."""
        categories: Dict[str, int] = {}
        priorities: Dict[str, int] = {}
        
        for category in EmailCategory:
            categories[category.value] = 0
        
        for priority in EmailPriority:
            priorities[priority.value] = 0
        
        unread_count = 0
        
        for email in emails:
            categories[email.category.value] += 1
            priorities[email.priority.value] += 1
            if not email.is_read:
                unread_count += 1
        
        return {
            "total_emails": len(emails),
            "unread_emails": unread_count,
            "categories": categories,
            "priorities": priorities
        }
    
    def _create_empty_brief(self, target_date: date) -> DailyBrief:
        """Create an empty daily brief."""
        return DailyBrief(
            date=datetime.combine(target_date, datetime.min.time()),
            total_emails=0,
            unread_emails=0,
            categories={},
            priorities={},
            headline="No emails for today",
            summary="No emails were found for this date.",
            action_items=[],
            deadlines=[]
        )
    
    def _create_error_brief(self, target_date: date, error: str) -> DailyBrief:
        """Create an error brief."""
        return DailyBrief(
            date=datetime.combine(target_date, datetime.min.time()),
            total_emails=0,
            unread_emails=0,
            categories={},
            priorities={},
            headline="Error generating brief",
            summary=f"An error occurred while generating the daily brief: {error}",
            action_items=["Check email agent logs for details"],
            deadlines=[]
        )
    

    
    async def summarize_email(self, email: Email) -> Dict[str, Any]:
        """Generate detailed summary and action items for a single email."""
        if self.openai_client and email.body_text:
            try:
                prompt = f"""
Analyze this email and provide:
1. A 2-3 sentence summary
2. List of action items (if any)
3. Priority level (low/medium/high)

Email:
Subject: {email.subject}
From: {email.sender.email}
Body: {email.body_text[:2000]}...

Format response as:
SUMMARY: [your summary]
ACTION_ITEMS: [bullet points of actions needed]
PRIORITY: [low/medium/high]
"""
                
                response = await self.openai_client.chat.completions.create(
                    model=settings.openai_model,
                    messages=[
                        {"role": "system", "content": "You are an expert at analyzing emails and extracting actionable insights."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=300,
                    temperature=0.3
                )
                
                content = response.choices[0].message.content.strip()
                self.stats["emails_summarized"] += 1
                self.stats["total_tokens_used"] += response.usage.total_tokens
                
                # Parse the response
                summary_data = self._parse_email_analysis(content)
                return summary_data
                
            except Exception as e:
                logger.error(f"Failed to analyze email {email.id}: {str(e)}")
        
        # Fallback to rule-based analysis
        return {
            "summary": f"Email from {email.sender.email} about: {email.subject}",
            "action_items": self._extract_action_items([email]),
            "priority": email.priority.value
        }
    
    async def filter_emails_by_query(self, emails: List[Email], query: str) -> List[Email]:
        """Filter emails using AI based on natural language query."""
        if not self.openai_client or not emails:
            return []
        
        try:
            # Create email summaries for analysis
            email_summaries = []
            for email in emails[:50]:  # Limit for token efficiency
                summary = f"ID: {email.id}\nSubject: {email.subject}\nFrom: {email.sender.email}\nDate: {email.date}\nCategory: {email.category.value}\n"
                if email.body_text:
                    summary += f"Preview: {email.body_text[:200]}..."
                email_summaries.append(summary)
            
            prompt = f"""
Based on the query "{query}", identify which emails are most relevant.
Return only the email IDs that match the criteria, one per line.

Query: {query}

Emails:
{chr(10).join([f"{i+1}. {summary}" for i, summary in enumerate(email_summaries)])}

Return only the matching email IDs, one per line:
"""
            
            response = await self.openai_client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at filtering emails based on user queries. Return only email IDs that match the criteria."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            self.stats["total_tokens_used"] += response.usage.total_tokens
            
            # Extract email IDs from response
            matching_ids = []
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('ID:'):
                    # Try to extract email ID
                    for email in emails:
                        if email.id in line:
                            matching_ids.append(email.id)
                            break
            
            # Return matching emails
            filtered_emails = [email for email in emails if email.id in matching_ids]
            
            logger.info(f"AI filtered {len(filtered_emails)} emails from {len(emails)} for query: '{query}'")
            return filtered_emails
            
        except Exception as e:
            logger.error(f"Failed to filter emails with AI: {str(e)}")
            # Fallback to simple text search
            query_lower = query.lower()
            return [email for email in emails 
                   if query_lower in email.subject.lower() 
                   or query_lower in (email.body_text or "").lower()]
    
    def _parse_email_analysis(self, content: str) -> Dict[str, Any]:
        """Parse AI analysis response into structured data."""
        result = {
            "summary": "",
            "action_items": [],
            "priority": "medium"
        }
        
        try:
            lines = content.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('SUMMARY:'):
                    result["summary"] = line.replace('SUMMARY:', '').strip()
                elif line.startswith('ACTION_ITEMS:'):
                    current_section = "action_items"
                    action_text = line.replace('ACTION_ITEMS:', '').strip()
                    if action_text:
                        result["action_items"].append(action_text)
                elif line.startswith('PRIORITY:'):
                    priority = line.replace('PRIORITY:', '').strip().lower()
                    if priority in ['low', 'medium', 'high']:
                        result["priority"] = priority
                elif current_section == "action_items" and line.startswith('•') or line.startswith('-'):
                    result["action_items"].append(line.lstrip('•-').strip())
        
        except Exception as e:
            logger.error(f"Failed to parse email analysis: {str(e)}")
        
        return result
    
    async def get_status(self) -> Dict[str, Any]:
        """Get summarizer agent status."""
        return {
            "llm_available": self.openai_client is not None,
            "llm_model": settings.openai_model if self.openai_client else None,
            "stats": self.stats.copy()
        }
    
    async def shutdown(self) -> None:
        """Shutdown the summarizer agent."""
        try:
            if self.openai_client:
                await self.openai_client.close()
            logger.info("Summarizer agent shutdown completed")
        except Exception as e:
            logger.error(f"Error during summarizer shutdown: {str(e)}")