"""Thread summarization agent for Email Agent."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from openai import AsyncOpenAI

from ..config import settings
from ..models import Email

logger = logging.getLogger(__name__)


class ThreadSummarizerAgent:
    """Agent that summarizes email threads and extracts key insights."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def summarize_thread(self, emails: List[Email]) -> Dict[str, Any]:
        """Summarize an email thread with key insights."""

        if not emails:
            return {"error": "No emails provided"}

        # Sort emails by date
        sorted_emails = sorted(emails, key=lambda e: e.date)

        # Build thread context
        thread_context = []
        for i, email in enumerate(sorted_emails):
            thread_context.append(
                f"""
Message {i+1} ({email.date.strftime('%Y-%m-%d %H:%M')}):
From: {email.sender.name or email.sender.email}
Subject: {email.subject}
Body: {email.body[:800]}...
"""
            )

        prompt = f"""
        Analyze this email thread and provide a comprehensive summary:
        
        {chr(10).join(thread_context)}
        
        Provide a JSON response with:
        {{
            "thread_summary": "Brief overview of the thread topic and progression",
            "key_decisions": ["list of important decisions made"],
            "action_items": [
                {{
                    "action": "what needs to be done",
                    "owner": "who should do it",
                    "deadline": "YYYY-MM-DD or null",
                    "status": "open|completed|blocked"
                }}
            ],
            "participants": [
                {{
                    "email": "participant email",
                    "role": "initiator|responder|cc",
                    "engagement_level": "high|medium|low"
                }}
            ],
            "thread_status": "resolved|ongoing|stalled|escalated",
            "priority_level": "urgent|high|medium|low",
            "sentiment": "positive|neutral|negative|mixed",
            "next_steps": ["what should happen next"],
            "key_dates": [
                {{
                    "date": "YYYY-MM-DD",
                    "event": "description of what happened"
                }}
            ],
            "thread_type": "discussion|decision|information|request|meeting|complaint",
            "requires_attention": true/false,
            "estimated_resolution_time": "time estimate for completion"
        }}
        
        Focus on actionable insights and clear next steps.
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert email thread analyst. Extract key insights and actionable information from email conversations. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )

            result = json.loads(response.choices[0].message.content)

            # Add metadata
            result["thread_id"] = emails[0].thread_id if emails else None
            result["email_count"] = len(emails)
            result["date_range"] = {
                "start": sorted_emails[0].date.isoformat(),
                "end": sorted_emails[-1].date.isoformat(),
            }
            result["summarized_at"] = datetime.now().isoformat()

            return result

        except Exception as e:
            logger.error(f"Failed to summarize thread: {str(e)}")
            return {
                "error": str(e),
                "thread_id": emails[0].thread_id if emails else None,
                "email_count": len(emails),
            }

    async def get_thread_insights(
        self, thread_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate deeper insights from thread summary."""

        if "error" in thread_summary:
            return thread_summary

        insights_prompt = f"""
        Based on this email thread summary, provide strategic insights:
        
        Thread Summary: {thread_summary.get('thread_summary', 'N/A')}
        Status: {thread_summary.get('thread_status', 'N/A')}
        Priority: {thread_summary.get('priority_level', 'N/A')}
        Type: {thread_summary.get('thread_type', 'N/A')}
        
        Action Items: {json.dumps(thread_summary.get('action_items', []), indent=2)}
        
        Provide insights as JSON:
        {{
            "business_impact": "assessment of business/personal impact",
            "risk_factors": ["potential risks or blockers"],
            "opportunities": ["potential opportunities identified"],
            "communication_quality": "assessment of communication effectiveness",
            "escalation_needed": true/false,
            "follow_up_strategy": "recommended approach for follow-up",
            "similar_patterns": "any recurring patterns noticed",
            "efficiency_score": 1-10,
            "collaboration_score": 1-10,
            "recommendations": ["specific actionable recommendations"]
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a business communication analyst. Provide strategic insights on email thread effectiveness and outcomes.",
                    },
                    {"role": "user", "content": insights_prompt},
                ],
                temperature=0.2,
            )

            insights = json.loads(response.choices[0].message.content)
            insights["insights_generated_at"] = datetime.now().isoformat()

            return insights

        except Exception as e:
            logger.error(f"Failed to generate thread insights: {str(e)}")
            return {"error": str(e)}

    async def summarize_multiple_threads(
        self, thread_groups: List[List[Email]]
    ) -> List[Dict[str, Any]]:
        """Summarize multiple threads efficiently."""

        # Process in batches to avoid rate limits
        batch_size = 3
        results = []

        for i in range(0, len(thread_groups), batch_size):
            batch = thread_groups[i : i + batch_size]
            tasks = [self.summarize_thread(emails) for emails in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Thread summarization error: {result}")
                    results.append({"error": str(result)})
                else:
                    results.append(result)

            # Small delay to respect rate limits
            await asyncio.sleep(0.2)

        return results

    async def generate_threads_overview(
        self, thread_summaries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate an overview of multiple thread summaries."""

        valid_summaries = [s for s in thread_summaries if "error" not in s]

        if not valid_summaries:
            return {"error": "No valid thread summaries provided"}

        # Analyze patterns across threads
        total_threads = len(valid_summaries)
        urgent_threads = len(
            [s for s in valid_summaries if s.get("priority_level") == "urgent"]
        )
        unresolved_threads = len(
            [
                s
                for s in valid_summaries
                if s.get("thread_status") in ["ongoing", "stalled"]
            ]
        )
        requires_attention = len(
            [s for s in valid_summaries if s.get("requires_attention", False)]
        )

        # Count action items
        total_actions = sum(len(s.get("action_items", [])) for s in valid_summaries)
        overdue_actions = 0

        today = datetime.now().date()
        for summary in valid_summaries:
            for action in summary.get("action_items", []):
                if action.get("deadline"):
                    try:
                        deadline = datetime.strptime(
                            action["deadline"], "%Y-%m-%d"
                        ).date()
                        if deadline < today and action.get("status") != "completed":
                            overdue_actions += 1
                    except ValueError:
                        continue

        # Thread types distribution
        thread_types = {}
        for summary in valid_summaries:
            thread_type = summary.get("thread_type", "unknown")
            thread_types[thread_type] = thread_types.get(thread_type, 0) + 1

        # Sentiment analysis
        sentiments = {}
        for summary in valid_summaries:
            sentiment = summary.get("sentiment", "neutral")
            sentiments[sentiment] = sentiments.get(sentiment, 0) + 1

        return {
            "overview_generated_at": datetime.now().isoformat(),
            "total_threads": total_threads,
            "summary_stats": {
                "urgent_threads": urgent_threads,
                "unresolved_threads": unresolved_threads,
                "requires_attention": requires_attention,
                "total_action_items": total_actions,
                "overdue_actions": overdue_actions,
            },
            "thread_types": thread_types,
            "sentiment_distribution": sentiments,
            "efficiency_metrics": {
                "avg_efficiency": (
                    sum(
                        s.get("insights", {}).get("efficiency_score", 5)
                        for s in valid_summaries
                    )
                    / total_threads
                    if total_threads > 0
                    else 0
                ),
                "avg_collaboration": (
                    sum(
                        s.get("insights", {}).get("collaboration_score", 5)
                        for s in valid_summaries
                    )
                    / total_threads
                    if total_threads > 0
                    else 0
                ),
            },
            "top_priorities": [
                s
                for s in valid_summaries
                if s.get("priority_level") in ["urgent", "high"]
                and s.get("requires_attention", False)
            ][:5],
            "recommendations": [
                f"Focus on {urgent_threads} urgent threads requiring immediate attention",
                f"Follow up on {unresolved_threads} unresolved threads",
                f"Address {overdue_actions} overdue action items",
                "Review stalled threads for potential escalation",
            ],
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get thread summarizer status."""
        return {
            "agent_type": "thread_summarizer",
            "model": self.model,
            "status": "ready",
        }

    async def shutdown(self) -> None:
        """Shutdown the thread summarizer agent."""
        logger.info("Thread summarizer agent shutdown completed")
