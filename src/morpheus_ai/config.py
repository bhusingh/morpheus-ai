"""Load .morpheus-ai.yaml project config."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

CONFIG_FILENAME = ".morpheus-ai.yaml"

# Instruction files auto-discovered from AI coding tools
_INSTRUCTION_FILES = [
    "CLAUDE.md",
    ".cursorrules",
    ".cursor/rules",
    ".github/copilot-instructions.md",
    ".windsurfrules",
    ".clinerules",
]


@dataclass(frozen=True)
class Config:
    pack: str = "standard"
    custom_rules: str | None = None
    instructions: list[str] | None = None
    fmt: str = "text"
    stats_enabled: bool = True
    audit_enabled: bool = True
    auto_instructions: bool = True
    config_dir: Path | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        rules = data.get("rules", {})
        output = data.get("output", {})
        stats = data.get("stats", {})
        audit = data.get("audit", {})
        instructions = data.get("instructions")
        if isinstance(instructions, str):
            instructions = [instructions]
        instr_cfg = data.get("instructions_config", {})
        return cls(
            pack=rules.get("pack", "standard"),
            custom_rules=rules.get("custom"),
            instructions=instructions,
            fmt=output.get("format", "text"),
            stats_enabled=stats.get("enabled", True),
            audit_enabled=audit.get("enabled", True),
            auto_instructions=instr_cfg.get("auto_discover", True),
        )


def find_config(start: Path | None = None) -> Path | None:
    """Walk up from start (or cwd) looking for .morpheus-ai.yaml."""
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        candidate = directory / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    return None


def discover_instruction_files(start: Path | None = None) -> list[str]:
    """Find instruction files from AI coding tools in the project."""
    cwd = (start or Path.cwd()).resolve()
    found: list[str] = []
    for name in _INSTRUCTION_FILES:
        candidate = cwd / name
        try:
            if candidate.is_file() and candidate.stat().st_size <= _MAX_INSTRUCTION_BYTES:
                found.append(str(candidate))
        except OSError:
            continue
    return found


_MAX_INSTRUCTION_BYTES = 500_000  # 500 KB cap per instruction file


def load_config(path: Path | None = None) -> Config:
    if path is None:
        path = find_config()
    if path is None or not path.is_file():
        return Config()
    try:
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            return Config()
        cfg = Config.from_dict(data)
        return Config(
            pack=cfg.pack,
            custom_rules=cfg.custom_rules,
            instructions=cfg.instructions,
            fmt=cfg.fmt,
            stats_enabled=cfg.stats_enabled,
            audit_enabled=cfg.audit_enabled,
            auto_instructions=cfg.auto_instructions,
            config_dir=path.parent,
        )
    except (yaml.YAMLError, OSError):
        return Config()
