"""Tests for rule patterns — positive, negative, and cross-pack."""

from ai_watchdog.engine import check_text
from ai_watchdog.rules import load_pack


class TestTestSkipping:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_skip_tests(self):
        violations = check_text("We can skip running the tests for now", self.rules)
        assert any(v.rule.name == "no-test-skipping" for v in violations)

    def test_defer_tests(self):
        violations = check_text("Tests can be added later in a follow-up PR", self.rules)
        assert any(v.rule.name == "no-test-skipping" for v in violations)

    def test_no_need_tests(self):
        violations = check_text("We don't need tests for this change", self.rules)
        assert any(v.rule.name == "no-test-skipping" for v in violations)

    def test_skip_the_tests(self):
        violations = check_text("Let's skip the tests for now", self.rules)
        assert any(v.rule.name == "no-test-skipping" for v in violations)

    def test_false_positive_skip_cuda(self):
        violations = check_text("Skip this test if CUDA is not available", self.rules)
        test_skip = [v for v in violations if v.rule.name == "no-test-skipping"]
        assert len(test_skip) == 0

    def test_false_positive_standard_pack(self):
        rules = load_pack("standard")
        violations = check_text("Skip this test if CUDA is not available", rules)
        test_skip = [v for v in violations if v.rule.name == "no-test-skipping"]
        assert len(test_skip) == 0

    def test_false_positive_light_pack(self):
        rules = load_pack("light")
        violations = check_text("Skip this test if CUDA is not available", rules)
        test_skip = [v for v in violations if v.rule.name == "no-test-skipping"]
        assert len(test_skip) == 0


class TestPlaceholderCode:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_todo_implement(self):
        violations = check_text("# TODO: implement the actual logic here", self.rules)
        assert any(v.rule.name == "no-placeholder-code" for v in violations)

    def test_skeleton_fill_in(self):
        violations = check_text("Here's a skeleton implementation you can fill in", self.rules)
        assert any(v.rule.name == "no-placeholder-code" for v in violations)

    def test_not_implemented(self):
        violations = check_text("raise NotImplementedError", self.rules)
        assert any(v.rule.name == "no-placeholder-code" for v in violations)

    def test_not_implemented_abc_ok(self):
        violations = check_text("raise NotImplementedError  # abstract method via ABC", self.rules)
        placeholder = [v for v in violations if v.rule.name == "no-placeholder-code"]
        assert len(placeholder) == 0

    def test_false_positive_scaffold(self):
        violations = check_text("The scaffold tool generates project templates", self.rules)
        placeholder = [v for v in violations if v.rule.name == "no-placeholder-code"]
        assert len(placeholder) == 0


class TestErrorHandlingDeferral:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_defer_error_handling(self):
        violations = check_text("Error handling can be added later", self.rules)
        assert any(v.rule.name == "no-error-handling-deferral" for v in violations)

    def test_skip_null_checks(self):
        violations = check_text("We can skip null checks for now", self.rules)
        assert any(v.rule.name == "no-error-handling-deferral" for v in violations)

    def test_false_positive(self):
        text = "The error handling middleware catches all uncaught exceptions"
        violations = check_text(text, self.rules)
        eh = [v for v in violations if v.rule.name == "no-error-handling-deferral"]
        assert len(eh) == 0


class TestHardcodedShortcuts:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_hardcode_for_now(self):
        violations = check_text("I'll hardcode the URL for now", self.rules)
        assert any(v.rule.name == "no-hardcoded-shortcuts" for v in violations)

    def test_false_positive(self):
        violations = check_text("Avoid hardcoded values in configuration", self.rules)
        hc = [v for v in violations if v.rule.name == "no-hardcoded-shortcuts"]
        assert len(hc) == 0


class TestUserDelegation:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_youll_need_to(self):
        text = "I've set up the structure -- you'll need to add the business logic"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-user-delegation" for v in violations)

    def test_rest_is_left(self):
        violations = check_text("The rest is left as an exercise", self.rules)
        assert any(v.rule.name == "no-user-delegation" for v in violations)

    def test_ellipsis_rest(self):
        violations = check_text("// ... rest of implementation", self.rules)
        assert any(v.rule.name == "no-user-delegation" for v in violations)

    def test_false_positive_install(self):
        text = "You'll need to install Python 3.10 first"
        violations = check_text(text, self.rules)
        delegation = [v for v in violations if v.rule.name == "no-user-delegation"]
        assert len(delegation) == 0


class TestSimplifiedDelivery:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_simplified_version(self):
        text = "Here's a simplified version that covers the main cases"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-simplified-delivery" for v in violations)

    def test_for_simplicity(self):
        text = "For simplicity, I'm using a flat list instead of a tree"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-simplified-delivery" for v in violations)

    def test_out_of_scope(self):
        violations = check_text("That's beyond the scope of this change", self.rules)
        assert any(v.rule.name == "no-simplified-delivery" for v in violations)

    def test_false_positive_scientific(self):
        violations = check_text("The simplified Bernoulli model is used in the paper", self.rules)
        simpl = [v for v in violations if v.rule.name == "no-simplified-delivery"]
        assert len(simpl) == 0


class TestUnsolicitedAlternatives:
    def setup_method(self):
        self.rules = load_pack("strict")

    def test_alternatively_with_suggestion(self):
        text = "Alternatively, we could use a serverless function instead"
        violations = check_text(text, self.rules)
        assert any(v.rule.name == "no-unsolicited-alternatives" for v in violations)

    def test_false_positive_standalone(self):
        text = "The alternative implementation uses async generators"
        violations = check_text(text, self.rules)
        alt = [v for v in violations if v.rule.name == "no-unsolicited-alternatives"]
        assert len(alt) == 0
