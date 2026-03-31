"""Tests for stats persistence, corruption tolerance, and recording."""

from morpheus_ai.rules import Rule, Severity
from morpheus_ai.stats import Stats
from morpheus_ai.violation import Violation


def _make_violation(name: str = "test-rule", severity: Severity = Severity.BLOCK) -> Violation:
    rule = Rule(name=name, severity=severity, description="Test")
    return Violation(rule=rule, matched_text="match", line=1)


def test_load_missing_file(tmp_path):
    path = tmp_path / "stats.json"
    s = Stats.load(path)
    assert s.total_checks == 0


def test_save_and_load(tmp_path):
    path = tmp_path / "stats.json"
    s = Stats()
    s.total_checks = 5
    s.total_violations = 2
    s.save(path)

    loaded = Stats.load(path)
    assert loaded.total_checks == 5
    assert loaded.total_violations == 2


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "deep" / "nested" / "stats.json"
    s = Stats()
    s.save(path)
    assert path.exists()


def test_load_corrupt_json(tmp_path):
    path = tmp_path / "stats.json"
    path.write_text("{truncated")
    s = Stats.load(path)
    assert s.total_checks == 0


def test_load_empty_file(tmp_path):
    path = tmp_path / "stats.json"
    path.write_text("")
    s = Stats.load(path)
    assert s.total_checks == 0


def test_load_non_dict_json(tmp_path):
    path = tmp_path / "stats.json"
    path.write_text('"just a string"')
    s = Stats.load(path)
    assert s.total_checks == 0


def test_record_increments_counters():
    s = Stats()
    violations = [
        _make_violation("rule-a", Severity.BLOCK),
        _make_violation("rule-b", Severity.WARN),
    ]
    s.record(violations)

    assert s.total_checks == 1
    assert s.total_violations == 2
    assert s.by_rule["rule-a"] == 1
    assert s.by_rule["rule-b"] == 1
    assert s.by_severity["BLOCK"] == 1
    assert s.by_severity["WARN"] == 1
    assert s.last_updated != ""


def test_record_empty_violations():
    s = Stats()
    s.record([])
    assert s.total_checks == 1
    assert s.total_violations == 0


def test_record_multiple_calls():
    s = Stats()
    s.record([_make_violation()])
    s.record([_make_violation(), _make_violation()])
    assert s.total_checks == 2
    assert s.total_violations == 3
