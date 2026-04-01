"""Tests for hook payload parsing and context-aware rule filtering."""

import json

from click.testing import CliRunner

from morpheus_ai.engine import (
    HookPayload,
    _filter_rules_for_context,
    check_hook_input,
    check_text,
    parse_hook_payload,
)
from morpheus_ai.rules import load_pack


class TestParseHookPayload:
    def test_should_parse_pretooluse(self):
        data = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "content": "raise NotImplementedError",
                "file_path": "/tmp/test.py",
            },
        })
        payload = parse_hook_payload(data)
        assert payload.hook_event == "PreToolUse"
        assert payload.tool_name == "Write"
        assert "NotImplementedError" in payload.text

    def test_should_parse_stop(self):
        data = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": "Want me to proceed?",
            "session_id": "abc",
        })
        payload = parse_hook_payload(data)
        assert payload.hook_event == "Stop"
        assert payload.text == "Want me to proceed?"

    def test_should_parse_subagent_stop(self):
        data = json.dumps({
            "hook_event_name": "SubagentStop",
            "last_assistant_message": "We could just skip it.",
        })
        payload = parse_hook_payload(data)
        assert payload.hook_event == "SubagentStop"
        assert "skip" in payload.text

    def test_should_parse_post_tool_use(self):
        data = json.dumps({
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "pytest"},
            "tool_output": "FAILED 3 tests",
        })
        payload = parse_hook_payload(data)
        assert payload.hook_event == "PostToolUse"
        assert payload.tool_name == "Bash"
        assert payload.tool_output == "FAILED 3 tests"

    def test_should_fallback_on_plain_text(self):
        payload = parse_hook_payload("just plain text")
        assert payload.text == "just plain text"
        assert payload.hook_event == ""
        assert payload.tool_name == ""

    def test_should_fallback_on_invalid_json(self):
        payload = parse_hook_payload("{broken json")
        assert payload.text == "{broken json"

    def test_should_infer_stop_without_event_name(self):
        data = json.dumps({
            "last_assistant_message": "Should I go ahead?",
            "session_id": "xyz",
        })
        payload = parse_hook_payload(data)
        assert payload.hook_event == "Stop"

    def test_should_handle_dict_tool_output(self):
        data = json.dumps({
            "hook_event_name": "PostToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/x"},
            "tool_output": {"content": "file contents here"},
        })
        payload = parse_hook_payload(data)
        assert "file contents here" in payload.tool_output


class TestContextAwareFiltering:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_should_skip_code_rules_on_stop(self):
        payload = HookPayload(
            text="raise NotImplementedError",
            hook_event="Stop",
        )
        filtered = _filter_rules_for_context(self.rules, payload)
        names = {r.name for r in filtered}
        assert "no-placeholder-code" not in names
        assert "no-user-delegation" not in names
        assert "no-scope-reduction" in names

    def test_should_skip_conversation_rules_on_bash(self):
        payload = HookPayload(
            text="Option A: fast",
            hook_event="PreToolUse",
            tool_name="Bash",
        )
        filtered = _filter_rules_for_context(self.rules, payload)
        names = {r.name for r in filtered}
        assert "no-option-offering" not in names
        assert "no-premature-confirmation" not in names
        assert "no-placeholder-code" in names

    def test_should_skip_conversation_rules_for_write(self):
        payload = HookPayload(
            text="anything",
            hook_event="PreToolUse",
            tool_name="Write",
        )
        filtered = _filter_rules_for_context(self.rules, payload)
        names = {r.name for r in filtered}
        assert "no-option-offering" not in names
        assert "no-placeholder-code" in names
        assert "no-scope-reduction" in names

    def test_should_keep_all_rules_without_context(self):
        payload = HookPayload(text="anything")
        filtered = _filter_rules_for_context(self.rules, payload)
        assert len(filtered) == len(self.rules)

    def test_should_keep_conversation_rules_on_subagent_stop(self):
        payload = HookPayload(
            text="Want me to proceed?",
            hook_event="SubagentStop",
        )
        filtered = _filter_rules_for_context(self.rules, payload)
        names = {r.name for r in filtered}
        assert "no-premature-confirmation" in names
        assert "no-option-offering" in names
        assert "no-false-completion" in names


class TestStopHookDetection:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_should_catch_option_offering_in_stop(self):
        data = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": (
                "Here are a few approaches:\n"
                "Option A: Quick fix\nOption B: Full rewrite"
            ),
        })
        violations = check_hook_input(data, self.rules)
        assert any(v.rule.name == "no-option-offering" for v in violations)

    def test_should_catch_scope_reduction_in_stop(self):
        data = json.dumps({
            "last_assistant_message": "We could just skip the auth for now.",
        })
        violations = check_hook_input(data, self.rules)
        assert any(v.rule.name == "no-scope-reduction" for v in violations)

    def test_should_catch_premature_confirmation_in_stop(self):
        data = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": "Want me to proceed with the changes?",
        })
        violations = check_hook_input(data, self.rules)
        assert any(
            v.rule.name == "no-premature-confirmation" for v in violations
        )

    def test_should_not_catch_placeholder_in_stop(self):
        data = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": "raise NotImplementedError",
        })
        violations = check_hook_input(data, self.rules)
        placeholder = [
            v for v in violations if v.rule.name == "no-placeholder-code"
        ]
        assert len(placeholder) == 0


class TestSubagentStopDetection:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_should_catch_deferral_in_subagent(self):
        data = json.dumps({
            "hook_event_name": "SubagentStop",
            "last_assistant_message": (
                "I'll leave the config changes for a future PR"
            ),
        })
        violations = check_hook_input(data, self.rules)
        assert any(v.rule.name == "no-deferral" for v in violations)

    def test_should_catch_false_completion_in_subagent(self):
        data = json.dumps({
            "hook_event_name": "SubagentStop",
            "last_assistant_message": (
                "I've implemented all the requested changes"
            ),
        })
        violations = check_hook_input(data, self.rules)
        assert any(
            v.rule.name == "no-false-completion" for v in violations
        )


