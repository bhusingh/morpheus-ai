"""Core rules engine — loads rules, runs checks."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from morpheus_ai.rules import Rule, Severity, load_pack, load_rules_from_yaml
from morpheus_ai.violation import Violation

_MAX_MATCHED_TEXT = 200
_MAX_RECURSION_DEPTH = 50

_DIRECTIVE_RE = re.compile(r"(?i)\b(must|always|never|do not|don't|required)\b")

# Rules that only apply to code written via Write/Edit tools
_CODE_ONLY_RULES = frozenset({
    "no-placeholder-code",
    "no-user-delegation",
})

# Rules that only apply to conversational text (Stop/SubagentStop)
_CONVERSATION_ONLY_RULES = frozenset({
    "no-option-offering",
    "no-premature-confirmation",
    "no-excessive-planning",
    "no-scope-creep-warnings",
    "no-hedging",
    "no-false-blockers",
    "no-cost-scaring",
    "no-false-completion",
})


_TICK_RE = re.compile(r"^\s*<tick>\s*$")


@dataclass(frozen=True)
class HookPayload:
    """Parsed hook payload with structured metadata."""

    text: str
    hook_event: str = ""
    tool_name: str = ""
    tool_output: str = ""
    is_proactive_tick: bool = False
    is_speculation: bool = False


def load_rules(
    pack: str = "standard",
    rules_dir: str | Path | None = None,
) -> list[Rule]:
    rules = load_pack(pack)
    if rules_dir:
        rules_path = Path(rules_dir)
        if rules_path.is_dir():
            for yaml_file in sorted(rules_path.glob("*.yaml")):
                rules.extend(load_rules_from_yaml(yaml_file))
        elif rules_path.is_file():
            rules.extend(load_rules_from_yaml(rules_path))
    return rules


def _extract_strings(obj: object, _depth: int = 0) -> list[str]:
    """Extract all string values from nested dicts/lists with depth limit."""
    if _depth > _MAX_RECURSION_DEPTH:
        return []
    parts: list[str] = []
    if isinstance(obj, str):
        parts.append(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            parts.extend(_extract_strings(value, _depth + 1))
    elif isinstance(obj, list):
        for item in obj:
            parts.extend(_extract_strings(item, _depth + 1))
    return parts


def _truncate(text: str) -> str:
    if len(text) <= _MAX_MATCHED_TEXT:
        return text
    return text[:_MAX_MATCHED_TEXT] + "..."


def check_text(
    text: str,
    rules: list[Rule],
    instructions: list[str] | None = None,
) -> list[Violation]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    violations: list[Violation] = []
    lines = text.splitlines()

    for rule in rules:
        if rule.instruction_check:
            if instructions:
                violations.extend(_check_instructions(text, rule, instructions))
            continue

        for pattern in rule.patterns:
            if rule.multiline:
                match = pattern.search(text)
                if match:
                    line_num = text[:match.start()].count("\n") + 1
                    violations.append(Violation(
                        rule=rule,
                        matched_text=_truncate(match.group(0)),
                        line=line_num,
                    ))
            else:
                for line_num, line in enumerate(lines, start=1):
                    match = pattern.search(line)
                    if match:
                        violations.append(Violation(
                            rule=rule,
                            matched_text=_truncate(match.group(0)),
                            line=line_num,
                        ))
                        break

    return violations


def _check_instructions(
    text: str,
    rule: Rule,
    instructions: list[str],
) -> list[Violation]:
    """Check text against instruction file directives."""
    violations: list[Violation] = []
    for instruction_text in instructions:
        for line in instruction_text.splitlines():
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith("#"):
                continue
            if _DIRECTIVE_RE.search(line_stripped):
                directive = _extract_directive(line_stripped)
                if directive:
                    violation = _check_directive_compliance(text, directive, rule)
                    if violation:
                        violations.append(violation)
    return violations


def _extract_directive(line: str) -> str | None:
    """Extract the actionable part of a directive line."""
    line = re.sub(r"^[\s\-*>]+", "", line)
    line = re.sub(r"^#+\s*", "", line)
    if len(line) < 10 or len(line) > 200:
        return None
    return line


def _check_directive_compliance(
    text: str,
    directive: str,
    rule: Rule,
) -> Violation | None:
    """Check if text violates a 'never' or 'do not' directive."""
    never_match = re.search(
        r"(?i)\b(never|do not|don't|must not|must never)\b\s+(.{5,60})",
        directive,
    )
    if not never_match:
        return None
    forbidden_action = never_match.group(2).strip().rstrip(".")
    words = forbidden_action.split()[:4]
    if len(words) < 2:
        return None
    search_pattern = r"(?i)\b" + r"\b[^\n]{0,30}\b".join(re.escape(w) for w in words) + r"\b"
    try:
        match = re.search(search_pattern, text)
    except re.error:
        return None
    if match:
        return Violation(
            rule=rule,
            matched_text=f"Violates: {directive[:80]}",
            line=None,
        )
    return None


def parse_hook_payload(raw_input: str) -> HookPayload:
    """Parse hook JSON into structured payload.

    Handles all Claude Code hook formats:
    - PreToolUse: {"tool_name": "...", "tool_input": {...}}
    - PostToolUse: {"tool_name": "...", "tool_output": "..."}
    - Stop/SubagentStop: {"last_assistant_message": "..."}
    - Plain text fallback
    """
    try:
        data = json.loads(raw_input)
    except (json.JSONDecodeError, TypeError):
        return HookPayload(text=raw_input)

    if not isinstance(data, dict):
        return HookPayload(text=raw_input)

    hook_event = data.get("hook_event_name", "")
    tool_name = data.get("tool_name", "")

    # Stop / SubagentStop: scan Claude's conversational response
    assistant_msg = data.get("last_assistant_message")
    if assistant_msg and isinstance(assistant_msg, str):
        is_tick = bool(_TICK_RE.match(assistant_msg))
        return HookPayload(
            text=assistant_msg,
            hook_event=hook_event or "Stop",
            tool_name=tool_name,
            is_proactive_tick=is_tick,
        )

    # PostToolUse: scan tool output
    tool_output = data.get("tool_output", "")
    if isinstance(tool_output, dict):
        tool_output = "\n".join(_extract_strings(tool_output))

    # Detect speculative execution
    is_speculation = bool(data.get("is_speculation"))

    # PreToolUse / PostToolUse: scan tool input fields
    tool_input = data.get("tool_input", data)
    text_parts = _extract_strings(tool_input)
    text = "\n".join(text_parts)

    return HookPayload(
        text=text,
        hook_event=hook_event,
        tool_name=tool_name,
        tool_output=str(tool_output) if tool_output else "",
        is_speculation=is_speculation,
    )


def extract_hook_text(raw_input: str) -> str:
    """Extract scannable text from hook JSON. Convenience wrapper."""
    return parse_hook_payload(raw_input).text


def _filter_rules_for_context(
    rules: list[Rule],
    payload: HookPayload,
) -> list[Rule]:
    """Filter rules based on hook context to reduce false positives."""
    if not payload.hook_event:
        return rules

    is_stop = payload.hook_event in ("Stop", "SubagentStop")

    filtered = []
    for rule in rules:
        if is_stop and rule.name in _CODE_ONLY_RULES:
            continue
        if not is_stop and rule.name in _CONVERSATION_ONLY_RULES:
            continue
        filtered.append(rule)
    return filtered


def check_hook_input(
    raw_input: str,
    rules: list[Rule],
    instructions: list[str] | None = None,
) -> list[Violation]:
    payload = parse_hook_payload(raw_input)

    # Skip proactive tick messages (KAIROS autonomous mode)
    if payload.is_proactive_tick:
        return []

    filtered = _filter_rules_for_context(rules, payload)
    violations = check_text(payload.text, filtered, instructions=instructions)

    # PostToolUse: scan tool output for false-completion (skip read-only tools)
    _READ_TOOLS = {"Read", "Glob", "Grep", "ToolSearch", "LSP"}
    if (payload.tool_output
            and payload.hook_event == "PostToolUse"
            and payload.tool_name not in _READ_TOOLS):
        fc_rules = [r for r in rules if r.name == "no-false-completion"]
        violations.extend(check_text(payload.tool_output, fc_rules))

    return violations


def max_severity(violations: list[Violation]) -> Severity | None:
    if not violations:
        return None
    order = {Severity.BLOCK: 0, Severity.WARN: 1, Severity.INFO: 2}
    return min((v.severity for v in violations), key=lambda s: order.get(s, 2))
