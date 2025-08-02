"""Crew-AI orchestration for Email Agent."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from crewai import Agent, Crew, Task, Process
from crewai.tools import BaseTool

from ..config import settings
from ..models import Email, DailyBrief, ConnectorConfig
from ..sdk.base import BaseCrewAdapter
from ..sdk.exceptions import AgentError
from .collector import CollectorAgent
from .categorizer import CategorizerAgent
from .summarizer import SummarizerAgent
from .sentiment_analyzer import SentimentAnalyzer
from .thread_analyzer import ThreadAnalyzer
from .triage_agent import TriageAgent
from .draft_agent import DraftAgent
from .enhanced_summarizer import EnhancedSummarizerAgent

logger = logging.getLogger(__name__)


class EmailAgentCrew(BaseCrewAdapter):
    """Crew-AI based multi-agent orchestration for email processing."""
    
    def __init__(self):
        self.crew: Optional[Crew] = None
        self.agents: Dict[str, Agent] = {}
        self.tools: Dict[str, BaseTool] = {}
        self.collector_agent: CollectorAgent = CollectorAgent()
        self.categorizer_agent: CategorizerAgent = CategorizerAgent()
        self.summarizer_agent: SummarizerAgent = SummarizerAgent()
        self.sentiment_analyzer: SentimentAnalyzer = SentimentAnalyzer()
        self.thread_analyzer: ThreadAnalyzer = ThreadAnalyzer()
        self.triage_agent: TriageAgent = TriageAgent()
        self.draft_agent: DraftAgent = DraftAgent()
        self.enhanced_summarizer: EnhancedSummarizerAgent = EnhancedSummarizerAgent()
    
    async def initialize_crew(self, agents_config: Dict[str, Any]) -> None:
        """Initialize the agent crew with configuration."""
        try:
            # Create CrewAI agents
            collector = Agent(
                role="Email Collector",
                goal="Fetch and collect emails from various sources efficiently",
                backstory="You are an expert at connecting to email services and retrieving messages. You handle authentication, rate limiting, and error recovery gracefully.",
                verbose=agents_config.get('verbose', False),
                allow_delegation=False,
                tools=self._get_collector_tools()
            )
            
            categorizer = Agent(
                role="Email Categorizer",
                goal="Categorize and organize emails using rules and ML",
                backstory="You are a master at organizing emails. You understand patterns, apply rules consistently, and can identify the true nature of each message.",
                verbose=agents_config.get('verbose', False),
                allow_delegation=False,
                tools=self._get_categorizer_tools()
            )
            
            summarizer = Agent(
                role="Email Summarizer",
                goal="Generate concise summaries and daily briefs from emails",
                backstory="You are an expert at distilling key information from large volumes of text. You identify action items, deadlines, and important details.",
                verbose=agents_config.get('verbose', False),
                allow_delegation=False,
                tools=self._get_summarizer_tools()
            )
            
            self.agents = {
                "collector": collector,
                "categorizer": categorizer,
                "summarizer": summarizer
            }
            
            # Create crew with sequential process
            self.crew = Crew(
                agents=list(self.agents.values()),
                tasks=[],  # Tasks will be added dynamically
                process=Process.sequential,
                verbose=agents_config.get('verbose', False)
            )
            
            logger.info("Email Agent crew initialized successfully")
            
        except Exception as e:
            raise AgentError(f"Failed to initialize crew: {str(e)}")
    
    async def execute_task(self, task_name: str, **kwargs: Any) -> Any:
        """Execute a task using the agent crew."""
        if not self.crew:
            raise AgentError("Crew not initialized")
        
        try:
            if task_name == "collect_emails":
                return await self._execute_collection_task(**kwargs)
            elif task_name == "categorize_emails":
                return await self._execute_categorization_task(**kwargs)
            elif task_name == "generate_brief":
                return await self._execute_brief_task(**kwargs)
            elif task_name == "full_processing":
                return await self._execute_full_processing(**kwargs)
            elif task_name == "summarize_email":
                return await self._execute_email_summary_task(**kwargs)
            elif task_name == "filter_emails":
                return await self._execute_email_filter_task(**kwargs)
            elif task_name == "analyze_sentiment":
                return await self._execute_sentiment_analysis_task(**kwargs)
            elif task_name == "analyze_threads":
                return await self._execute_thread_analysis_task(**kwargs)
            elif task_name == "comprehensive_analysis":
                return await self._execute_comprehensive_analysis_task(**kwargs)
            elif task_name == "triage_emails":
                return await self._execute_triage_task(**kwargs)
            elif task_name == "smart_inbox":
                return await self._execute_smart_inbox_task(**kwargs)
            elif task_name == "generate_drafts":
                return await self._execute_draft_generation_task(**kwargs)
            elif task_name == "analyze_writing_style":
                return await self._execute_writing_style_task(**kwargs)
            elif task_name == "generate_narrative_brief":
                return await self._execute_narrative_brief_task(**kwargs)
            else:
                raise AgentError(f"Unknown task: {task_name}")
                
        except Exception as e:
            logger.error(f"Task execution failed: {str(e)}")
            raise AgentError(f"Task {task_name} failed: {str(e)}")
    
    async def _execute_collection_task(self, **kwargs) -> List[Email]:
        """Execute email collection task."""
        connector_configs = kwargs.get('connector_configs', [])
        since = kwargs.get('since')
        
        # Create collection task
        Task(
            description=f"Collect emails from {len(connector_configs)} connectors since {since}",
            agent=self.agents["collector"],
            expected_output="List of collected emails with metadata"
        )
        
        # Execute using our custom agent logic
        emails = await self.collector_agent.collect_emails(connector_configs, since)
        
        logger.info(f"Collected {len(emails)} emails")
        return emails
    
    async def _execute_categorization_task(self, **kwargs) -> List[Email]:
        """Execute email categorization task."""
        emails = kwargs.get('emails', [])
        rules = kwargs.get('rules', [])
        
        if not emails:
            return []
        
        # Create categorization task
        Task(
            description=f"Categorize {len(emails)} emails using {len(rules)} rules",
            agent=self.agents["categorizer"],
            expected_output="List of categorized emails with updated metadata"
        )
        
        # Execute using our custom agent logic
        categorized_emails = await self.categorizer_agent.categorize_emails(emails, rules)
        
        logger.info(f"Categorized {len(categorized_emails)} emails")
        return categorized_emails
    
    async def _execute_brief_task(self, **kwargs) -> DailyBrief:
        """Execute daily brief generation task."""
        emails = kwargs.get('emails', [])
        date = kwargs.get('date', datetime.now().date())
        
        # Create brief generation task
        Task(
            description=f"Generate daily brief for {date} from {len(emails)} emails",
            agent=self.agents["summarizer"],
            expected_output="Daily brief with summary, action items, and key threads"
        )
        
        # Execute using our custom agent logic
        brief = await self.summarizer_agent.generate_brief(emails, date)
        
        logger.info(f"Generated daily brief for {date}")
        return brief
    
    async def _execute_full_processing(self, **kwargs) -> Dict[str, Any]:
        """Execute full email processing pipeline."""
        connector_configs = kwargs.get('connector_configs', [])
        rules = kwargs.get('rules', [])
        since = kwargs.get('since')
        generate_brief = kwargs.get('generate_brief', True)
        
        results = {
            "emails_collected": 0,
            "emails_categorized": 0,
            "emails_saved": 0,
            "brief_generated": False,
            "errors": []
        }
        
        try:
            # Step 1: Collect emails
            emails = await self._execute_collection_task(
                connector_configs=connector_configs,
                since=since
            )
            results["emails_collected"] = len(emails)
            
            if not emails:
                return results
            
            # Step 2: Categorize emails
            categorized_emails = await self._execute_categorization_task(
                emails=emails,
                rules=rules
            )
            results["emails_categorized"] = len(categorized_emails)
            
            # Step 3: Save emails to database
            from ..storage.database import DatabaseManager
            db = DatabaseManager()
            saved_count = db.save_emails(categorized_emails)
            results["emails_saved"] = saved_count
            logger.info(f"Saved {saved_count} emails to database")
            
            # Step 4: Generate brief if requested
            if generate_brief and categorized_emails:
                brief = await self._execute_brief_task(
                    emails=categorized_emails,
                    date=datetime.now().date()
                )
                results["brief_generated"] = True
                results["brief"] = brief
            
            return results
            
        except Exception as e:
            results["errors"].append(str(e))
            logger.error(f"Full processing failed: {str(e)}")
            return results
    
    async def _execute_email_summary_task(self, **kwargs) -> Dict[str, Any]:
        """Execute individual email summarization task."""
        email = kwargs.get('email')
        
        if not email:
            raise AgentError("No email provided for summarization")
        
        # Create summary task
        Task(
            description=f"Summarize email: {email.subject}",
            agent=self.agents["summarizer"],
            expected_output="Email summary with action items"
        )
        
        # Execute using our custom agent logic
        summary_data = await self.summarizer_agent.summarize_email(email)
        
        logger.info(f"Summarized email: {email.id}")
        return summary_data
    
    async def _execute_email_filter_task(self, **kwargs) -> List[Email]:
        """Execute AI-powered email filtering task."""
        emails = kwargs.get('emails', [])
        query = kwargs.get('query', '')
        
        if not emails or not query:
            return []
        
        # Create filtering task
        Task(
            description=f"Filter {len(emails)} emails based on query: '{query}'",
            agent=self.agents["summarizer"],
            expected_output="Filtered list of relevant emails"
        )
        
        # Execute using our custom agent logic
        filtered_emails = await self.summarizer_agent.filter_emails_by_query(emails, query)
        
        logger.info(f"Filtered {len(filtered_emails)} emails from {len(emails)} total")
        return filtered_emails
    
    async def _execute_sentiment_analysis_task(self, **kwargs) -> Dict[str, Any]:
        """Execute sentiment analysis task."""
        emails = kwargs.get('emails', [])
        
        if not emails:
            return {}
        
        # Create sentiment analysis task
        Task(
            description=f"Analyze sentiment for {len(emails)} emails",
            agent=self.agents["summarizer"],  # Use summarizer agent for now
            expected_output="Sentiment analysis results with insights"
        )
        
        # Execute sentiment analysis
        if len(emails) == 1:
            sentiment_data = await self.sentiment_analyzer.analyze_sentiment(emails[0])
        else:
            sentiment_data = await self.sentiment_analyzer.get_sentiment_insights(emails)
        
        logger.info(f"Analyzed sentiment for {len(emails)} emails")
        return sentiment_data
    
    async def _execute_thread_analysis_task(self, **kwargs) -> Dict[str, Any]:
        """Execute thread analysis task."""
        emails = kwargs.get('emails', [])
        
        if not emails:
            return {}
        
        # Create thread analysis task
        Task(
            description=f"Analyze email threads from {len(emails)} emails",
            agent=self.agents["summarizer"],
            expected_output="Thread analysis with conversation insights"
        )
        
        # Group emails by thread and analyze
        thread_data = await self.thread_analyzer.find_related_threads(emails)
        
        logger.info(f"Analyzed {len(thread_data)} threads from {len(emails)} emails")
        return {"threads": thread_data, "total_emails": len(emails)}
    
    async def _execute_comprehensive_analysis_task(self, **kwargs) -> Dict[str, Any]:
        """Execute comprehensive analysis combining all agents."""
        emails = kwargs.get('emails', [])
        
        if not emails:
            return {}
        
        logger.info(f"Starting comprehensive analysis of {len(emails)} emails")
        
        # Basic categorization and summarization
        categorized_emails = await self._execute_categorization_task(emails=emails, rules=kwargs.get('rules', []))
        
        # Sentiment analysis
        sentiment_insights = await self.sentiment_analyzer.get_sentiment_insights(emails)
        
        # Thread analysis
        thread_data = await self.thread_analyzer.find_related_threads(emails)
        
        # Generate comprehensive insights
        comprehensive_data = {
            "email_count": len(emails),
            "categorized_emails": len(categorized_emails),
            "sentiment_insights": sentiment_insights,
            "thread_analysis": {
                "threads_found": len(thread_data),
                "threads": thread_data[:10]  # Limit for response size
            },
            "summary": {
                "total_processed": len(emails),
                "categories_found": len(set(email.category.value for email in emails)),
                "priority_distribution": {
                    priority.value: sum(1 for email in emails if email.priority == priority)
                    for priority in set(email.priority for email in emails)
                },
                "time_range": {
                    "earliest": min(email.date for email in emails).isoformat() if emails else None,
                    "latest": max(email.date for email in emails).isoformat() if emails else None
                }
            }
        }
        
        logger.info("Comprehensive analysis completed")
        return comprehensive_data
    
    async def _execute_triage_task(self, **kwargs) -> Dict[str, Any]:
        """Execute email triage task."""
        emails = kwargs.get('emails', [])
        
        if not emails:
            return {"error": "No emails provided for triage"}
        
        # Create triage task
        Task(
            description=f"Triage {len(emails)} emails for attention scoring and routing",
            agent=self.agents.get("categorizer"),  # Use categorizer agent for CrewAI
            expected_output="Emails grouped by triage decision with attention scores"
        )
        
        # Execute triage using our custom agent logic
        triage_results = await self.triage_agent.process_email_batch(emails)
        
        logger.info(f"Triaged {len(emails)} emails into {len(triage_results)} groups")
        return triage_results
    
    async def _execute_smart_inbox_task(self, **kwargs) -> Dict[str, Any]:
        """Execute smart inbox creation task."""
        emails = kwargs.get('emails', [])
        
        if not emails:
            return {"priority_inbox": [], "regular_inbox": [], "archived": []}
        
        # First categorize emails
        categorized_emails = await self._execute_categorization_task(emails=emails, rules=kwargs.get('rules', []))
        
        # Then triage them
        triage_results = await self._execute_triage_task(emails=categorized_emails)
        
        # Create smart inbox structure
        smart_inbox = {
            "priority_inbox": triage_results.get("priority_inbox", []),
            "regular_inbox": triage_results.get("regular_inbox", []),
            "auto_archived": triage_results.get("auto_archive", []),
            "spam": triage_results.get("spam_folder", []),
            "stats": {
                "total_emails": len(emails),
                "priority_count": len(triage_results.get("priority_inbox", [])),
                "regular_count": len(triage_results.get("regular_inbox", [])),
                "archived_count": len(triage_results.get("auto_archive", [])),
                "spam_count": len(triage_results.get("spam_folder", []))
            }
        }
        
        logger.info(f"Created smart inbox: {smart_inbox['stats']['priority_count']} priority, {smart_inbox['stats']['regular_count']} regular")
        return smart_inbox
    
    async def _execute_draft_generation_task(self, **kwargs) -> Dict[str, Any]:
        """Execute draft generation task."""
        original_email = kwargs.get('original_email')
        context = kwargs.get('context', 'reply')
        num_suggestions = kwargs.get('num_suggestions', 3)
        
        if not original_email:
            return {"error": "No original email provided for draft generation"}
        
        # Create draft generation task
        Task(
            description=f"Generate {num_suggestions} draft suggestions for responding to email: {original_email.subject}",
            agent=self.agents.get("summarizer"),  # Use summarizer agent for CrewAI
            expected_output="Draft suggestions with confidence scores and style analysis"
        )
        
        # Execute draft generation using our custom agent logic
        draft_suggestions = self.draft_agent.generate_draft_suggestions(
            original_email, 
            context, 
            num_suggestions
        )
        
        # Format results
        results = {
            "original_email_id": original_email.id,
            "original_subject": original_email.subject,
            "context": context,
            "suggestions": [
                {
                    "subject": suggestion.subject,
                    "body": suggestion.body,
                    "confidence": suggestion.confidence,
                    "style_match": suggestion.style_match,
                    "suggested_tone": suggestion.suggested_tone,
                    "estimated_length": suggestion.estimated_length,
                    "reasoning": suggestion.reasoning,
                    "key_points": suggestion.key_points,
                    "template_used": suggestion.template_used
                }
                for suggestion in draft_suggestions
            ],
            "total_suggestions": len(draft_suggestions)
        }
        
        logger.info(f"Generated {len(draft_suggestions)} draft suggestions for email: {original_email.id}")
        return results
    
    async def _execute_writing_style_task(self, **kwargs) -> Dict[str, Any]:
        """Execute writing style analysis task."""
        sent_emails = kwargs.get('sent_emails', [])
        force_refresh = kwargs.get('force_refresh', False)
        
        if not sent_emails:
            return {"error": "No sent emails provided for writing style analysis"}
        
        # Check if we need to refresh the analysis
        if not force_refresh and not self.draft_agent.should_refresh_style():
            return self.draft_agent.get_style_summary()
        
        # Create writing style analysis task
        Task(
            description=f"Analyze writing style from {len(sent_emails)} sent emails",
            agent=self.agents.get("summarizer"),  # Use summarizer agent for CrewAI
            expected_output="Writing style profile with patterns and preferences"
        )
        
        # Execute writing style analysis using our custom agent logic
        writing_style = self.draft_agent.analyze_writing_style(sent_emails)
        
        # Format results
        results = {
            "analysis_completed": True,
            "emails_analyzed": len(sent_emails),
            "avg_length": writing_style.avg_length,
            "formality_score": writing_style.formality_score,
            "greeting_style": writing_style.greeting_style,
            "closing_style": writing_style.closing_style,
            "sentence_complexity": writing_style.sentence_complexity,
            "common_phrases": writing_style.common_phrases,
            "tone_keywords": writing_style.tone_keywords,
            "punctuation_style": writing_style.punctuation_style,
            "preferred_times": writing_style.preferred_times,
            "style_summary": self.draft_agent.get_style_summary()
        }
        
        logger.info(f"Analyzed writing style from {len(sent_emails)} sent emails")
        return results
    
    async def _execute_narrative_brief_task(self, **kwargs) -> Dict[str, Any]:
        """Execute narrative brief generation task."""
        emails = kwargs.get('emails', [])
        target_date = kwargs.get('target_date', datetime.now().date())
        context = kwargs.get('context', {})
        
        if not emails:
            return {"error": "No emails provided for narrative brief generation"}
        
        # Create narrative brief generation task
        Task(
            description=f"Generate narrative-style brief for {target_date} from {len(emails)} emails",
            agent=self.agents.get("summarizer"),  # Use summarizer agent for CrewAI
            expected_output="Narrative brief with story-like structure and <60 second reading time"
        )
        
        # Execute narrative brief generation using our enhanced agent
        brief = await self.enhanced_summarizer.generate_narrative_brief(
            emails, 
            target_date, 
            context
        )
        
        # Extract narrative metadata from summary
        import json
        narrative_summary = brief.summary
        narrative_metadata = {}
        
        if "---NARRATIVE_METADATA---" in brief.summary:
            parts = brief.summary.split("---NARRATIVE_METADATA---")
            narrative_summary = parts[0].strip()
            try:
                narrative_metadata = json.loads(parts[1].strip())
            except json.JSONDecodeError:
                narrative_metadata = {}
        
        # Format results
        results = {
            "brief_generated": True,
            "target_date": target_date.isoformat(),
            "emails_processed": len(emails),
            "brief": {
                "headline": brief.headline,
                "summary": narrative_summary,
                "action_items": brief.action_items,
                "deadlines": brief.deadlines,
                "key_threads": brief.key_threads,
                "categories": brief.categories,
                "priorities": brief.priorities,
                "estimated_reading_time": narrative_metadata.get("estimated_reading_time", 45),
                "narrative_score": narrative_metadata.get("narrative_score", 0.8),
                "story_arcs": narrative_metadata.get("story_arcs", []),
                "key_characters": narrative_metadata.get("key_characters", []),
                "themes": narrative_metadata.get("themes", [])
            },
            "model_used": brief.model_used,
            "processing_time": brief.processing_time
        }
        
        logger.info(f"Generated narrative brief for {target_date}: {results['brief']['estimated_reading_time']}s read")
        return results
    
    async def get_agent_status(self, agent_name: str) -> Dict[str, Any]:
        """Get the status of a specific agent."""
        if agent_name not in self.agents:
            return {"error": f"Unknown agent: {agent_name}"}
        
        agent = self.agents[agent_name]
        
        # Get basic agent info
        status = {
            "name": agent_name,
            "role": agent.role,
            "goal": agent.goal,
            "backstory": agent.backstory,
            "tools_count": len(agent.tools) if agent.tools else 0,
            "status": "ready" if self.crew else "not_initialized"
        }
        
        # Add agent-specific status
        if agent_name == "collector":
            status.update(await self.collector_agent.get_status())
        elif agent_name == "categorizer":
            status.update(await self.categorizer_agent.get_status())
        elif agent_name == "summarizer":
            status.update(await self.summarizer_agent.get_status())
        elif agent_name == "sentiment_analyzer":
            status.update(await self.sentiment_analyzer.get_status())
        elif agent_name == "thread_analyzer":
            status.update(await self.thread_analyzer.get_status())
        elif agent_name == "triage_agent":
            status.update(await self.triage_agent.get_status())
        elif agent_name == "draft_agent":
            status.update({"writing_style_analyzed": self.draft_agent.writing_style is not None})
        elif agent_name == "enhanced_summarizer":
            status.update(await self.enhanced_summarizer.get_status())
        
        return status
    
    async def shutdown(self) -> None:
        """Shutdown the agent crew."""
        try:
            if self.collector_agent:
                await self.collector_agent.shutdown()
            if self.categorizer_agent:
                await self.categorizer_agent.shutdown()
            if self.summarizer_agent:
                await self.summarizer_agent.shutdown()
            if self.sentiment_analyzer:
                await self.sentiment_analyzer.shutdown()
            if self.thread_analyzer:
                await self.thread_analyzer.shutdown()
            if self.triage_agent:
                await self.triage_agent.shutdown()
            if self.draft_agent:
                # Draft agent doesn't need async shutdown
                pass
            if self.enhanced_summarizer:
                # Enhanced summarizer doesn't need async shutdown
                pass
            
            self.crew = None
            self.agents.clear()
            
            logger.info("Email Agent crew shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during crew shutdown: {str(e)}")
    
    def _get_collector_tools(self) -> List[BaseTool]:
        """Get tools for the collector agent."""
        # In a real implementation, these would be actual CrewAI tools
        # For now, return empty list as our agents handle tools internally
        return []
    
    def _get_categorizer_tools(self) -> List[BaseTool]:
        """Get tools for the categorizer agent."""
        return []
    
    def _get_summarizer_tools(self) -> List[BaseTool]:
        """Get tools for the summarizer agent."""
        return []
    
    def get_crew_stats(self) -> Dict[str, Any]:
        """Get crew statistics."""
        return {
            "initialized": self.crew is not None,
            "agents_count": len(self.agents),
            "tools_count": len(self.tools),
            "agents": list(self.agents.keys()) if self.agents else []
        }