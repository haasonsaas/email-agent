"""Multi-agent orchestration for Email Agent."""

from .categorizer import CategorizerAgent
from .collector import CollectorAgent
from .crew import EmailAgentCrew
from .summarizer import SummarizerAgent

__all__ = [
    "EmailAgentCrew",
    "CollectorAgent",
    "CategorizerAgent",
    "SummarizerAgent",
]
