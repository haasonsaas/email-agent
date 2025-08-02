"""Smart action extraction agent for Email Agent."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from openai import AsyncOpenAI

from ..config import settings
from ..models import Email

logger = logging.getLogger(__name__)


class ActionExtractorAgent:
    """Agent that extracts actionable items, commitments, and deadlines from emails."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def extract_actions(self, email: Email) -> Dict[str, Any]:
        """Extract actionable items from an email."""

        prompt = f"""
        Analyze this email and extract actionable information:
        
        Subject: {email.subject}
        From: {email.sender.name or email.sender.email}
        Body: {getattr(email, 'body_text', getattr(email, 'body', email.subject))}
        
        Extract and return JSON with:
        {{
            "action_items": [
                {{
                    "action": "specific action to take",
                    "deadline": "YYYY-MM-DD or null",
                    "priority": "high|medium|low",
                    "category": "respond|schedule|review|follow_up|other"
                }}
            ],
            "commitments_made": [
                {{
                    "commitment": "what I committed to do",
                    "deadline": "YYYY-MM-DD or null",
                    "recipient": "who I committed to"
                }}
            ],
            "waiting_for": [
                {{
                    "waiting_for": "what I'm waiting for",
                    "from_whom": "who should provide it",
                    "deadline": "YYYY-MM-DD or null"
                }}
            ],
            "meeting_requests": [
                {{
                    "type": "schedule|reschedule|cancel",
                    "proposed_times": ["suggested times"],
                    "duration": "estimated duration",
                    "attendees": ["list of attendees"]
                }}
            ],
            "needs_response": true/false,
            "response_urgency": "urgent|normal|low",
            "summary": "brief summary of what this email is about",
            "email_type": "receipt|notification|request|conversation|newsletter|alert"
        }}
        
        Important guidelines:
        - Mark as "urgent" ONLY if: explicit deadline today/tomorrow, security/fraud alerts, time-sensitive requests
        - Routine receipts, transaction confirmations, and shipping notifications are NOT urgent
        - Bank/card transaction emails are usually just receipts unless they mention fraud or unusual activity
        - Focus on what actually requires human action vs. just informational emails
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert email analyst. Extract actionable information accurately. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )

            result = json.loads(response.choices[0].message.content)

            # Add metadata
            result["extracted_at"] = datetime.now().isoformat()
            result["email_id"] = email.id

            return result

        except Exception as e:
            logger.error(f"Failed to extract actions from email {email.id}: {str(e)}")
            return {
                "action_items": [],
                "commitments_made": [],
                "waiting_for": [],
                "meeting_requests": [],
                "needs_response": False,
                "response_urgency": "low",
                "summary": email.subject,
                "error": str(e),
            }

    async def extract_batch_actions(self, emails: List[Email]) -> List[Dict[str, Any]]:
        """Extract actions from multiple emails efficiently."""

        # Process in batches to avoid rate limits
        batch_size = 5
        results = []

        for i in range(0, len(emails), batch_size):
            batch = emails[i : i + batch_size]
            tasks = [self.extract_actions(email) for email in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch processing error: {result}")
                    results.append({"error": str(result)})
                else:
                    results.append(result)

            # Small delay to respect rate limits
            await asyncio.sleep(0.1)

        return results

    async def track_commitments(
        self, email: Email, actions: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Track commitments and deadlines from email."""

        tracked_items = []

        # Process commitments made
        for commitment in actions.get("commitments_made", []):
            tracked_items.append(
                {
                    "type": "commitment",
                    "description": commitment["commitment"],
                    "deadline": commitment.get("deadline"),
                    "recipient": commitment.get("recipient"),
                    "email_id": email.id,
                    "status": "pending",
                    "created_at": datetime.now().isoformat(),
                }
            )

        # Process things we're waiting for
        for waiting in actions.get("waiting_for", []):
            tracked_items.append(
                {
                    "type": "waiting_for",
                    "description": waiting["waiting_for"],
                    "deadline": waiting.get("deadline"),
                    "from_whom": waiting.get("from_whom"),
                    "email_id": email.id,
                    "status": "waiting",
                    "created_at": datetime.now().isoformat(),
                }
            )

        return tracked_items

    async def generate_action_summary(
        self, actions_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate a summary of all actions across emails."""

        total_actions = len(actions_list)
        urgent_actions = sum(
            1
            for actions in actions_list
            for item in actions.get("action_items", [])
            if item.get("priority") == "high"
        )

        needs_response = sum(
            1 for actions in actions_list if actions.get("needs_response", False)
        )

        deadlines_today = []
        deadlines_this_week = []

        today = datetime.now().date()
        week_end = today + timedelta(days=7)

        for actions in actions_list:
            for item in actions.get("action_items", []):
                if item.get("deadline"):
                    try:
                        deadline_date = datetime.strptime(
                            item["deadline"], "%Y-%m-%d"
                        ).date()
                        if deadline_date == today:
                            deadlines_today.append(item)
                        elif deadline_date <= week_end:
                            deadlines_this_week.append(item)
                    except ValueError:
                        continue

        return {
            "total_emails_with_actions": total_actions,
            "urgent_actions": urgent_actions,
            "needs_response": needs_response,
            "deadlines_today": len(deadlines_today),
            "deadlines_this_week": len(deadlines_this_week),
            "today_items": deadlines_today,
            "week_items": deadlines_this_week,
            "summary_generated_at": datetime.now().isoformat(),
        }

    async def get_status(self) -> Dict[str, Any]:
        """Get action extractor status."""
        return {
            "agent_type": "action_extractor",
            "model": self.model,
            "status": "ready",
        }

    async def shutdown(self) -> None:
        """Shutdown the action extractor agent."""
        logger.info("Action extractor agent shutdown completed")
