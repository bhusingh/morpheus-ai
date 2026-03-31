"""Rule model — YAML parsing and regex pattern compilation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class Severity(Enum):
    BLOCK = "BLOCK"
    WARN = "WARN"
    INFO = "INFO"


@dataclass(frozen=True)
class Rule:
    name: str
    severity: Severity
    description: str
    patterns: tuple[re.Pattern[str], ...] = ()
    instruction_check: bool = False
    multiline: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        if "name" not in data or "severity" not in data:
            raise ValueError(f"Rule missing required field 'name' or 'severity': {data}")
        severity = Severity(data["severity"])
        patterns = tuple(re.compile(p) for p in data.get("patterns", []))
        return cls(
            name=data["name"],
            severity=severity,
            description=data.get("description", ""),
            patterns=patterns,
            instruction_check=data.get("instruction_check", False),
            multiline=data.get("multiline", False),
        )


def load_rules_from_yaml(path: Path) -> list[Rule]:
    text = path.read_text()
    data = yaml.safe_load(text)
    if not data or "rules" not in data:
        return []
    return [Rule.from_dict(r) for r in data["rules"]]


_VALID_PACK_NAME = re.compile(r"^[a-zA-Z0-9_-]+$")


def load_pack(name: str) -> list[Rule]:
    if not _VALID_PACK_NAME.match(name):
        raise ValueError(f"Invalid pack name '{name}': must be alphanumeric, hyphens, underscores")
    pack_dir = Path(__file__).parent / "packs"
    path = pack_dir / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Rule pack '{name}' not found at {path}")
    return load_rules_from_yaml(path)
