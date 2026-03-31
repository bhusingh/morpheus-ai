# ai-watchdog — Engineering Standards

## What this project is

A CLI tool + Python library that catches AI coding assistants (Claude Code, Cursor, Copilot) being lazy — detecting scope reduction, option offering, deferral, and instruction violations in real-time.

**Target users**: Developers who use AI coding assistants and are tired of them suggesting shortcuts instead of executing.

## Architecture

```
src/ai_watchdog/
  __init__.py          # Public API: Watchdog, Violation, Rule
  cli.py               # Click CLI: check, watch, audit, stats
  engine.py            # Core rules engine — loads rules, runs checks
  rules.py             # Rule model (YAML parsing, pattern compilation)
  violation.py         # Violation model with severity levels
  context.py           # Context analyzer — was user's message a directive or question?
  instructions.py      # Loads and validates CLAUDE.md / .cursorrules compliance
  reporter.py          # Output formatting (text, JSON, GitHub annotations)
  stats.py             # Violation tracking and reporting
  packs/               # Built-in rule packs (YAML files)
    strict.yaml
    standard.yaml
    light.yaml
rules/                 # User-facing example rules
tests/                 # pytest tests
```

## Stack

- **Python 3.10+** — minimum version for broad compatibility
- **Click** — CLI framework
- **Rich** — Terminal output formatting
- **PyYAML** — Rule file parsing
- **No ML dependencies** — this must be fast (< 50ms per check). Regex + heuristics only.

## Key Design Decisions

1. **Speed over accuracy** — False positives are acceptable, false negatives are not. A check must complete in < 50ms to work as a real-time hook.
2. **Rules are data, not code** — All detection patterns live in YAML files. Users can add/override without touching Python.
3. **Severity levels matter** — BLOCK = reject the action (exit 1), WARN = log and continue (exit 0), INFO = silent count.
4. **stdin/stdout protocol** — For hook integration, the tool reads from stdin and writes to stderr (violations) or stdout (pass-through).
5. **Zero config works** — `ai-watchdog check --stdin` with no rules file uses the `standard` built-in pack.

## CLI Commands

```
ai-watchdog check [--stdin] [--pack NAME] [--rules DIR] [--format text|json]
ai-watchdog watch --file PATH [--pack NAME] [--rules DIR]
ai-watchdog audit --conversation PATH [--instructions PATH] [--rules DIR]
ai-watchdog stats [--days N] [--format text|json]
ai-watchdog init                  # Create .ai-watchdog.yaml + example rules
```

## Hook Integration Protocol

When used as a Claude Code hook (PreToolUse), the tool:
1. Reads the tool input from stdin (JSON with `tool_name` and `tool_input` fields)
2. Extracts text content to analyze
3. Runs rules against it
4. If BLOCK violation found: prints violation to stderr, exits with code 2 (hook blocks action)
5. If WARN/INFO only: prints to stderr, exits with code 0 (hook allows action)
6. If clean: exits with code 0

## Coding Standards

- **Tests for every rule** — each built-in rule must have positive and negative test cases
- **No dependencies beyond click/rich/pyyaml** — keep install fast
- **Type hints everywhere** — this is a developer tool, be strict
- **Docstrings on public API only** — internal code should be self-documenting
- Functions < 30 lines, files < 200 lines
- No classes unless there's state to manage

## Release Plan

1. MVP: `check` command with `strict` pack, stdin/stdout, Claude Code hook example
2. v0.2: `audit` command, instruction file compliance, stats tracking
3. v0.3: `watch` command (live file tailing), GitHub Actions integration
4. v1.0: Stable API, comprehensive rule packs, community rules repo
