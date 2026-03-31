"""ai-watchdog: Stop your AI coding assistant from being lazy."""

__version__ = "0.1.0"

from ai_watchdog.engine import check_hook_input, check_text, load_rules
from ai_watchdog.rules import Rule, Severity, load_pack
from ai_watchdog.violation import Violation

__all__ = [
    "Rule",
    "Severity",
    "Violation",
    "check_hook_input",
    "check_text",
    "load_pack",
    "load_rules",
]
