"""Tests for output formatting."""

import io
import json

from ai_watchdog.reporter import format_github, format_json, format_text, report
from ai_watchdog.rules import Rule, Severity
from ai_watchdog.violation import Violation

RULE = Rule(
    name="test-rule",
    severity=Severity.BLOCK,
    description="Test rule",
)

VIOLATION = Violation(rule=RULE, matched_text="skip it for now", line=5)


def test_format_text_empty():
    assert format_text([]) == ""


def test_format_text():
    output = format_text([VIOLATION])
    assert "[BLOCK]" in output
    assert "test-rule" in output
    assert "line 5" in output
    assert "skip it for now" in output


def test_format_text_sanitizes_ansi():
    v = Violation(rule=RULE, matched_text="\x1b[31mred text\x1b[0m", line=1)
    output = format_text([v])
    assert "\x1b" not in output
    assert "red text" in output


def test_format_json():
    output = format_json([VIOLATION])
    data = json.loads(output)
    assert len(data) == 1
    assert data[0]["rule"] == "test-rule"
    assert data[0]["severity"] == "BLOCK"
    assert data[0]["line"] == 5


def test_format_json_empty():
    output = format_json([])
    assert json.loads(output) == []


def test_format_github():
    output = format_github([VIOLATION])
    assert "::error" in output
    assert "test-rule" in output


def test_format_github_warn():
    warn_rule = Rule(name="warn-rule", severity=Severity.WARN, description="Warn")
    v = Violation(rule=warn_rule, matched_text="maybe", line=1)
    output = format_github([v])
    assert "::warning" in output


def test_format_github_info_uses_notice():
    info_rule = Rule(name="info-rule", severity=Severity.INFO, description="Info")
    v = Violation(rule=info_rule, matched_text="perhaps", line=1)
    output = format_github([v])
    assert "::notice" in output
    assert "::warning" not in output


def test_format_github_empty():
    assert format_github([]) == ""


def test_format_github_escapes_colons():
    rule = Rule(name="test", severity=Severity.BLOCK, description="foo :: bar")
    v = Violation(rule=rule, matched_text="test", line=1)
    output = format_github([v])
    assert "foo :: bar" not in output
    assert "foo :  bar" in output


def test_report_text():
    buf = io.StringIO()
    report([VIOLATION], fmt="text", output=buf)
    assert "test-rule" in buf.getvalue()


def test_report_json():
    buf = io.StringIO()
    report([VIOLATION], fmt="json", output=buf)
    data = json.loads(buf.getvalue())
    assert data[0]["rule"] == "test-rule"


def test_report_github():
    buf = io.StringIO()
    report([VIOLATION], fmt="github", output=buf)
    assert "::error" in buf.getvalue()


def test_report_empty_no_output():
    buf = io.StringIO()
    report([], fmt="text", output=buf)
    assert buf.getvalue() == ""
