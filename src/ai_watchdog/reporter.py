"""Output formatting — text, JSON, GitHub annotations."""

from __future__ import annotations

import json
import re
import sys
from typing import TextIO

from ai_watchdog.violation import Violation

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_GITHUB_SEVERITY = {"BLOCK": "error", "WARN": "warning", "INFO": "notice"}


def _sanitize(text: str) -> str:
    return _ANSI_RE.sub("", text)


def format_text(violations: list[Violation]) -> str:
    if not violations:
        return ""
    lines: list[str] = []
    for v in violations:
        prefix = f"[{v.severity.value}]"
        loc = f" (line {v.line})" if v.line else ""
        lines.append(f"{prefix} {v.rule.name}{loc}: {v.rule.description}")
        lines.append(f"  matched: \"{_sanitize(v.matched_text)}\"")
    return "\n".join(lines)


def format_json(violations: list[Violation]) -> str:
    items = [
        {
            "rule": v.rule.name,
            "severity": v.severity.value,
            "description": v.rule.description,
            "matched_text": _sanitize(v.matched_text),
            "line": v.line,
        }
        for v in violations
    ]
    return json.dumps(items, indent=2)


def format_github(violations: list[Violation], file: str = "input") -> str:
    lines: list[str] = []
    for v in violations:
        level = _GITHUB_SEVERITY.get(v.severity.value, "notice")
        line = v.line or 1
        desc = v.rule.description.replace("::", ": ")
        name = v.rule.name.replace("::", ": ")
        lines.append(f"::{level} file={file},line={line}::{name}: {desc}")
    return "\n".join(lines)


def report(
    violations: list[Violation],
    fmt: str = "text",
    output: TextIO = sys.stderr,
) -> None:
    if fmt == "json":
        text = format_json(violations)
    elif fmt == "github":
        text = format_github(violations)
    else:
        text = format_text(violations)
    if text:
        print(text, file=output)
