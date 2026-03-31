"""Violation tracking and reporting."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from morpheus_ai.violation import Violation


def _default_stats_path() -> Path:
    try:
        return Path.home() / ".morpheus-ai" / "stats.json"
    except RuntimeError:
        import tempfile
        return Path(tempfile.gettempdir()) / ".morpheus-ai" / "stats.json"


DEFAULT_STATS_PATH = _default_stats_path()


@dataclass
class Stats:
    total_checks: int = 0
    total_violations: int = 0
    by_rule: Counter[str] = field(default_factory=Counter)
    by_severity: Counter[str] = field(default_factory=Counter)
    last_updated: str = ""

    def record(self, violations: list[Violation]) -> None:
        self.total_checks += 1
        self.total_violations += len(violations)
        for v in violations:
            self.by_rule[v.rule.name] += 1
            self.by_severity[v.severity.value] += 1
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "total_checks": self.total_checks,
            "total_violations": self.total_violations,
            "by_rule": dict(self.by_rule),
            "by_severity": dict(self.by_severity),
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Stats:
        s = cls()
        s.total_checks = data.get("total_checks", 0)
        s.total_violations = data.get("total_violations", 0)
        s.by_rule = Counter(data.get("by_rule", {}))
        s.by_severity = Counter(data.get("by_severity", {}))
        s.last_updated = data.get("last_updated", "")
        return s

    def save(self, path: Path = DEFAULT_STATS_PATH) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path = DEFAULT_STATS_PATH) -> Stats:
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text())
            if not isinstance(data, dict):
                return cls()
            return cls.from_dict(data)
        except (json.JSONDecodeError, ValueError, TypeError, OSError):
            return cls()
