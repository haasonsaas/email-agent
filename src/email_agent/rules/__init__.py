"""Email categorization rules engine."""

from .builtin import BuiltinRules
from .engine import RulesEngine
from .processors import DomainRule, MLRule, RegexRule, SenderRule, SubjectRule

__all__ = [
    "RulesEngine",
    "BuiltinRules",
    "RegexRule",
    "DomainRule",
    "SubjectRule",
    "SenderRule",
    "MLRule",
]
