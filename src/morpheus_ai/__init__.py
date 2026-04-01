"""morpheus-ai: Stop your AI coding assistant from being lazy."""

__version__ = "0.3.0"

from morpheus_ai.engine import (
    HookPayload,
    check_hook_input,
    check_text,
    load_rules,
    parse_hook_payload,
)
from morpheus_ai.rules import Rule, Severity, load_pack
from morpheus_ai.violation import Violation

__all__ = [
    "HookPayload",
    "Rule",
    "Severity",
    "Violation",
    "check_hook_input",
    "check_text",
    "load_pack",
    "load_rules",
    "parse_hook_payload",
]