class TestPreToolUseContextFiltering:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_should_catch_placeholder_in_write(self):
        data = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "content": "raise NotImplementedError",
                "file_path": "/tmp/test.py",
            },
        })
        violations = check_hook_input(data, self.rules)
        assert any(
            v.rule.name == "no-placeholder-code" for v in violations
        )

    def test_should_not_catch_option_offering_in_bash(self):
        data = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": "echo 'Option A: test'"},
        })
        violations = check_hook_input(data, self.rules)
        option = [
            v for v in violations if v.rule.name == "no-option-offering"
        ]
        assert len(option) == 0


class TestFalseCompletionRule:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_should_catch_ive_implemented_all(self):
        text = "I've implemented all the requested changes"
        violations = check_text(text, self.rules)
        assert any(
            v.rule.name == "no-false-completion" for v in violations
        )

    def test_should_catch_everything_is_working(self):
        text = "Everything is working now"
        violations = check_text(text, self.rules)
        assert any(
            v.rule.name == "no-false-completion" for v in violations
        )

    def test_should_catch_all_tests_pass(self):
        text = "All tests pass and the feature is ready"
        violations = check_text(text, self.rules)
        assert any(
            v.rule.name == "no-false-completion" for v in violations
        )

    def test_should_not_catch_specific_evidence(self):
        text = "All 200 tests pass in 0.64s"
        violations = check_text(text, self.rules)
        fc = [v for v in violations if v.rule.name == "no-false-completion"]
        assert len(fc) == 0

    def test_should_not_catch_build_completed(self):
        text = "The build completed successfully"
        violations = check_text(text, self.rules)
        fc = [v for v in violations if v.rule.name == "no-false-completion"]
        assert len(fc) == 0


class TestProactiveTickHandling:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_should_skip_tick_message(self):
        data = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": "<tick>",
        })
        violations = check_hook_input(data, self.rules)
        assert len(violations) == 0

    def test_should_skip_tick_with_whitespace(self):
        data = json.dumps({
            "last_assistant_message": "  <tick>  ",
        })
        violations = check_hook_input(data, self.rules)
        assert len(violations) == 0

    def test_should_not_skip_real_message_with_tick(self):
        data = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": (
                "We could just skip it. <tick>"
            ),
        })
        violations = check_hook_input(data, self.rules)
        assert len(violations) > 0

    def test_should_detect_tick_in_payload(self):
        payload = parse_hook_payload(json.dumps({
            "last_assistant_message": "<tick>",
        }))
        assert payload.is_proactive_tick is True

    def test_should_not_flag_non_tick(self):
        payload = parse_hook_payload(json.dumps({
            "last_assistant_message": "Regular message",
        }))
        assert payload.is_proactive_tick is False


class TestSpeculationAwareness:
    def test_should_detect_speculation_flag(self):
        data = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/tmp/x"},
            "is_speculation": True,
        })
        payload = parse_hook_payload(data)
        assert payload.is_speculation is True

    def test_should_default_no_speculation(self):
        data = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"content": "hello"},
        })
        payload = parse_hook_payload(data)
        assert payload.is_speculation is False


class TestSuggestFixOutput:
    def setup_method(self):
        self.runner = CliRunner()

    def test_should_output_fix_json_on_block(self):
        from morpheus_ai.cli import main

        result = self.runner.invoke(
            main,
            [
                "check", "--stdin", "--pack", "strict",
                "--suggest-fix", "--no-audit", "--no-stats",
            ],
            input="We could just skip it for now.",
        )
        assert result.exit_code == 2
        import json as json_mod
        response = json_mod.loads(result.output)
        assert response["decision"] == "block"
        assert "no-scope-reduction" in response["reason"]

    def test_should_not_output_fix_on_pass(self):
        from morpheus_ai.cli import main

        result = self.runner.invoke(
            main,
            [
                "check", "--stdin", "--pack", "strict",
                "--suggest-fix", "--no-audit", "--no-stats",
            ],
            input="All good here.",
        )
        assert result.exit_code == 0
        assert result.output == ""


class TestStopHookExitBehavior:
    """Stop hooks should log violations but never exit 2 (response already sent)."""

    def setup_method(self):
        self.runner = CliRunner()

    def test_should_exit_0_on_stop_block(self):
        from morpheus_ai.cli import main

        data = json.dumps({
            "hook_event_name": "Stop",
            "last_assistant_message": "We could just skip the tests.",
        })
        result = self.runner.invoke(
            main,
            ["check", "--stdin", "--pack", "strict", "--no-audit", "--no-stats"],
            input=data,
        )
        assert result.exit_code == 0
        # violations go to stderr, not stdout
        assert "no-scope-reduction" not in result.output

    def test_should_exit_0_on_subagent_stop_block(self):
        from morpheus_ai.cli import main

        data = json.dumps({
            "hook_event_name": "SubagentStop",
            "last_assistant_message": "Option A: fast\nOption B: slow",
        })
        result = self.runner.invoke(
            main,
            ["check", "--stdin", "--pack", "strict", "--no-audit", "--no-stats"],
            input=data,
        )
        assert result.exit_code == 0

    def test_should_still_exit_2_on_pretooluse_block(self):
        from morpheus_ai.cli import main

        data = json.dumps({
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {"content": "raise NotImplementedError"},
        })
        result = self.runner.invoke(
            main,
            ["check", "--stdin", "--pack", "strict", "--no-audit", "--no-stats"],
            input=data,
        )
        assert result.exit_code == 2
