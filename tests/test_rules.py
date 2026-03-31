"""Tests for rule loading and pattern compilation."""

from pathlib import Path

import pytest

from ai_watchdog.rules import Rule, Severity, load_pack, load_rules_from_yaml


def test_load_strict_pack():
    rules = load_pack("strict")
    assert len(rules) >= 15
    names = [r.name for r in rules]
    assert "no-scope-reduction" in names
    assert "no-option-offering" in names
    assert "no-deferral" in names
    assert "no-test-skipping" in names
    assert "no-placeholder-code" in names
    assert "no-user-delegation" in names
    assert "no-simplified-delivery" in names


def test_load_standard_pack():
    rules = load_pack("standard")
    assert len(rules) >= 11


def test_load_light_pack():
    rules = load_pack("light")
    assert len(rules) >= 6
    assert len(rules) < len(load_pack("strict"))


def test_load_nonexistent_pack():
    with pytest.raises(FileNotFoundError):
        load_pack("nonexistent")


def test_load_invalid_pack_name():
    with pytest.raises(ValueError, match="Invalid pack name"):
        load_pack("../../etc/passwd")


def test_load_pack_path_traversal():
    with pytest.raises(ValueError, match="Invalid pack name"):
        load_pack("../secrets")


def test_rule_from_dict():
    data = {
        "name": "test-rule",
        "severity": "BLOCK",
        "description": "A test rule",
        "patterns": ["(?i)\\bskip\\b"],
    }
    rule = Rule.from_dict(data)
    assert rule.name == "test-rule"
    assert rule.severity == Severity.BLOCK
    assert len(rule.patterns) == 1
    assert rule.patterns[0].search("let's skip that")


def test_rule_from_dict_missing_name():
    with pytest.raises(ValueError, match="missing required field"):
        Rule.from_dict({"severity": "BLOCK"})


def test_rule_from_dict_missing_severity():
    with pytest.raises(ValueError, match="missing required field"):
        Rule.from_dict({"name": "test"})


def test_rule_multiline_flag():
    data = {
        "name": "multi",
        "severity": "WARN",
        "description": "Multiline rule",
        "multiline": True,
        "patterns": ["step 1[\\s\\S]*step 2"],
    }
    rule = Rule.from_dict(data)
    assert rule.multiline is True


def test_rule_instruction_check():
    data = {
        "name": "instruction-compliance",
        "severity": "BLOCK",
        "description": "Check instructions",
        "instruction_check": True,
        "patterns": [],
    }
    rule = Rule.from_dict(data)
    assert rule.instruction_check is True
    assert rule.patterns == ()


def test_rule_patterns_are_tuple():
    data = {
        "name": "test",
        "severity": "WARN",
        "description": "Test",
        "patterns": ["(?i)\\bfoo\\b"],
    }
    rule = Rule.from_dict(data)
    assert isinstance(rule.patterns, tuple)


def test_load_rules_from_yaml(tmp_path: Path):
    yaml_file = tmp_path / "custom.yaml"
    yaml_file.write_text(
        "rules:\n"
        "  - name: custom-rule\n"
        "    severity: WARN\n"
        "    description: Custom\n"
        "    patterns:\n"
        '      - "(?i)\\\\bfoo\\\\b"\n'
    )
    rules = load_rules_from_yaml(yaml_file)
    assert len(rules) == 1
    assert rules[0].name == "custom-rule"
    assert rules[0].severity == Severity.WARN


def test_load_empty_yaml(tmp_path: Path):
    yaml_file = tmp_path / "empty.yaml"
    yaml_file.write_text("")
    assert load_rules_from_yaml(yaml_file) == []
