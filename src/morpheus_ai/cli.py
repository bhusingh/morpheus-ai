"""Click CLI — check, stats, init."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from morpheus_ai.config import load_config
from morpheus_ai.engine import check_hook_input, check_text, load_rules, max_severity
from morpheus_ai.reporter import report
from morpheus_ai.rules import Severity
from morpheus_ai.stats import Stats


@click.group()
@click.version_option(package_name="morpheus-ai")
def main() -> None:
    """morpheus-ai — stop your AI coding assistant from being lazy."""


@main.command()
@click.option("--stdin", "use_stdin", is_flag=True, help="Read input from stdin (hook mode).")
@click.option("--pack", default=None, help="Rule pack: strict, standard, light.")
@click.option("--rules", "rules_dir", default=None, help="Custom rules directory.")
@click.option("--instructions", "instructions_path", default=None,
              help="Instruction file to enforce (e.g. CLAUDE.md).")
@click.option("--format", "fmt", default=None,
              type=click.Choice(["text", "json", "github"]), help="Output format.")
@click.option("--no-stats", is_flag=True, help="Disable stats recording.")
@click.argument("file", required=False, type=click.Path(exists=True))
def check(
    use_stdin: bool,
    pack: str | None,
    rules_dir: str | None,
    instructions_path: str | None,
    fmt: str | None,
    no_stats: bool,
    file: str | None,
) -> None:
    """Check text for lazy AI patterns."""
    cfg = load_config()

    pack = pack or cfg.pack
    rules_dir = rules_dir or cfg.custom_rules
    fmt = fmt or cfg.fmt
    stats_enabled = cfg.stats_enabled and not no_stats

    text = _read_input(use_stdin, file)
    rules = load_rules(pack=pack, rules_dir=rules_dir)
    instructions = _load_instructions(instructions_path, cfg)

    if use_stdin:
        violations = check_hook_input(text, rules, instructions=instructions)
    else:
        violations = check_text(text, rules, instructions=instructions)

    report(violations, fmt=fmt)

    if stats_enabled:
        try:
            s = Stats.load()
            s.record(violations)
            s.save()
        except Exception:
            pass

    if max_severity(violations) == Severity.BLOCK:
        raise SystemExit(2)


def _read_input(use_stdin: bool, file: str | None) -> str:
    _MAX_INPUT = 1_000_000
    if use_stdin:
        return sys.stdin.read(_MAX_INPUT)
    if file:
        file_path = Path(file)
        if file_path.stat().st_size > _MAX_INPUT:
            click.echo(f"Error: file too large (max {_MAX_INPUT} bytes).", err=True)
            raise SystemExit(2)
        return file_path.read_text()
    click.echo("Error: provide --stdin or a file path.", err=True)
    raise SystemExit(2)


def _load_instructions(
    cli_path: str | None,
    cfg: object,
) -> list[str] | None:
    paths: list[str] = []
    if cli_path:
        paths = [cli_path]
    elif hasattr(cfg, "instructions") and cfg.instructions:
        paths = cfg.instructions
    if not paths:
        return None
    contents: list[str] = []
    for p in paths:
        path = Path(p)
        if path.is_file():
            contents.append(path.read_text())
    return contents or None


@main.command()
@click.option("--format", "fmt", default="text", type=click.Choice(["text", "json"]))
def stats(fmt: str) -> None:
    """Show violation statistics."""
    s = Stats.load()
    if fmt == "json":
        import json

        click.echo(json.dumps(s.to_dict(), indent=2))
    else:
        click.echo(f"Total checks:     {s.total_checks}")
        click.echo(f"Total violations: {s.total_violations}")
        if s.by_rule:
            click.echo("\nBy rule:")
            for rule, count in s.by_rule.most_common():
                click.echo(f"  {rule}: {count}")
        if s.by_severity:
            click.echo("\nBy severity:")
            for sev, count in s.by_severity.most_common():
                click.echo(f"  {sev}: {count}")
        if s.last_updated:
            click.echo(f"\nLast updated: {s.last_updated}")


@main.command()
def init() -> None:
    """Create .morpheus-ai.yaml and example rules in the current directory."""
    config_path = Path(".morpheus-ai.yaml")
    rules_path = Path("rules")
    try:
        _do_init(config_path, rules_path)
    except OSError as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


def _do_init(config_path: Path, rules_path: Path) -> None:
    if config_path.exists():
        click.echo(f"{config_path} already exists, skipping.")
    else:
        config_path.write_text(
            "# morpheus-ai configuration\n"
            "# CLI flags override these defaults.\n"
            "\n"
            "rules:\n"
            "  pack: standard        # strict, standard, light\n"
            "  # custom: ./rules/   # path to custom rules directory\n"
            "\n"
            "# instructions:         # instruction files to enforce\n"
            "#   - CLAUDE.md\n"
            "#   - .cursorrules\n"
            "\n"
            "output:\n"
            "  format: text          # text, json, github\n"
            "\n"
            "stats:\n"
            "  enabled: true         # track violation frequency\n"
        )
        click.echo(f"Created {config_path}")

    rules_path.mkdir(exist_ok=True)
    example = rules_path / "custom.yaml"
    if not example.exists():
        example.write_text(
            "# Custom rules — add your own patterns here\n"
            "rules:\n"
            "  - name: example-custom-rule\n"
            "    severity: WARN\n"
            "    description: Example custom rule\n"
            "    patterns:\n"
            '      - "(?i)\\bplaceholder pattern\\b"\n'
        )
        click.echo(f"Created {example}")
