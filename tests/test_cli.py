"""Tests for the CLI interface."""

import pytest
from click.testing import CliRunner

import morpheus_ai.audit as audit_module
import morpheus_ai.stats as stats_module
from morpheus_ai.cli import main


@pytest.fixture(autouse=True)
def _isolate_local_data(tmp_path, monkeypatch):
    """Redirect stats and audit to temp so tests never touch ~/.morpheus-ai/."""
    monkeypatch.setattr(stats_module, "DEFAULT_STATS_PATH", tmp_path / "stats.json")
    monkeypatch.setattr(audit_module, "DEFAULT_AUDIT_PATH", tmp_path / "audit.log")


class TestCheckCommand:
    def setup_method(self):
        self.runner = CliRunner()

    def test_stdin_clean(self):
        result = self.runner.invoke(main, ["check", "--stdin"], input="def hello(): pass\n")
        assert result.exit_code == 0

    def test_stdin_blocking_violation(self):
        result = self.runner.invoke(
            main,
            ["check", "--stdin", "--pack", "strict"],
            input="We could just skip the tests for now.",
        )
        assert result.exit_code == 2

    def test_stdin_json_format(self):
        result = self.runner.invoke(
            main,
            ["check", "--stdin", "--format", "json", "--pack", "strict"],
            input="We could just skip it for now.",
        )
        assert result.exit_code == 2

    def test_file_input(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("We could just skip the tests for now.")
        result = self.runner.invoke(main, ["check", "--pack", "strict", str(f)])
        assert result.exit_code == 2

    def test_file_clean(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Implemented all requested changes successfully.")
        result = self.runner.invoke(main, ["check", str(f)])
        assert result.exit_code == 0

    def test_no_input_error(self):
        result = self.runner.invoke(main, ["check"])
        assert result.exit_code == 2

    def test_warn_only_passes(self):
        result = self.runner.invoke(
            main,
            ["check", "--stdin", "--pack", "strict"],
            input="I think we should probably use Redis here",
        )
        # INFO severity (hedging) does not cause exit code 2
        assert result.exit_code == 0

    def test_light_pack(self):
        result = self.runner.invoke(
            main,
            ["check", "--stdin", "--pack", "light"],
            input="We could just skip it.",
        )
        assert result.exit_code == 2


class TestStatsCommand:
    def test_stats_text(self):
        runner = CliRunner()
        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0
        assert "Total checks" in result.output

    def test_stats_json(self):
        runner = CliRunner()
        result = runner.invoke(main, ["stats", "--format", "json"])
        assert result.exit_code == 0


class TestConfigIntegration:
    def test_config_sets_pack(self, tmp_path, monkeypatch):
        """Config file pack setting is used when --pack is not given."""
        monkeypatch.chdir(tmp_path)
        config = tmp_path / ".morpheus-ai.yaml"
        config.write_text("rules:\n  pack: strict\n")
        f = tmp_path / "input.txt"
        f.write_text("We could just skip it for now.")
        runner = CliRunner()
        result = runner.invoke(main, ["check", str(f)])
        # strict pack catches this as BLOCK
        assert result.exit_code == 2

    def test_cli_flag_overrides_config(self, tmp_path, monkeypatch):
        """--pack flag overrides config file."""
        monkeypatch.chdir(tmp_path)
        config = tmp_path / ".morpheus-ai.yaml"
        config.write_text("rules:\n  pack: strict\n")
        runner = CliRunner()
        result = runner.invoke(
            main, ["check", "--stdin", "--pack", "light"],
            input="I think we should probably use Redis here",
        )
        # light pack doesn't have hedging rule, so no violation
        assert result.exit_code == 0

    def test_no_stats_flag(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            main, ["check", "--stdin", "--no-stats"],
            input="def hello(): pass\n",
        )
        assert result.exit_code == 0


class TestAuditCommand:
    def setup_method(self):
        self.runner = CliRunner()

    def test_audit_empty(self):
        result = self.runner.invoke(main, ["audit"])
        assert result.exit_code == 0
        assert "No audit entries" in result.output

    def test_audit_after_check(self):
        self.runner.invoke(
            main, ["check", "--stdin", "--pack", "strict"],
            input="We could just skip it.",
        )
        result = self.runner.invoke(main, ["audit", "--tail", "1"])
        assert result.exit_code == 0
        assert "BLOCKED" in result.output
        assert "no-scope-reduction" in result.output

    def test_audit_json_format(self):
        self.runner.invoke(
            main, ["check", "--stdin"],
            input="All good.",
        )
        result = self.runner.invoke(main, ["audit", "--format", "json"])
        assert result.exit_code == 0
        assert '"source": "stdin"' in result.output

    def test_audit_clear(self):
        self.runner.invoke(
            main, ["check", "--stdin"],
            input="hello",
        )
        result = self.runner.invoke(main, ["audit", "--clear"])
        assert result.exit_code == 0
        assert "cleared" in result.output
        result = self.runner.invoke(main, ["audit"])
        assert "No audit entries" in result.output

    def test_no_audit_flag(self, tmp_path, monkeypatch):
        audit_path = tmp_path / "audit.log"
        monkeypatch.setattr(audit_module, "DEFAULT_AUDIT_PATH", audit_path)
        self.runner.invoke(
            main, ["check", "--stdin", "--no-audit"],
            input="hello",
        )
        assert not audit_path.exists()


class TestInitCommand:
    def test_init(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / ".morpheus-ai.yaml").exists()
        assert (tmp_path / "rules" / "custom.yaml").exists()

    def test_init_idempotent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "already exists" in result.output
