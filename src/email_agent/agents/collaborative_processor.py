"""Collaborative decision-making engine for multi-agent email processing."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from ..models import Email, EmailAddress, EmailCategory, EmailPriority
from .enhanced_ceo_labeler import EnhancedCEOLabeler
from .relationship_intelligence import RelationshipIntelligence
from .thread_intelligence import ThreadIntelligence
from .triage_agent import TriageAgent

logger = logging.getLogger(__name__)


class AgentConfidence(Enum):
    """Agent confidence levels for collaborative decisions."""
    VERY_LOW = 0.2
    LOW = 0.4
    MEDIUM = 0.6
    HIGH = 0.8
    VERY_HIGH = 1.0


@dataclass
class AgentAssessment:
    """Individual agent's assessment of an email."""
    agent_name: str
    priority_score: float  # 0-1 scale
    confidence: AgentConfidence
    reasoning: str
    suggested_labels: List[str]
    urgency_level: str  # critical, high, medium, low
    risk_factors: List[str]
    opportunities: List[str]
    metadata: Dict[str, Any]


@dataclass
class CollaborativeDecision:
    """Final collaborative decision from multiple agents."""
    email_id: str
    final_priority: float
    consensus_confidence: float
    agreed_labels: List[str]
    final_urgency: str
    reasoning_summary: str
    agent_assessments: List[AgentAssessment]
    conflicts_resolved: List[str]
    decision_timestamp: datetime
    should_escalate: bool
    follow_up_actions: List[str]


