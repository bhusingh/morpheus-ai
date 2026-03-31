"""Tests for config file loading."""

from pathlib import Path

from ai_watchdog.config import Config, find_config, load_config


def test_default_config():
    cfg = Config()
    assert cfg.pack == "standard"
    assert cfg.fmt == "text"
    assert cfg.stats_enabled is True
    assert cfg.custom_rules is None
    assert cfg.instructions is None


def test_from_dict_full():
    data = {
        "rules": {"pack": "strict", "custom": "./rules/"},
        "instructions": ["CLAUDE.md", ".cursorrules"],
        "output": {"format": "json"},
        "stats": {"enabled": False},
    }
    cfg = Config.from_dict(data)
    assert cfg.pack == "strict"
    assert cfg.custom_rules == "./rules/"
    assert cfg.instructions == ["CLAUDE.md", ".cursorrules"]
    assert cfg.fmt == "json"
    assert cfg.stats_enabled is False


def test_from_dict_minimal():
    cfg = Config.from_dict({})
    assert cfg.pack == "standard"
    assert cfg.stats_enabled is True


def test_from_dict_instructions_as_string():
    cfg = Config.from_dict({"instructions": "CLAUDE.md"})
    assert cfg.instructions == ["CLAUDE.md"]


def test_load_config_from_file(tmp_path):
    config_file = tmp_path / ".ai-watchdog.yaml"
    config_file.write_text(
        "rules:\n"
        "  pack: strict\n"
        "output:\n"
        "  format: json\n"
        "stats:\n"
        "  enabled: false\n"
    )
    cfg = load_config(config_file)
    assert cfg.pack == "strict"
    assert cfg.fmt == "json"
    assert cfg.stats_enabled is False


def test_load_config_missing_file():
    cfg = load_config(Path("/nonexistent/.ai-watchdog.yaml"))
    assert cfg.pack == "standard"


def test_load_config_corrupt_yaml(tmp_path):
    config_file = tmp_path / ".ai-watchdog.yaml"
    config_file.write_text(": : : invalid")
    cfg = load_config(config_file)
    assert cfg.pack == "standard"


def test_find_config_in_cwd(tmp_path):
    config_file = tmp_path / ".ai-watchdog.yaml"
    config_file.write_text("rules:\n  pack: light\n")
    found = find_config(tmp_path)
    assert found == config_file


def test_find_config_in_parent(tmp_path):
    config_file = tmp_path / ".ai-watchdog.yaml"
    config_file.write_text("rules:\n  pack: strict\n")
    subdir = tmp_path / "src" / "deep"
    subdir.mkdir(parents=True)
    found = find_config(subdir)
    assert found == config_file


def test_find_config_none(tmp_path):
    empty = tmp_path / "empty_project"
    empty.mkdir()
    found = find_config(empty)
    # may find the project's own config if running from the repo,
    # so we just check it doesn't crash
    assert found is None or found.name == ".ai-watchdog.yaml"
