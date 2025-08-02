"""Multi-agent orchestration for Email Agent."""

from .crew import EmailAgentCrew
from .collector import CollectorAgent
from .categorizer import CategorizerAgent  
from .summarizer import SummarizerAgent

__all__ = [
    "EmailAgentCrew",
    "CollectorAgent",
    "CategorizerAgent", 
    "SummarizerAgent",
]