class CollaborativeEmailProcessor:
    """Multi-agent collaborative decision-making system."""
    
    def __init__(self):
        """Initialize the collaborative processor."""
        self.ceo_labeler = EnhancedCEOLabeler()
        self.relationship_agent = RelationshipIntelligence()
        self.thread_agent = ThreadIntelligence()
        self.triage_agent = TriageAgent()
        
        # Collaboration weights for different agent types
        self.agent_weights = {
            'ceo_strategic': 0.35,  # CEO strategic assessment gets highest weight
            'relationship': 0.25,   # Relationship context is crucial
            'thread_context': 0.20, # Thread continuity matters
            'triage_baseline': 0.20 # Basic triage provides foundation
        }
        
        # Improved confidence thresholds for better decision diversity
        self.confidence_thresholds = {
            'high_priority': 0.65,    # Lowered from 0.75
            'escalation': 0.70,       # Lowered from 0.80
            'autonomous_action': 0.80  # Lowered from 0.85
        }
        
        # Batch intelligence cache
        self._batch_profiles_built = False
        self._batch_relationships_analyzed = False
        self._batch_threads_analyzed = False
        
        logger.info("🤝 Collaborative Email Processor initialized")
    
    async def prepare_batch_intelligence(self, emails: List[Email]) -> None:
        """Pre-build intelligence for a batch of emails to avoid redundant work."""
        logger.info(f"🧠 Pre-building batch intelligence for {len(emails)} emails...")
        
        # Build all sender profiles at once
        if not self._batch_profiles_built:
            await self.ceo_labeler.build_sender_profiles(emails)
            self._batch_profiles_built = True
            logger.debug(f"  ✅ Built profiles for {len(self.ceo_labeler.sender_profiles)} senders")
        
        # Analyze all relationships at once  
        if not self._batch_relationships_analyzed:
            await self.relationship_agent.analyze_relationships(emails)
            self._batch_relationships_analyzed = True
            logger.debug(f"  🤝 Analyzed {len(self.relationship_agent.contact_profiles)} relationships")
        
        # Analyze all threads at once
        if not self._batch_threads_analyzed:
            await self.thread_agent.analyze_thread_patterns(emails)
            self._batch_threads_analyzed = True
            logger.debug(f"  🧵 Analyzed {len(self.thread_agent.thread_profiles)} threads")
    
    def reset_batch_cache(self) -> None:
        """Reset batch cache for new batch processing."""
        self._batch_profiles_built = False
        self._batch_relationships_analyzed = False
        self._batch_threads_analyzed = False
        logger.debug("🔄 Batch intelligence cache reset")
    
    async def process_email_collaboratively(self, email: Email) -> CollaborativeDecision:
        """Process email with multi-agent collaboration."""
        logger.info(f"🧠 Starting collaborative assessment for: {email.subject[:50]}...")
        
        try:
            # Phase 1: Gather individual agent assessments
            assessments = await self._gather_agent_assessments(email)
            
            # Phase 2: Agents "discuss" and identify conflicts
            conflicts = await self._identify_conflicts(assessments)
            
            # Phase 3: Resolve conflicts through weighted consensus
            consensus = await self._build_consensus(email, assessments, conflicts)
            
            # Phase 4: Generate collaborative decision
            decision = await self._finalize_decision(email, assessments, consensus, conflicts)
            
            logger.info(f"✅ Collaborative decision complete: {decision.final_urgency} priority")
            return decision
            
        except Exception as e:
            logger.error(f"❌ Collaborative processing failed: {e}")
            # Fallback to basic triage
            return await self._fallback_decision(email)
    
    async def _gather_agent_assessments(self, email: Email) -> List[AgentAssessment]:
        """Gather assessments from all specialist agents."""
        logger.debug("📊 Gathering assessments from all agents...")
        
        # Run all agent assessments in parallel
        ceo_task = self._get_ceo_strategic_assessment(email)
        relationship_task = self._get_relationship_assessment(email)
        thread_task = self._get_thread_context_assessment(email)
        triage_task = self._get_triage_baseline_assessment(email)
        
        assessments = await asyncio.gather(
            ceo_task, relationship_task, thread_task, triage_task,
            return_exceptions=True
        )
        
        # Filter out failed assessments
        valid_assessments = [a for a in assessments if isinstance(a, AgentAssessment)]
        
        logger.debug(f"📈 Collected {len(valid_assessments)} agent assessments")
        return valid_assessments
    
    async def _get_ceo_strategic_assessment(self, email: Email) -> AgentAssessment:
        """Get CEO strategic importance assessment."""
        try:
            # Use pre-built sender profile (no redundant building)
            sender_profile = self.ceo_labeler.sender_profiles.get(email.sender.email.lower())
            if not sender_profile:
                strategic_score = 0.3
                reasoning = "Unknown sender, low strategic importance"
                urgency = "medium"
            else:
                strategic_score = sender_profile.importance_score / 100.0
                reasoning = f"Strategic importance: {sender_profile.strategic_importance}"
                
                if sender_profile.strategic_importance == 'critical':
                    urgency = "critical"
                elif sender_profile.strategic_importance == 'high':
                    urgency = "high"
                else:
                    urgency = "medium"
            
            # Get enhanced labels
            labels, label_reason = await self.ceo_labeler.get_enhanced_labels(email)
            
            # Determine confidence based on strategic importance and profile strength
            if sender_profile and sender_profile.strategic_importance == 'critical':
                confidence = AgentConfidence.VERY_HIGH  # Critical senders = very high confidence
            elif sender_profile and sender_profile.strategic_importance == 'high':
                confidence = AgentConfidence.HIGH  # High importance = high confidence
            elif sender_profile and sender_profile.total_emails > 5:
                confidence = AgentConfidence.HIGH
            elif sender_profile and sender_profile.total_emails > 2:
                confidence = AgentConfidence.MEDIUM
            else:
                confidence = AgentConfidence.LOW
            
            # Identify risks and opportunities
            risks = []
            opportunities = []
            
            if strategic_score > 0.7:
                opportunities.append("High-value strategic relationship")
            if "urgent" in email.subject.lower() and strategic_score < 0.5:
                risks.append("Urgency claim from non-strategic sender")
            
            return AgentAssessment(
                agent_name="CEO Strategic Advisor",
                priority_score=strategic_score,
                confidence=confidence,
                reasoning=f"🎯 {reasoning}. Labels: {', '.join(labels) if labels else 'None'}",
                suggested_labels=labels or [],
                urgency_level=urgency,
                risk_factors=risks,
                opportunities=opportunities,
                metadata={
                    'sender_profile': sender_profile.__dict__ if sender_profile else None,
                    'label_reason': label_reason
                }
            )
            
        except Exception as e:
            logger.error(f"CEO assessment failed: {e}")
            return AgentAssessment(
                agent_name="CEO Strategic Advisor",
                priority_score=0.5,
                confidence=AgentConfidence.LOW,
                reasoning="🎯 Assessment unavailable - system error",
                suggested_labels=[],
                urgency_level="medium",
                risk_factors=["Assessment system unavailable"],
                opportunities=[],
                metadata={}
            )
    
    async def _get_relationship_assessment(self, email: Email) -> AgentAssessment:
        """Get relationship intelligence assessment."""
        try:
            # Use pre-built relationship intelligence (no redundant analysis)
            contact_profile = None
            for profile in self.relationship_agent.contact_profiles.values():
                if profile.email.lower() == email.sender.email.lower():
                    contact_profile = profile
                    break
            
            if contact_profile:
                # Enhanced scoring based on relationship type and importance
                relationship_scores = {
                    'founder': 0.98,     # Founder gets highest priority
                    'internal': 0.95,    # Internal company emails
                    'board': 0.95,
                    'investor': 0.90,
                    'advisor': 0.75,
                    'vendor_critical': 0.70,  # Critical vendors higher
                    'customer': 0.60,
                    'team': 0.55,
                    'vendor_important': 0.45,  # Important vendors
                    'vendor': 0.30
                }
                
                priority_score = relationship_scores.get(contact_profile.relationship_type, 0.40)
                
                reasoning = f"🤝 {contact_profile.relationship_type.title()} relationship"
                if contact_profile.company:
                    reasoning += f" at {contact_profile.company}"
                
                urgency = "critical" if priority_score > 0.85 else "high" if priority_score > 0.65 else "medium"
                confidence = AgentConfidence.HIGH
                
                opportunities = []
                if contact_profile.relationship_type in ['board', 'investor']:
                    opportunities.append("Strategic relationship maintenance")
                
                risks = []
                if urgency == "critical" and "delay" not in email.subject.lower():
                    risks.append("High-stakes relationship - response timing critical")
                
            else:
                # Fallback: check email domain for strategic classification
                sender_domain = email.sender.email.split('@')[-1] if '@' in email.sender.email else ''
                
                # Use CEO labeler's strategic domains for fallback classification
                domain_classification = self.ceo_labeler.strategic_domains.get(sender_domain)
                
                if domain_classification == 'internal':
                    priority_score = 0.95
                    reasoning = "🤝 Internal email (domain-based detection)"
                    urgency = "critical"
                    confidence = AgentConfidence.HIGH
                elif domain_classification == 'vendor_critical':
                    priority_score = 0.70
                    reasoning = f"🤝 Critical vendor: {sender_domain}"
                    urgency = "high"
                    confidence = AgentConfidence.HIGH
                elif domain_classification == 'vendor_important':
                    priority_score = 0.45
                    reasoning = f"🤝 Important vendor: {sender_domain}"
                    urgency = "medium"
                    confidence = AgentConfidence.MEDIUM
                else:
                    priority_score = 0.40
                    reasoning = "🤝 Unknown relationship - new contact analysis needed"
                    urgency = "medium"
                    confidence = AgentConfidence.MEDIUM
                
                opportunities = ["Potential new relationship to cultivate"] if priority_score <= 0.40 else []
                risks = []
            
            return AgentAssessment(
                agent_name="Relationship Intelligence",
                priority_score=priority_score,
                confidence=confidence,
                reasoning=reasoning,
                suggested_labels=["KeyRelationships"] if priority_score > 0.70 else [],
                urgency_level=urgency,
                risk_factors=risks,
                opportunities=opportunities,
                metadata={
                    'contact_profile': contact_profile.__dict__ if contact_profile else None,
                    'strategic_contacts': len(self.relationship_agent.contact_profiles)
                }
            )
            
        except Exception as e:
            logger.error(f"Relationship assessment failed: {e}")
            return AgentAssessment(
                agent_name="Relationship Intelligence",
                priority_score=0.4,
                confidence=AgentConfidence.LOW,
                reasoning="🤝 Relationship analysis unavailable",
                suggested_labels=[],
                urgency_level="medium",
                risk_factors=["Relationship context unavailable"],
                opportunities=[],
                metadata={}
            )
    
    async def _get_thread_context_assessment(self, email: Email) -> AgentAssessment:
        """Get thread continuity assessment."""
        try:
            # Use pre-built thread intelligence (no redundant analysis) 
            thread_profile = None
            for profile in self.thread_agent.thread_profiles.values():
                if profile.thread_id == email.thread_id:
                    thread_profile = profile
                    break
            
            if thread_profile:
                # Score based on thread type and status
                thread_scores = {
                    'decision': 0.80,
                    'escalation': 0.85,
                    'discussion': 0.60,
                    'transactional': 0.40
                }
                
                status_multipliers = {
                    'active': 1.0,
                    'stalled': 1.2,  # Stalled threads need attention
                    'escalated': 1.3,
                    'dormant': 0.7
                }
                
                base_score = thread_scores.get(thread_profile.thread_type, 0.50)
                status_multiplier = status_multipliers.get(thread_profile.status, 1.0)
                priority_score = min(base_score * status_multiplier, 1.0)
                
                reasoning = f"🧵 {thread_profile.thread_type.title()} thread ({thread_profile.status})"
                if thread_profile.message_count > 5:
                    reasoning += f", {thread_profile.message_count} messages"
                
                urgency = "high" if priority_score > 0.75 else "medium" if priority_score > 0.50 else "low"
                confidence = AgentConfidence.HIGH if thread_profile.message_count > 3 else AgentConfidence.MEDIUM
                
                opportunities = []
                risks = []
                
                if thread_profile.status == 'stalled':
                    risks.append("Thread stalled - may need intervention")
                    opportunities.append("Opportunity to unblock progress")
                
                if thread_profile.thread_type == 'decision' and not thread_profile.decisions_made:
                    risks.append("Decision thread without clear outcome")
                
            else:
                priority_score = 0.35
                reasoning = "🧵 New thread - no conversation history"
                urgency = "medium"
                confidence = AgentConfidence.LOW
                opportunities = ["Start of new conversation"]
                risks = []
            
            return AgentAssessment(
                agent_name="Thread Intelligence",
                priority_score=priority_score,
                confidence=confidence,
                reasoning=reasoning,
                suggested_labels=["ThreadContinuity"] if priority_score > 0.65 else [],
                urgency_level=urgency,
                risk_factors=risks,
                opportunities=opportunities,
                metadata={
                    'thread_profile': thread_profile.__dict__ if thread_profile else None,
                    'critical_threads': len(self.thread_agent.thread_profiles)
                }
            )
            
        except Exception as e:
            logger.error(f"Thread assessment failed: {e}")
            return AgentAssessment(
                agent_name="Thread Intelligence",
                priority_score=0.4,
                confidence=AgentConfidence.LOW,
                reasoning="🧵 Thread analysis unavailable",
                suggested_labels=[],
                urgency_level="medium",
                risk_factors=["Thread context unavailable"],
                opportunities=[],
                metadata={}
            )
    
    async def _get_triage_baseline_assessment(self, email: Email) -> AgentAssessment:
        """Get baseline triage assessment with strategic awareness."""
        try:
            # Get triage decision
            decision, attention_score = await self.triage_agent.make_triage_decision(email)
            
            base_priority_score = attention_score.score / 100.0
            
            # Boost score for strategic senders (use CEO labeler profiles)
            strategic_boost = 0.0
            sender_profile = self.ceo_labeler.sender_profiles.get(email.sender.email.lower())
            if sender_profile:
                if sender_profile.strategic_importance == 'critical':
                    strategic_boost = 0.40  # Significant boost for critical senders
                elif sender_profile.strategic_importance == 'high':
                    strategic_boost = 0.25  # Boost for high importance
                elif sender_profile.strategic_importance == 'medium':
                    strategic_boost = 0.10  # Small boost for medium
            
            priority_score = min(base_priority_score + strategic_boost, 1.0)
            
            reasoning = f"📋 Attention score: {attention_score.score:.1f}"
            if strategic_boost > 0:
                reasoning += f" + strategic boost: {strategic_boost:.2f}"
            reasoning += f", Decision: {decision.value}"
            
            urgency_mapping = {
                'PRIORITY_INBOX': 'high',
                'REGULAR_INBOX': 'medium', 
                'AUTO_ARCHIVE': 'low',
                'SPAM_FOLDER': 'low'
            }
            
            urgency = urgency_mapping.get(decision.value, 'medium')
            
            # Confidence based on score clarity
            if attention_score.score > 80 or attention_score.score < 20:
                confidence = AgentConfidence.HIGH
            elif attention_score.score > 60 or attention_score.score < 40:
                confidence = AgentConfidence.MEDIUM
            else:
                confidence = AgentConfidence.LOW
            
            risks = []
            opportunities = []
            
            if decision.value == 'SPAM_FOLDER':
                risks.append("Flagged as potential spam")
            elif decision.value == 'PRIORITY_INBOX':
                opportunities.append("High attention score indicates importance")
            
            return AgentAssessment(
                agent_name="Triage Baseline",
                priority_score=priority_score,
                confidence=confidence,
                reasoning=reasoning,
                suggested_labels=[],
                urgency_level=urgency,
                risk_factors=risks,
                opportunities=opportunities,
                metadata={
                    'triage_decision': decision.value,
                    'attention_score': attention_score.score,
                    'factors': attention_score.factors
                }
            )
            
        except Exception as e:
            logger.error(f"Triage assessment failed: {e}")
            return AgentAssessment(
                agent_name="Triage Baseline",
                priority_score=0.5,
                confidence=AgentConfidence.LOW,
                reasoning="📋 Triage analysis unavailable",
                suggested_labels=[],
                urgency_level="medium",
                risk_factors=["Baseline triage unavailable"],
                opportunities=[],
                metadata={}
            )
    
    async def _identify_conflicts(self, assessments: List[AgentAssessment]) -> List[str]:
        """Identify conflicts between agent assessments."""
        conflicts = []
        
        if len(assessments) < 2:
            return conflicts
        
        # Check for priority score conflicts (> 0.3 difference)
        scores = [a.priority_score for a in assessments]
        if max(scores) - min(scores) > 0.3:
            conflicts.append(f"Priority score conflict: {min(scores):.2f} to {max(scores):.2f}")
        
        # Check for urgency level conflicts
        urgencies = [a.urgency_level for a in assessments]
        if len(set(urgencies)) > 2:
            conflicts.append(f"Urgency disagreement: {', '.join(set(urgencies))}")
        
        # Check for confidence conflicts with high scores
        high_conf_agents = [a for a in assessments if a.confidence.value >= 0.8]
        if len(high_conf_agents) >= 2:
            high_conf_scores = [a.priority_score for a in high_conf_agents]
            if max(high_conf_scores) - min(high_conf_scores) > 0.2:
                conflicts.append("High-confidence agents disagree on priority")
        
        return conflicts
    
    async def _build_consensus(self, email: Email, assessments: List[AgentAssessment], conflicts: List[str]) -> Dict[str, Any]:
        """Build consensus from agent assessments."""
        if not assessments:
            return {'priority_score': 0.5, 'urgency': 'medium', 'confidence': 0.3}
        
        # Weighted average of priority scores
        weighted_score = 0.0
        total_weight = 0.0
        
        for assessment in assessments:
            # Get agent weight
            agent_type = self._get_agent_type(assessment.agent_name)
            weight = self.agent_weights.get(agent_type, 0.15)
            
            # Apply confidence multiplier
            confidence_multiplier = assessment.confidence.value
            final_weight = weight * confidence_multiplier
            
            weighted_score += assessment.priority_score * final_weight
            total_weight += final_weight
        
        if total_weight > 0:
            consensus_score = weighted_score / total_weight
        else:
            consensus_score = 0.5
        
        # Consensus urgency (majority wins, but high-confidence agents get more weight)
        urgency_votes = {}
        for assessment in assessments:
            urgency = assessment.urgency_level
            weight = assessment.confidence.value
            urgency_votes[urgency] = urgency_votes.get(urgency, 0) + weight
        
        consensus_urgency = max(urgency_votes, key=urgency_votes.get) if urgency_votes else 'medium'
        
        # Overall consensus confidence
        avg_confidence = sum(a.confidence.value for a in assessments) / len(assessments)
        
        # Reduce confidence if there are conflicts
        if conflicts:
            avg_confidence *= (1.0 - len(conflicts) * 0.1)
        
        return {
            'priority_score': consensus_score,
            'urgency': consensus_urgency,
            'confidence': max(avg_confidence, 0.1)  # Minimum 10% confidence
        }
    
    def _get_agent_type(self, agent_name: str) -> str:
        """Map agent name to type for weighting."""
        mapping = {
            'CEO Strategic Advisor': 'ceo_strategic',
            'Relationship Intelligence': 'relationship',
            'Thread Intelligence': 'thread_context',
            'Triage Baseline': 'triage_baseline'
        }
        return mapping.get(agent_name, 'unknown')
    
    async def _finalize_decision(self, email: Email, assessments: List[AgentAssessment], 
                               consensus: Dict[str, Any], conflicts: List[str]) -> CollaborativeDecision:
        """Create final collaborative decision."""
        
        # Combine all suggested labels
        all_labels = []
        for assessment in assessments:
            all_labels.extend(assessment.suggested_labels)
        
        # Remove duplicates while preserving order
        agreed_labels = list(dict.fromkeys(all_labels))
        
        # Generate reasoning summary
        reasoning_parts = []
        for assessment in assessments:
            if assessment.confidence.value >= 0.6:  # Only include confident assessments
                reasoning_parts.append(f"{assessment.agent_name}: {assessment.reasoning}")
        
        reasoning_summary = " | ".join(reasoning_parts) if reasoning_parts else "Consensus reached with limited confidence"
        
        # Determine if escalation is needed (improved logic)
        should_escalate = (
            consensus['priority_score'] > self.confidence_thresholds['escalation'] and
            consensus['confidence'] > 0.6
        ) or len(conflicts) > 2 or consensus['urgency'] == 'critical'
        
        # Generate follow-up actions
        follow_up_actions = []
        if should_escalate:
            follow_up_actions.append("Escalate to user for immediate attention")
        
        if consensus['urgency'] == 'critical':
            follow_up_actions.append("Priority inbox placement")
        
        if agreed_labels:
            follow_up_actions.append(f"Apply labels: {', '.join(agreed_labels)}")
        
        # Collect all opportunities
        opportunities = []
        for assessment in assessments:
            opportunities.extend(assessment.opportunities)
        
        if opportunities:
            follow_up_actions.extend(opportunities[:2])  # Top 2 opportunities
        
        return CollaborativeDecision(
            email_id=email.id,
            final_priority=consensus['priority_score'],
            consensus_confidence=consensus['confidence'],
            agreed_labels=agreed_labels,
            final_urgency=consensus['urgency'],
            reasoning_summary=reasoning_summary,
            agent_assessments=assessments,
            conflicts_resolved=conflicts,
            decision_timestamp=datetime.now(),
            should_escalate=should_escalate,
            follow_up_actions=follow_up_actions
        )
    
    async def _fallback_decision(self, email: Email) -> CollaborativeDecision:
        """Fallback decision when collaborative processing fails."""
        return CollaborativeDecision(
            email_id=email.id,
            final_priority=0.5,
            consensus_confidence=0.3,
            agreed_labels=[],
            final_urgency="medium",
            reasoning_summary="Collaborative processing unavailable - using fallback",
            agent_assessments=[],
            conflicts_resolved=[],
            decision_timestamp=datetime.now(),
            should_escalate=False,
            follow_up_actions=["Manual review recommended"]
        )
    
    async def get_processor_status(self) -> Dict[str, Any]:
        """Get collaborative processor status."""
        return {
            "processor_type": "collaborative_multi_agent",
            "active_agents": len(self.agent_weights),
            "agent_weights": self.agent_weights,
            "confidence_thresholds": self.confidence_thresholds,
            "status": "ready"
        }