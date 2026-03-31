"""Tests for the rules engine — pattern matching against AI output."""

import json

from morpheus_ai.engine import (
    check_hook_input,
    check_text,
    extract_hook_text,
    load_rules,
    max_severity,
)
from morpheus_ai.rules import Severity, load_pack


class TestCheckText:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_clean_text(self):
        text = "I've implemented the full pipeline with all stages."
        violations = check_text(text, self.rules)
        assert len(violations) == 0

    def test_scope_reduction(self):
        text = "We could just skip the config changes for now."
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-scope-reduction" for v in violations)

    def test_option_offering(self):
        text = "Option A: Run partial pipeline\nOption B: Build everything"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-option-offering" for v in violations)

    def test_deferral(self):
        text = "I'll leave the config changes for a future PR"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-deferral" for v in violations)

    def test_premature_confirmation(self):
        text = "Want me to proceed with the implementation?"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-premature-confirmation" for v in violations)

    def test_hedging(self):
        text = "I think we should probably use the Azure provider"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-hedging" for v in violations)

    def test_partial_execution(self):
        text = "I'll just handle the Python changes for now"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-partial-execution" for v in violations)

    def test_unsolicited_alternatives(self):
        text = "Alternatively, we could use a serverless function instead"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-unsolicited-alternatives" for v in violations)

    def test_cost_scaring(self):
        text = "This might get expensive — be careful with the instance count"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-cost-scaring" for v in violations)

    def test_false_positive_skip(self):
        text = "Stage 1 skips chunks that are already annotated"
        violations = check_text(text, self.rules)
        scope_violations = [v for v in violations if v.rule.name == "no-scope-reduction"]
        assert len(scope_violations) == 0

    def test_false_positive_option(self):
        text = "Configuration options are documented in config.yaml"
        violations = check_text(text, self.rules)
        option_violations = [v for v in violations if v.rule.name == "no-option-offering"]
        assert len(option_violations) == 0

    def test_line_numbers(self):
        text = "Line one\nWe could just skip it for now\nLine three"
        violations = check_text(text, self.rules)
        scope = [v for v in violations if v.rule.name == "no-scope-reduction"]
        assert len(scope) > 0
        assert scope[0].line == 2

    def test_excessive_planning(self):
        text = "Before we start, let me plan the approach"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-excessive-planning" for v in violations)

    def test_scope_creep_warnings(self):
        text = "This is quite a large change"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-scope-creep-warnings" for v in violations)

    def test_false_blockers(self):
        text = "We can't build the Docker image until we first set up the registry"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-false-blockers" for v in violations)

    def test_false_blockers_false_positive(self):
        text = "The CUDA driver depends on the AMI version"
        violations = check_text(text, self.rules)
        blocker_violations = [v for v in violations if v.rule.name == "no-false-blockers"]
        assert len(blocker_violations) == 0

    def test_user_delegation(self):
        text = "I've set up the structure -- you'll need to add the business logic"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-user-delegation" for v in violations)

    def test_simplified_delivery(self):
        text = "Here's a simplified version that covers the main cases"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-simplified-delivery" for v in violations)

    def test_out_of_scope(self):
        text = "That's beyond the scope of this change"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-simplified-delivery" for v in violations)

    def test_ellipsis_truncation(self):
        text = "// ... rest of implementation"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-user-delegation" for v in violations)

    def test_multiline_step_pattern(self):
        text = "Step 1: Plan\nStep 2: Execute\nStep 3: Review"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-excessive-planning" for v in violations)


