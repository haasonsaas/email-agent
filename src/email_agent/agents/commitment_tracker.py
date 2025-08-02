"""Commitment tracking agent for Email Agent."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json
import sqlite3
from pathlib import Path

from openai import AsyncOpenAI
from ..config import settings
from ..models import Email

logger = logging.getLogger(__name__)


class CommitmentTrackerAgent:
    """Agent that tracks commitments, deadlines, and follow-ups."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.tracker_db_path = Path(settings.data_dir) / "commitments.db"
        self._init_tracker_db()
        
    def _init_tracker_db(self):
        """Initialize the commitment tracking database."""
        try:
            with sqlite3.connect(self.tracker_db_path) as conn:
                cursor = conn.cursor()
                
                # Commitments table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS commitments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email_id TEXT,
                        commitment_type TEXT,
                        description TEXT,
                        committed_to TEXT,
                        committed_by TEXT,
                        deadline DATE,
                        priority TEXT,
                        status TEXT,
                        created_at DATETIME,
                        updated_at DATETIME,
                        completion_date DATETIME,
                        reminder_sent BOOLEAN DEFAULT FALSE,
                        context_data TEXT
                    )
                """)
                
                # Follow-ups table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS follow_ups (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        commitment_id INTEGER,
                        follow_up_type TEXT,
                        follow_up_date DATE,
                        status TEXT,
                        notes TEXT,
                        created_at DATETIME,
                        FOREIGN KEY (commitment_id) REFERENCES commitments (id)
                    )
                """)
                
                # Waiting items table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS waiting_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email_id TEXT,
                        description TEXT,
                        waiting_from TEXT,
                        expected_date DATE,
                        priority TEXT,
                        status TEXT,
                        created_at DATETIME,
                        updated_at DATETIME,
                        received_date DATETIME,
                        context_data TEXT
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to initialize commitment tracker database: {e}")
    
    async def track_commitments_from_actions(self, email: Email, actions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Track commitments extracted from email actions."""
        
        tracked_commitments = []
        
        try:
            with sqlite3.connect(self.tracker_db_path) as conn:
                cursor = conn.cursor()
                
                # Process commitments made
                for commitment in actions.get('commitments_made', []):
                    cursor.execute("""
                        INSERT INTO commitments (
                            email_id, commitment_type, description, committed_to,
                            committed_by, deadline, priority, status, created_at,
                            updated_at, context_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        email.id,
                        'outgoing',
                        commitment['commitment'],
                        commitment.get('recipient'),
                        email.sender.email,
                        commitment.get('deadline'),
                        'medium',  # Default priority
                        'pending',
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        json.dumps({
                            'email_subject': email.subject,
                            'sender': email.sender.email,
                            'action_context': commitment
                        })
                    ))
                    
                    commitment_id = cursor.lastrowid
                    tracked_commitments.append({
                        'id': commitment_id,
                        'type': 'commitment',
                        'description': commitment['commitment'],
                        'deadline': commitment.get('deadline'),
                        'status': 'pending'
                    })
                
                # Process waiting items
                for waiting in actions.get('waiting_for', []):
                    cursor.execute("""
                        INSERT INTO waiting_items (
                            email_id, description, waiting_from, expected_date,
                            priority, status, created_at, updated_at, context_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        email.id,
                        waiting['waiting_for'],
                        waiting.get('from_whom'),
                        waiting.get('deadline'),
                        'medium',
                        'waiting',
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        json.dumps({
                            'email_subject': email.subject,
                            'sender': email.sender.email,
                            'waiting_context': waiting
                        })
                    ))
                    
                    waiting_id = cursor.lastrowid
                    tracked_commitments.append({
                        'id': waiting_id,
                        'type': 'waiting',
                        'description': waiting['waiting_for'],
                        'expected_date': waiting.get('deadline'),
                        'status': 'waiting'
                    })
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to track commitments from actions: {e}")
        
        return tracked_commitments
    
    async def get_pending_commitments(
        self,
        commitment_type: Optional[str] = None,
        days_ahead: int = 30
    ) -> List[Dict[str, Any]]:
        """Get pending commitments within specified timeframe."""
        
        try:
            with sqlite3.connect(self.tracker_db_path) as conn:
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM commitments
                    WHERE status IN ('pending', 'in_progress')
                """
                params = []
                
                if commitment_type:
                    query += " AND commitment_type = ?"
                    params.append(commitment_type)
                
                if days_ahead > 0:
                    future_date = (datetime.now() + timedelta(days=days_ahead)).date().isoformat()
                    query += " AND (deadline IS NULL OR deadline <= ?)"
                    params.append(future_date)
                
                query += " ORDER BY deadline ASC, priority DESC"
                
                cursor.execute(query, params)
                commitments = cursor.fetchall()
                
                result = []
                for commitment in commitments:
                    result.append({
                        'id': commitment[0],
                        'email_id': commitment[1],
                        'commitment_type': commitment[2],
                        'description': commitment[3],
                        'committed_to': commitment[4],
                        'committed_by': commitment[5],
                        'deadline': commitment[6],
                        'priority': commitment[7],
                        'status': commitment[8],
                        'created_at': commitment[9],
                        'updated_at': commitment[10],
                        'days_remaining': self._calculate_days_remaining(commitment[6]) if commitment[6] else None
                    })
                
                return result
                
        except Exception as e:
            logger.error(f"Failed to get pending commitments: {e}")
            return []
    
    async def get_overdue_items(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get overdue commitments and waiting items."""
        
        today = datetime.now().date().isoformat()
        
        try:
            with sqlite3.connect(self.tracker_db_path) as conn:
                cursor = conn.cursor()
                
                # Overdue commitments
                cursor.execute("""
                    SELECT * FROM commitments
                    WHERE status IN ('pending', 'in_progress')
                    AND deadline IS NOT NULL
                    AND deadline < ?
                    ORDER BY deadline ASC
                """, (today,))
                
                overdue_commitments = []
                for commitment in cursor.fetchall():
                    overdue_commitments.append({
                        'id': commitment[0],
                        'description': commitment[3],
                        'committed_to': commitment[4],
                        'deadline': commitment[6],
                        'days_overdue': self._calculate_days_overdue(commitment[6]),
                        'priority': commitment[7],
                        'email_id': commitment[1]
                    })
                
                # Overdue waiting items
                cursor.execute("""
                    SELECT * FROM waiting_items
                    WHERE status = 'waiting'
                    AND expected_date IS NOT NULL
                    AND expected_date < ?
                    ORDER BY expected_date ASC
                """, (today,))
                
                overdue_waiting = []
                for waiting in cursor.fetchall():
                    overdue_waiting.append({
                        'id': waiting[0],
                        'description': waiting[2],
                        'waiting_from': waiting[3],
                        'expected_date': waiting[4],
                        'days_overdue': self._calculate_days_overdue(waiting[4]),
                        'priority': waiting[5],
                        'email_id': waiting[1]
                    })
                
                return {
                    'overdue_commitments': overdue_commitments,
                    'overdue_waiting': overdue_waiting
                }
                
        except Exception as e:
            logger.error(f"Failed to get overdue items: {e}")
            return {'overdue_commitments': [], 'overdue_waiting': []}
    
    async def update_commitment_status(
        self,
        commitment_id: int,
        status: str,
        notes: Optional[str] = None
    ) -> bool:
        """Update commitment status."""
        
        try:
            with sqlite3.connect(self.tracker_db_path) as conn:
                cursor = conn.cursor()
                
                update_data = {
                    'status': status,
                    'updated_at': datetime.now().isoformat()
                }
                
                if status == 'completed':
                    update_data['completion_date'] = datetime.now().isoformat()
                
                cursor.execute("""
                    UPDATE commitments
                    SET status = ?, updated_at = ?, completion_date = ?
                    WHERE id = ?
                """, (
                    status,
                    update_data['updated_at'],
                    update_data.get('completion_date'),
                    commitment_id
                ))
                
                if notes:
                    cursor.execute("""
                        INSERT INTO follow_ups (
                            commitment_id, follow_up_type, follow_up_date,
                            status, notes, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        commitment_id,
                        'status_update',
                        datetime.now().date().isoformat(),
                        status,
                        notes,
                        datetime.now().isoformat()
                    ))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to update commitment status: {e}")
            return False
    
    async def generate_commitment_report(self, days_ahead: int = 7) -> Dict[str, Any]:
        """Generate a comprehensive commitment report."""
        
        try:
            pending_commitments = await self.get_pending_commitments(days_ahead=days_ahead)
            overdue_items = await self.get_overdue_items()
            
            # Statistics
            total_pending = len(pending_commitments)
            urgent_commitments = len([c for c in pending_commitments if c.get('days_remaining', 999) <= 3])
            
            # Categorize by timeframe
            due_today = [c for c in pending_commitments if c.get('days_remaining') == 0]
            due_this_week = [c for c in pending_commitments if 0 < c.get('days_remaining', 999) <= 7]
            due_later = [c for c in pending_commitments if c.get('days_remaining', 0) > 7]
            
            # AI-powered insights
            insights_prompt = f"""
            Analyze these commitment data and provide strategic insights:
            
            Total pending commitments: {total_pending}
            Overdue commitments: {len(overdue_items['overdue_commitments'])}
            Overdue waiting items: {len(overdue_items['overdue_waiting'])}
            Due today: {len(due_today)}
            Due this week: {len(due_this_week)}
            
            Sample commitments:
            {json.dumps([c['description'] for c in pending_commitments[:5]], indent=2)}
            
            Provide insights as JSON:
            {{
                "workload_assessment": "light|moderate|heavy|overwhelming",
                "priority_recommendations": ["specific actions to take"],
                "risk_factors": ["potential issues identified"],
                "efficiency_tips": ["suggestions for better commitment management"],
                "follow_up_suggestions": ["recommended follow-up actions"],
                "time_management_score": 1-10
            }}
            """
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a productivity and commitment management expert."},
                    {"role": "user", "content": insights_prompt}
                ],
                temperature=0.2
            )
            
            insights = json.loads(response.choices[0].message.content)
            
            return {
                "report_generated_at": datetime.now().isoformat(),
                "summary": {
                    "total_pending_commitments": total_pending,
                    "urgent_commitments": urgent_commitments,
                    "overdue_commitments": len(overdue_items['overdue_commitments']),
                    "overdue_waiting_items": len(overdue_items['overdue_waiting']),
                    "due_today": len(due_today),
                    "due_this_week": len(due_this_week)
                },
                "timeframe_breakdown": {
                    "due_today": due_today,
                    "due_this_week": due_this_week,
                    "due_later": due_later[:10]  # Limit to avoid too much data
                },
                "overdue_items": overdue_items,
                "ai_insights": insights,
                "recommendations": [
                    f"Focus on {len(due_today)} items due today" if due_today else None,
                    f"Plan for {len(due_this_week)} items due this week" if due_this_week else None,
                    f"Follow up on {len(overdue_items['overdue_commitments'])} overdue commitments" if overdue_items['overdue_commitments'] else None,
                    f"Check status of {len(overdue_items['overdue_waiting'])} overdue waiting items" if overdue_items['overdue_waiting'] else None
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to generate commitment report: {e}")
            return {"error": str(e)}
    
    def _calculate_days_remaining(self, deadline_str: Optional[str]) -> Optional[int]:
        """Calculate days remaining until deadline."""
        if not deadline_str:
            return None
        
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            today = datetime.now().date()
            return (deadline - today).days
        except ValueError:
            return None
    
    def _calculate_days_overdue(self, deadline_str: str) -> int:
        """Calculate days overdue."""
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            today = datetime.now().date()
            return (today - deadline).days
        except ValueError:
            return 0
    
    async def get_commitment_stats(self) -> Dict[str, Any]:
        """Get commitment tracking statistics."""
        
        try:
            with sqlite3.connect(self.tracker_db_path) as conn:
                cursor = conn.cursor()
                
                # Total commitments
                cursor.execute("SELECT COUNT(*) FROM commitments")
                total_commitments = cursor.fetchone()[0]
                
                # Commitments by status
                cursor.execute("""
                    SELECT status, COUNT(*) FROM commitments
                    GROUP BY status
                """)
                status_breakdown = dict(cursor.fetchall())
                
                # Waiting items
                cursor.execute("SELECT COUNT(*) FROM waiting_items")
                total_waiting = cursor.fetchone()[0]
                
                # Recent activity (last 7 days)
                week_ago = (datetime.now() - timedelta(days=7)).isoformat()
                cursor.execute("""
                    SELECT COUNT(*) FROM commitments
                    WHERE created_at >= ?
                """, (week_ago,))
                recent_commitments = cursor.fetchone()[0]
                
                return {
                    "total_commitments": total_commitments,
                    "status_breakdown": status_breakdown,
                    "total_waiting_items": total_waiting,
                    "recent_commitments_7days": recent_commitments,
                    "completion_rate": status_breakdown.get('completed', 0) / max(total_commitments, 1) * 100,
                    "stats_generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to get commitment stats: {e}")
            return {"error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """Get commitment tracker status."""
        return {
            "agent_type": "commitment_tracker",
            "model": self.model,
            "tracker_db_path": str(self.tracker_db_path),
            "status": "ready" if self.tracker_db_path.exists() else "initializing"
        }
    
    async def shutdown(self) -> None:
        """Shutdown the commitment tracker agent."""
        logger.info("Commitment tracker agent shutdown completed")