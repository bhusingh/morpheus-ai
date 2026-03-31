"""morpheus-ai: Stop your AI coding assistant from being lazy."""

__version__ = "0.2.0"

from morpheus_ai.engine import check_hook_input, check_text, load_rules
from morpheus_ai.rules import Rule, Severity, load_pack
from morpheus_ai.violation import Violation

__all__ = [
    "Rule",
    "Severity",
    "Violation",
    "check_hook_input",
    "check_text",
    "load_pack",
    "load_rules",
]
