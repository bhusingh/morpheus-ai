"""Tests for audit logging."""

from morpheus_ai.audit import clear, read_entries, write_entry
from morpheus_ai.rules import Rule, Severity
from morpheus_ai.violation import Violation


def _make_violation(name: str = "test-rule") -> Violation:
    rule = Rule(name=name, severity=Severity.BLOCK, description="Test")
    return Violation(rule=rule, matched_text="match", line=1)


def test_write_and_read(tmp_path):
    path = tmp_path / "audit.log"
    write_entry(
        [_make_violation("rule-a")],
        source="stdin",
        pack="strict",
        input_bytes=100,
        rules_count=18,
        path=path,
    )
    entries = read_entries(path=path)
    assert len(entries) == 1
    e = entries[0]
    assert e["source"] == "stdin"
    assert e["pack"] == "strict"
    assert e["input_bytes"] == 100
    assert e["rules"] == 18
    assert e["violations"] == 1
    assert e["blocked"] is True
    assert "rule-a" in e["matched_rules"]
    assert "ts" in e


def test_write_no_violations(tmp_path):
    path = tmp_path / "audit.log"
    write_entry(
        [],
        source="stdin",
        pack="light",
        input_bytes=50,
        rules_count=6,
        path=path,
    )
    entries = read_entries(path=path)
    assert len(entries) == 1
    assert entries[0]["blocked"] is False
    assert entries[0]["violations"] == 0
    assert entries[0]["matched_rules"] == []


def test_multiple_entries(tmp_path):
    path = tmp_path / "audit.log"
    for i in range(5):
        write_entry(
            [],
            source="stdin",
            pack="standard",
            input_bytes=10,
            rules_count=12,
            path=path,
        )
    entries = read_entries(path=path)
    assert len(entries) == 5


def test_tail(tmp_path):
    path = tmp_path / "audit.log"
    for i in range(10):
        write_entry(
            [],
            source="stdin",
            pack="standard",
            input_bytes=i,
            rules_count=12,
            path=path,
        )
    entries = read_entries(path=path, tail=3)
    assert len(entries) == 3
    assert entries[0]["input_bytes"] == 7


def test_clear(tmp_path):
    path = tmp_path / "audit.log"
    write_entry(
        [],
        source="stdin",
        pack="light",
        input_bytes=10,
        rules_count=6,
        path=path,
    )
    assert path.exists()
    clear(path=path)
    assert not path.exists()
    assert read_entries(path=path) == []


def test_read_missing_file(tmp_path):
    path = tmp_path / "nonexistent.log"
    assert read_entries(path=path) == []


def test_read_corrupt_lines(tmp_path):
    path = tmp_path / "audit.log"
    path.write_text('{"valid": true}\nnot json\n{"also": "valid"}\n')
    entries = read_entries(path=path)
    assert len(entries) == 2


def test_deduplicates_rule_names(tmp_path):
    path = tmp_path / "audit.log"
    write_entry(
        [_make_violation("rule-a"), _make_violation("rule-a")],
        source="stdin",
        pack="strict",
        input_bytes=100,
        rules_count=18,
        path=path,
    )
    entries = read_entries(path=path)
    assert entries[0]["matched_rules"] == ["rule-a"]


def test_creates_parent_dirs(tmp_path):
    path = tmp_path / "deep" / "nested" / "audit.log"
    write_entry(
        [],
        source="stdin",
        pack="light",
        input_bytes=10,
        rules_count=6,
        path=path,
    )
    assert path.exists()