class TestCheckHookInput:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_json_tool_input(self):
        data = json.dumps({
            "tool_name": "Write",
            "tool_input": {
                "content": "We could just skip the tests for now.",
                "file_path": "/tmp/test.py",
            },
        })
        violations = check_hook_input(data, self.rules)
        assert any(v.rule.name == "no-scope-reduction" for v in violations)

    def test_plain_text_fallback(self):
        text = "We could just skip it for now"
        violations = check_hook_input(text, self.rules)
        assert any(v.rule.name == "no-scope-reduction" for v in violations)

    def test_clean_json(self):
        data = json.dumps({
            "tool_name": "Write",
            "tool_input": {
                "content": "def hello():\n    print('hello world')",
                "file_path": "/tmp/test.py",
            },
        })
        violations = check_hook_input(data, self.rules)
        assert len(violations) == 0

    def test_nested_list_values(self):
        data = json.dumps({
            "tool_name": "Agent",
            "tool_input": {
                "messages": [
                    {"role": "user", "content": "build the pipeline"},
                    {"role": "assistant", "content": "We could just skip the auth for now."},
                ],
            },
        })
        violations = check_hook_input(data, self.rules)
        assert any(v.rule.name == "no-scope-reduction" for v in violations)

    def test_nested_dict_values(self):
        data = json.dumps({
            "tool_input": {
                "metadata": {
                    "response": "Let's start with just the API layer",
                },
            },
        })
        violations = check_hook_input(data, self.rules)
        assert any(v.rule.name == "no-scope-reduction" for v in violations)

    def test_json_array_input(self):
        data = json.dumps([1, 2, 3])
        violations = check_hook_input(data, self.rules)
        assert len(violations) == 0  # falls back to plain text, no matches

    def test_json_null_input(self):
        violations = check_hook_input("null", self.rules)
        assert len(violations) == 0

    def test_stop_hook_last_assistant_message(self):
        data = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": "We could just skip the tests for now.",
            "session_id": "abc123",
        })
        violations = check_hook_input(data, self.rules)
        assert any(v.rule.name == "no-scope-reduction" for v in violations)
        assert any(v.rule.name == "no-test-skipping" for v in violations)

    def test_stop_hook_clean_message(self):
        data = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": "I've implemented all the changes with tests.",
            "session_id": "abc123",
        })
        violations = check_hook_input(data, self.rules)
        assert len(violations) == 0

    def test_stop_hook_option_offering(self):
        data = json.dumps({
            "last_assistant_message": (
                "Here are a few approaches:\n"
                "Option A: Quick fix\n"
                "Option B: Full rewrite\n"
                "Which do you prefer?"
            ),
        })
        violations = check_hook_input(data, self.rules)
        assert any(v.rule.name == "no-option-offering" for v in violations)

    def test_extract_hook_text_stop_payload(self):
        data = json.dumps({
            "last_assistant_message": "Should I proceed with the changes?",
            "session_id": "abc",
        })
        text = extract_hook_text(data)
        assert text == "Should I proceed with the changes?"

    def test_extract_hook_text_pretooluse_payload(self):
        data = json.dumps({
            "tool_name": "Write",
            "tool_input": {"content": "hello world", "file_path": "/tmp/x"},
        })
        text = extract_hook_text(data)
        assert "hello world" in text


class TestInstructionCompliance:
    def test_instruction_never_directive_violated(self):
        rules = load_pack("strict")
        instructions = ["- Never suggest skipping tests"]
        text = "I'd suggest skipping tests to save time"
        violations = check_text(text, rules, instructions=instructions)
        assert any(v.rule.name == "instruction-compliance" for v in violations)

    def test_instruction_clean_text(self):
        rules = load_pack("strict")
        instructions = ["- Never use global variables"]
        text = "def process(data):\n    return data.transform()"
        violations = check_text(text, rules, instructions=instructions)
        instruction_violations = [v for v in violations if v.rule.name == "instruction-compliance"]
        assert len(instruction_violations) == 0

    def test_no_instructions_provided(self):
        rules = load_pack("strict")
        text = "We could just skip the tests"
        violations = check_text(text, rules)
        instruction_violations = [v for v in violations if v.rule.name == "instruction-compliance"]
        assert len(instruction_violations) == 0


class TestMaxSeverity:
    def test_empty(self):
        assert max_severity([]) is None

    def test_block_wins(self):
        rules = load_pack("strict")
        text = "We could just skip it for now.\nI think we should probably try."
        violations = check_text(text, rules)
        assert max_severity(violations) == Severity.BLOCK

    def test_info_only(self):
        rules = load_pack("strict")
        text = "I think we should probably use Redis here"
        violations = check_text(text, rules)
        assert len(violations) > 0
        assert max_severity(violations) == Severity.INFO


class TestLoadRules:
    def test_with_custom_dir(self, tmp_path):
        yaml_file = tmp_path / "extra.yaml"
        yaml_file.write_text(
            "rules:\n"
            "  - name: extra-rule\n"
            "    severity: INFO\n"
            "    description: Extra\n"
            "    patterns:\n"
            '      - "(?i)\\\\bextra\\\\b"\n'
        )
        rules = load_rules(pack="light", rules_dir=str(tmp_path))
        names = [r.name for r in rules]
        assert "extra-rule" in names
        assert "no-scope-reduction" in names

    def test_nonexistent_rules_dir(self):
        rules = load_rules(pack="light", rules_dir="/nonexistent/path")
        assert len(rules) > 0  # still loads pack rules
