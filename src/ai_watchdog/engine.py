"""Core rules engine — loads rules, runs checks."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ai_watchdog.rules import Rule, Severity, load_pack, load_rules_from_yaml
from ai_watchdog.violation import Violation

_MAX_MATCHED_TEXT = 200
_MAX_RECURSION_DEPTH = 50

_DIRECTIVE_RE = re.compile(r"(?i)\b(must|always|never|do not|don't|required)\b")


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


def check_hook_input(
    raw_input: str,
    rules: list[Rule],
    instructions: list[str] | None = None,
) -> list[Violation]:
    try:
        data = json.loads(raw_input)
    except (json.JSONDecodeError, TypeError):
        return check_text(raw_input, rules, instructions=instructions)

    if not isinstance(data, dict):
        return check_text(raw_input, rules, instructions=instructions)

    tool_input = data.get("tool_input", data)
    text_parts = _extract_strings(tool_input)
    combined = "\n".join(text_parts)
    return check_text(combined, rules, instructions=instructions)


def max_severity(violations: list[Violation]) -> Severity | None:
    if not violations:
        return None
    order = {Severity.BLOCK: 0, Severity.WARN: 1, Severity.INFO: 2}
    return min((v.severity for v in violations), key=lambda s: order.get(s, 2))
