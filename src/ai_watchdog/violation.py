"""Violation model with severity levels."""

from __future__ import annotations

from dataclasses import dataclass

from ai_watchdog.rules import Rule, Severity


@dataclass(frozen=True)
class Violation:
    rule: Rule
    matched_text: str
    line: int | None = None

    @property
    def severity(self) -> Severity:
        return self.rule.severity

    @property
    def is_blocking(self) -> bool:
        return self.severity == Severity.BLOCK
