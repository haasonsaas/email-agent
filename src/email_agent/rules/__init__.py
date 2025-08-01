"""Email categorization rules engine."""

from .engine import RulesEngine
from .builtin import BuiltinRules
from .processors import RegexRule, DomainRule, SubjectRule, SenderRule, MLRule

__all__ = [
    "RulesEngine",
    "BuiltinRules", 
    "RegexRule",
    "DomainRule",
    "SubjectRule",
    "SenderRule",
    "MLRule",
]