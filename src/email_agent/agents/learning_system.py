"""Learning feedback system for Email Agent."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import json
import sqlite3
from pathlib import Path

from openai import AsyncOpenAI
from ..config import settings

logger = logging.getLogger(__name__)


class LearningFeedbackSystem:
    """System that learns from user feedback to improve AI decisions."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.feedback_db_path = Path(settings.data_dir) / "learning_feedback.db"
        self._init_feedback_db()
        
    def _init_feedback_db(self):
        """Initialize the feedback database."""
        try:
            with sqlite3.connect(self.feedback_db_path) as conn:
                cursor = conn.cursor()
                
                # Feedback table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email_id TEXT,
                        agent_type TEXT,
                        decision_type TEXT,
                        original_decision TEXT,
                        user_feedback TEXT,
                        correct_decision TEXT,
                        confidence_score REAL,
                        feedback_timestamp DATETIME,
                        context_data TEXT
                    )
                """)
                
                # Learning patterns table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS learning_patterns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pattern_type TEXT,
                        pattern_data TEXT,
                        success_rate REAL,
                        usage_count INTEGER,
                        last_updated DATETIME
                    )
                """)
                
                # User preferences table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        preference_type TEXT,
                        preference_key TEXT,
                        preference_value TEXT,
                        confidence REAL,
                        last_updated DATETIME
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize feedback database: {e}")
    
    async def record_feedback(
        self,
        email_id: str,
        agent_type: str,
        decision_type: str,
        original_decision: str,
        user_feedback: str,
        correct_decision: Optional[str] = None,
        confidence_score: float = 0.5,
        context_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Record user feedback on AI decisions."""
        
        try:
            with sqlite3.connect(self.feedback_db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO feedback (
                        email_id, agent_type, decision_type, original_decision,
                        user_feedback, correct_decision, confidence_score,
                        feedback_timestamp, context_data
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    email_id, agent_type, decision_type, original_decision,
                    user_feedback, correct_decision, confidence_score,
                    datetime.now().isoformat(), json.dumps(context_data or {})
                ))
                
                conn.commit()
                
                logger.info(f"Recorded feedback for {agent_type} decision on email {email_id}")
                
                # Update learning patterns
                await self._update_learning_patterns(agent_type, decision_type, user_feedback, context_data)
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")
            return False
    
    async def _update_learning_patterns(
        self,
        agent_type: str,
        decision_type: str,
        user_feedback: str,
        context_data: Optional[Dict[str, Any]]
    ):
        """Update learning patterns based on feedback."""
        
        try:
            # Analyze feedback with AI to extract patterns
            pattern_prompt = f"""
            Analyze this user feedback to extract learning patterns:
            
            Agent Type: {agent_type}
            Decision Type: {decision_type}
            User Feedback: {user_feedback}
            Context: {json.dumps(context_data or {}, indent=2)}
            
            Extract patterns as JSON:
            {{
                "pattern_type": "categorization|priority|action_extraction|threading",
                "key_indicators": ["list of indicators that led to this feedback"],
                "correction_rule": "what rule should be applied in similar cases",
                "confidence": 0.8,
                "applicable_contexts": ["when this pattern applies"],
                "sender_patterns": ["patterns about sender behavior"],
                "content_patterns": ["patterns in email content"],
                "timing_patterns": ["patterns related to timing"]
            }}
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a machine learning pattern analyzer. Extract actionable patterns from user feedback."},
                    {"role": "user", "content": pattern_prompt}
                ],
                temperature=0.1
            )
            
            pattern_data = json.loads(response.choices[0].message.content)
            
            # Store pattern in database
            with sqlite3.connect(self.feedback_db_path) as conn:
                cursor = conn.cursor()
                
                # Check if similar pattern exists
                cursor.execute("""
                    SELECT id, success_rate, usage_count FROM learning_patterns
                    WHERE pattern_type = ? AND pattern_data LIKE ?
                """, (pattern_data['pattern_type'], f"%{pattern_data.get('correction_rule', '')}%"))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing pattern
                    pattern_id, success_rate, usage_count = existing
                    new_usage_count = usage_count + 1
                    new_success_rate = (success_rate * usage_count + pattern_data['confidence']) / new_usage_count
                    
                    cursor.execute("""
                        UPDATE learning_patterns
                        SET success_rate = ?, usage_count = ?, last_updated = ?
                        WHERE id = ?
                    """, (new_success_rate, new_usage_count, datetime.now().isoformat(), pattern_id))
                    
                else:
                    # Insert new pattern
                    cursor.execute("""
                        INSERT INTO learning_patterns (
                            pattern_type, pattern_data, success_rate, usage_count, last_updated
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        pattern_data['pattern_type'],
                        json.dumps(pattern_data),
                        pattern_data['confidence'],
                        1,
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to update learning patterns: {e}")
    
    async def get_decision_suggestions(
        self,
        agent_type: str,
        decision_type: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get AI decision suggestions based on learned patterns."""
        
        try:
            # Get relevant patterns from database
            with sqlite3.connect(self.feedback_db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT pattern_data, success_rate, usage_count
                    FROM learning_patterns
                    WHERE pattern_type = ? AND success_rate > 0.6
                    ORDER BY success_rate DESC, usage_count DESC
                    LIMIT 10
                """, (decision_type,))
                
                patterns = cursor.fetchall()
            
            if not patterns:
                return []
            
            # Analyze context against patterns
            suggestions_prompt = f"""
            Based on these learned patterns, suggest the best decision for this context:
            
            Agent Type: {agent_type}
            Decision Type: {decision_type}
            Current Context: {json.dumps(context, indent=2)}
            
            Learned Patterns:
            {chr(10).join([f"Pattern {i+1} (Success: {success_rate:.2f}, Used: {usage_count}x): {pattern_data}" for i, (pattern_data, success_rate, usage_count) in enumerate(patterns)])}
            
            Provide suggestions as JSON:
            [
                {{
                    "suggested_decision": "recommended decision",
                    "confidence": 0.85,
                    "reasoning": "why this decision is recommended",
                    "matching_patterns": ["which patterns support this"],
                    "risk_factors": ["potential risks with this decision"]
                }}
            ]
            
            Provide up to 3 suggestions, ranked by confidence.
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an intelligent decision support system that learns from user feedback."},
                    {"role": "user", "content": suggestions_prompt}
                ],
                temperature=0.2
            )
            
            suggestions = json.loads(response.choices[0].message.content)
            
            # Add metadata
            for suggestion in suggestions:
                suggestion['generated_at'] = datetime.now().isoformat()
                suggestion['based_on_patterns'] = len(patterns)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to get decision suggestions: {e}")
            return []
    
    async def get_user_preferences(self, preference_type: str) -> Dict[str, Any]:
        """Get learned user preferences."""
        
        try:
            with sqlite3.connect(self.feedback_db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT preference_key, preference_value, confidence
                    FROM user_preferences
                    WHERE preference_type = ? AND confidence > 0.5
                    ORDER BY confidence DESC
                """, (preference_type,))
                
                preferences = cursor.fetchall()
            
            return {
                key: {"value": value, "confidence": confidence}
                for key, value, confidence in preferences
            }
            
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return {}
    
    async def update_user_preference(
        self,
        preference_type: str,
        preference_key: str,
        preference_value: str,
        confidence: float = 0.8
    ) -> bool:
        """Update user preferences based on behavior patterns."""
        
        try:
            with sqlite3.connect(self.feedback_db_path) as conn:
                cursor = conn.cursor()
                
                # Check if preference exists
                cursor.execute("""
                    SELECT id, confidence FROM user_preferences
                    WHERE preference_type = ? AND preference_key = ?
                """, (preference_type, preference_key))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing preference
                    pref_id, old_confidence = existing
                    new_confidence = (old_confidence + confidence) / 2  # Average confidences
                    
                    cursor.execute("""
                        UPDATE user_preferences
                        SET preference_value = ?, confidence = ?, last_updated = ?
                        WHERE id = ?
                    """, (preference_value, new_confidence, datetime.now().isoformat(), pref_id))
                    
                else:
                    # Insert new preference
                    cursor.execute("""
                        INSERT INTO user_preferences (
                            preference_type, preference_key, preference_value,
                            confidence, last_updated
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        preference_type, preference_key, preference_value,
                        confidence, datetime.now().isoformat()
                    ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to update user preference: {e}")
            return False
    
    async def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning system statistics."""
        
        try:
            with sqlite3.connect(self.feedback_db_path) as conn:
                cursor = conn.cursor()
                
                # Feedback stats
                cursor.execute("SELECT COUNT(*) FROM feedback")
                total_feedback = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT agent_type, COUNT(*) FROM feedback
                    GROUP BY agent_type
                """)
                feedback_by_agent = dict(cursor.fetchall())
                
                # Pattern stats
                cursor.execute("SELECT COUNT(*) FROM learning_patterns")
                total_patterns = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT pattern_type, COUNT(*), AVG(success_rate)
                    FROM learning_patterns
                    GROUP BY pattern_type
                """)
                pattern_stats = cursor.fetchall()
                
                # Preference stats
                cursor.execute("SELECT COUNT(*) FROM user_preferences")
                total_preferences = cursor.fetchone()[0]
                
                # Recent feedback
                cursor.execute("""
                    SELECT COUNT(*) FROM feedback
                    WHERE feedback_timestamp >= ?
                """, ((datetime.now() - timedelta(days=7)).isoformat(),))
                recent_feedback = cursor.fetchone()[0]
                
            return {
                "total_feedback_records": total_feedback,
                "feedback_by_agent": feedback_by_agent,
                "total_learned_patterns": total_patterns,
                "pattern_stats": {
                    pattern_type: {"count": count, "avg_success_rate": avg_rate}
                    for pattern_type, count, avg_rate in pattern_stats
                },
                "total_user_preferences": total_preferences,
                "recent_feedback_7days": recent_feedback,
                "learning_effectiveness": sum(
                    stats["avg_success_rate"] * stats["count"]
                    for stats in [
                        {"count": count, "avg_success_rate": avg_rate}
                        for _, count, avg_rate in pattern_stats
                    ]
                ) / max(total_patterns, 1),
                "stats_generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get learning stats: {e}")
            return {"error": str(e)}
    
    async def export_learning_data(self, output_path: str) -> bool:
        """Export learning data for analysis or backup."""
        
        try:
            learning_data = {
                "exported_at": datetime.now().isoformat(),
                "stats": await self.get_learning_stats(),
                "patterns": [],
                "preferences": {},
                "recent_feedback": []
            }
            
            with sqlite3.connect(self.feedback_db_path) as conn:
                cursor = conn.cursor()
                
                # Export patterns
                cursor.execute("SELECT * FROM learning_patterns")
                patterns = cursor.fetchall()
                
                for pattern in patterns:
                    learning_data["patterns"].append({
                        "id": pattern[0],
                        "pattern_type": pattern[1],
                        "pattern_data": json.loads(pattern[2]),
                        "success_rate": pattern[3],
                        "usage_count": pattern[4],
                        "last_updated": pattern[5]
                    })
                
                # Export preferences
                cursor.execute("SELECT * FROM user_preferences")
                preferences = cursor.fetchall()
                
                for pref in preferences:
                    pref_type = pref[1]
                    if pref_type not in learning_data["preferences"]:
                        learning_data["preferences"][pref_type] = {}
                    
                    learning_data["preferences"][pref_type][pref[2]] = {
                        "value": pref[3],
                        "confidence": pref[4],
                        "last_updated": pref[5]
                    }
                
                # Export recent feedback
                cursor.execute("""
                    SELECT * FROM feedback
                    WHERE feedback_timestamp >= ?
                    ORDER BY feedback_timestamp DESC
                    LIMIT 100
                """, ((datetime.now() - timedelta(days=30)).isoformat(),))
                
                recent_feedback = cursor.fetchall()
                
                for feedback in recent_feedback:
                    learning_data["recent_feedback"].append({
                        "email_id": feedback[1],
                        "agent_type": feedback[2],
                        "decision_type": feedback[3],
                        "original_decision": feedback[4],
                        "user_feedback": feedback[5],
                        "correct_decision": feedback[6],
                        "confidence_score": feedback[7],
                        "feedback_timestamp": feedback[8],
                        "context_data": json.loads(feedback[9]) if feedback[9] else {}
                    })
            
            # Write to file
            with open(output_path, 'w') as f:
                json.dump(learning_data, f, indent=2)
            
            logger.info(f"Learning data exported to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export learning data: {e}")
            return False
    
    async def get_status(self) -> Dict[str, Any]:
        """Get learning system status."""
        return {
            "agent_type": "learning_feedback_system",
            "model": self.model,
            "feedback_db_path": str(self.feedback_db_path),
            "status": "ready" if self.feedback_db_path.exists() else "initializing"
        }
    
    async def shutdown(self) -> None:
        """Shutdown the learning system."""
        logger.info("Learning feedback system shutdown completed")