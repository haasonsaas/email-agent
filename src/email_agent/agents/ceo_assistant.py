"""CEO Executive Assistant Agent - Intelligent email categorization for startup CEOs."""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from openai import AsyncOpenAI

from ..config import settings
from ..models import Email

logger = logging.getLogger(__name__)


class CEOAssistantAgent:
    """Agent that acts as an executive assistant for startup CEOs."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

        # Define important domains and contacts
        self.investor_domains = [
            "sequoia.com",
            "a16z.com",
            "accel.com",
            "greylock.com",
            "ycombinator.com",
        ]
        self.key_relationship_patterns = [
            "founder",
            "ceo",
            "cto",
            "advisor",
            "board member",
            "investor",
        ]

    async def analyze_for_ceo(self, email: Email) -> Dict[str, Any]:
        """Analyze email with CEO perspective and priorities."""

        prompt = f"""
        Analyze this email as an executive assistant for a startup CEO. Consider strategic importance, urgency, and appropriate categorization.
        
        From: {email.sender.name or email.sender.email}
        Subject: {email.subject}
        Body: {getattr(email, 'body_text', getattr(email, 'body', email.subject))}
        
        Return JSON with:
        {{
            "ceo_labels": [
                // Include all applicable labels from this list:
                // Strategic: "Investors", "Customers", "Team", "Board", "Metrics"
                // Operational: "Legal", "Finance", "Product", "Vendors", "PR-Marketing"
                // Time-Sensitive: "DecisionRequired", "SignatureRequired", "WeeklyReview", "Delegatable"
                // Relationships: "KeyRelationships", "Networking", "Advisors"
                // Efficiency: "QuickWins", "DeepWork", "ReadLater"
            ],
            "strategic_importance": "critical|high|medium|low",
            "requires_ceo_action": true/false,
            "delegation_suggestion": "who this could be delegated to, if applicable",
            "time_to_handle": "estimated minutes",
            "key_insights": "brief strategic insight for CEO",
            "relationship_context": "important relationship info if applicable",
            "decision_points": ["list of decisions needed"],
            "follow_up_required": true/false,
            "sentiment": "positive|neutral|negative|urgent"
        }}
        
        Guidelines:
        - DecisionRequired: Strategic decisions only CEO can make
        - SignatureRequired: Contracts, legal docs, official approvals
        - Investors: ANY investor communication, even informal
        - Customers: Direct customer feedback, escalations, success stories
        - Team: Hiring decisions, performance issues, culture topics
        - Board: Board member communications, board meeting prep
        - Metrics: Requests for data, KPI reports, financial metrics
        - QuickWins: Can be handled in <5 minutes with clear action
        - DeepWork: Requires >30min of focused thinking/writing
        - Delegatable: Could be handled by team with guidance
        - KeyRelationships: Communications from other CEOs, key partners, advisors
        
        Be selective with labels - only apply those that truly fit. Most emails get 1-3 labels.
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert executive assistant specializing in helping startup CEOs manage their communications efficiently. You understand startup dynamics, investor relations, and CEO priorities. Always return valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)

            # Add metadata
            result["analyzed_at"] = datetime.now().isoformat()
            result["email_id"] = email.id

            # Enhance with domain analysis
            sender_domain = (
                email.sender.email.split("@")[-1] if "@" in email.sender.email else ""
            )
            if sender_domain in self.investor_domains:
                if "Investors" not in result.get("ceo_labels", []):
                    result["ceo_labels"].append("Investors")
                result["strategic_importance"] = "critical"

            # Check for key relationships
            sender_lower = (email.sender.name or email.sender.email).lower()
            if any(
                pattern in sender_lower for pattern in self.key_relationship_patterns
            ):
                if "KeyRelationships" not in result.get("ceo_labels", []):
                    result["ceo_labels"].append("KeyRelationships")

            return result

        except Exception as e:
            logger.error(f"Failed to analyze email {email.id} for CEO: {str(e)}")
            return {
                "ceo_labels": ["ReadLater"],
                "strategic_importance": "low",
                "requires_ceo_action": False,
                "error": str(e),
            }

    async def generate_ceo_brief(self, emails: List[Email]) -> Dict[str, Any]:
        """Generate executive brief for CEO from analyzed emails."""

        # Analyze all emails
        analyses = []
        for email in emails:
            analysis = await self.analyze_for_ceo(email)
            analyses.append({"email": email, "analysis": analysis})

        # Group by importance and category
        critical_items = []
        decisions_needed = []
        quick_wins = []
        investor_updates = []
        customer_insights = []
        team_matters = []

        for item in analyses:
            analysis = item["analysis"]
            email = item["email"]

            if analysis.get("strategic_importance") == "critical":
                critical_items.append(
                    {
                        "subject": email.subject,
                        "from": email.sender.name or email.sender.email,
                        "insight": analysis.get("key_insights", ""),
                        "labels": analysis.get("ceo_labels", []),
                    }
                )

            if "DecisionRequired" in analysis.get("ceo_labels", []):
                decisions_needed.extend(
                    [
                        {
                            "decision": dp,
                            "context": email.subject,
                            "from": email.sender.email,
                        }
                        for dp in analysis.get("decision_points", [])
                    ]
                )

            if "QuickWins" in analysis.get("ceo_labels", []):
                quick_wins.append(
                    {
                        "task": email.subject,
                        "time": analysis.get("time_to_handle", "5"),
                        "from": email.sender.email,
                    }
                )

            if "Investors" in analysis.get("ceo_labels", []):
                investor_updates.append(
                    {
                        "from": email.sender.name or email.sender.email,
                        "subject": email.subject,
                        "sentiment": analysis.get("sentiment", "neutral"),
                    }
                )

            if "Customers" in analysis.get("ceo_labels", []):
                customer_insights.append(
                    {
                        "insight": analysis.get("key_insights", email.subject),
                        "sentiment": analysis.get("sentiment", "neutral"),
                        "from": email.sender.email,
                    }
                )

            if "Team" in analysis.get("ceo_labels", []):
                team_matters.append(
                    {
                        "matter": email.subject,
                        "from": email.sender.name or email.sender.email,
                        "requires_action": analysis.get("requires_ceo_action", False),
                    }
                )

        return {
            "brief_generated_at": datetime.now().isoformat(),
            "total_emails_analyzed": len(emails),
            "critical_items": critical_items,
            "decisions_needed": decisions_needed,
            "quick_wins": quick_wins[:5],  # Top 5 quick wins
            "investor_updates": investor_updates,
            "customer_insights": customer_insights,
            "team_matters": team_matters,
            "summary": {
                "critical_count": len(critical_items),
                "decisions_count": len(decisions_needed),
                "quick_wins_count": len(quick_wins),
                "investor_emails": len(investor_updates),
                "customer_emails": len(customer_insights),
                "team_emails": len(team_matters),
            },
        }

    async def suggest_time_blocks(
        self, analyses: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Suggest time blocking for CEO based on email analysis."""

        time_blocks = {
            "morning_focus": [],  # Deep work items
            "quick_responses": [],  # Quick wins
            "afternoon_meetings": [],  # Calls/meetings suggested
            "end_of_day_review": [],  # Read later items
            "weekly_planning": [],  # Weekly review items
        }

        for analysis in analyses:
            labels = analysis.get("ceo_labels", [])

            if "DeepWork" in labels:
                time_blocks["morning_focus"].append(
                    {
                        "task": analysis.get("key_insights", ""),
                        "estimated_time": analysis.get("time_to_handle", "60"),
                        "email_id": analysis.get("email_id"),
                    }
                )

            if "QuickWins" in labels:
                time_blocks["quick_responses"].append(
                    {
                        "task": analysis.get("key_insights", ""),
                        "estimated_time": analysis.get("time_to_handle", "5"),
                        "email_id": analysis.get("email_id"),
                    }
                )

            if any(label in labels for label in ["Networking", "KeyRelationships"]):
                if analysis.get("follow_up_required"):
                    time_blocks["afternoon_meetings"].append(
                        {
                            "contact": analysis.get("relationship_context", ""),
                            "purpose": analysis.get("key_insights", ""),
                            "email_id": analysis.get("email_id"),
                        }
                    )

            if "ReadLater" in labels:
                time_blocks["end_of_day_review"].append(
                    {
                        "content": analysis.get("key_insights", ""),
                        "email_id": analysis.get("email_id"),
                    }
                )

            if "WeeklyReview" in labels:
                time_blocks["weekly_planning"].append(
                    {
                        "item": analysis.get("key_insights", ""),
                        "email_id": analysis.get("email_id"),
                    }
                )

        return time_blocks

    async def get_status(self) -> Dict[str, Any]:
        """Get CEO assistant agent status."""
        return {
            "agent_type": "ceo_assistant",
            "model": self.model,
            "capabilities": [
                "strategic_email_analysis",
                "ceo_label_assignment",
                "executive_briefing",
                "time_block_suggestions",
                "relationship_tracking",
            ],
            "status": "ready",
        }
