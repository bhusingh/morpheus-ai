"""Load .morpheus-ai.yaml project config."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_FILENAME = ".morpheus-ai.yaml"


@dataclass(frozen=True)
class Config:
    pack: str = "standard"
    custom_rules: str | None = None
    instructions: list[str] | None = None
    fmt: str = "text"
    stats_enabled: bool = True
    audit_enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        rules = data.get("rules", {})
        output = data.get("output", {})
        stats = data.get("stats", {})
        audit = data.get("audit", {})
        instructions = data.get("instructions")
        if isinstance(instructions, str):
            instructions = [instructions]
        return cls(
            pack=rules.get("pack", "standard"),
            custom_rules=rules.get("custom"),
            instructions=instructions,
            fmt=output.get("format", "text"),
            stats_enabled=stats.get("enabled", True),
            audit_enabled=audit.get("enabled", True),
        )


def find_config(start: Path | None = None) -> Path | None:
    """Walk up from start (or cwd) looking for .morpheus-ai.yaml."""
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def load_config(path: Path | None = None) -> Config:
    if path is None:
        path = find_config()
    if path is None or not path.is_file():
        return Config()
    try:
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            return Config()
        return Config.from_dict(data)
    except (yaml.YAMLError, OSError):
        return Config()
