"""Audit log — local, append-only record of every check."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from morpheus_ai.violation import Violation

_MAX_LOG_BYTES = 5_000_000  # 5 MB cap, oldest entries trimmed


def _default_audit_path() -> Path:
    try:
        return Path.home() / ".morpheus-ai" / "audit.log"
    except RuntimeError:
        import tempfile
        return Path(tempfile.gettempdir()) / ".morpheus-ai" / "audit.log"


DEFAULT_AUDIT_PATH = _default_audit_path()


def write_entry(
    violations: list[Violation],
    source: str,
    pack: str,
    input_bytes: int,
    rules_count: int,
    tool_name: str = "",
    speculation: bool = False,
    path: Path | None = None,
) -> None:
    """Append one audit entry. Never raises."""
    try:
        path = path or DEFAULT_AUDIT_PATH
        blocked = any(v.is_blocking for v in violations)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "source": source,
            "pack": pack,
            "input_bytes": input_bytes,
            "rules": rules_count,
            "violations": len(violations),
            "blocked": blocked,
            "matched_rules": sorted({v.rule.name for v in violations}),
        }
        if tool_name:
            entry["tool"] = tool_name
        if speculation:
            entry["speculation"] = True
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        _trim_if_needed(path)
    except Exception:
        pass


def _trim_if_needed(path: Path) -> None:
    """Keep log under size cap by dropping oldest entries."""
    try:
        if path.stat().st_size <= _MAX_LOG_BYTES:
            return
        lines = path.read_text().splitlines()
        half = len(lines) // 2
        path.write_text("\n".join(lines[half:]) + "\n")
    except Exception:
        pass


def read_entries(
    path: Path | None = None,
    tail: int | None = None,
) -> list[dict]:
    """Read audit entries, optionally last N."""
    path = path or DEFAULT_AUDIT_PATH
    if not path.exists():
        return []
    try:
        lines = path.read_text().strip().splitlines()
        if tail is not None:
            lines = lines[-tail:]
        entries = []
        for line in lines:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries
    except OSError:
        return []


def clear(path: Path | None = None) -> None:
    """Delete the audit log."""
    try:
        path = path or DEFAULT_AUDIT_PATH
        if path.exists():
            path.unlink()
    except OSError:
        pass
