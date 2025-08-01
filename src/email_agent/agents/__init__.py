"""Multi-agent orchestration for Email Agent."""

# from .crew import EmailAgentCrew  # Optional crew-ai dependency
from .collector import CollectorAgent
from .categorizer import CategorizerAgent  
from .summarizer import SummarizerAgent

__all__ = [
    # "EmailAgentCrew",  # Optional 
    "CollectorAgent",
    "CategorizerAgent", 
    "SummarizerAgent",
]