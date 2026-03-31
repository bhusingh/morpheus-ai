# ai-watchdog — Project Instructions

## What this project is

`ai-watchdog` is a fast Python CLI tool and library for detecting lazy AI-assistant behavior such as:
- scope reduction
- option offering
- deferral
- test skipping
- placeholder delivery
- instruction-compliance violations

The product is intentionally lightweight: regex- and heuristic-based, fast enough for hook usage, and easy to customize with YAML rule packs.

## Current architecture

```text
src/ai_watchdog/
  __init__.py          # Public API exports
  __main__.py          # python -m ai_watchdog entrypoint
  cli.py               # Click CLI: check, stats, init
  config.py            # Loads .ai-watchdog.yaml from cwd/parents
  engine.py            # Rule loading, text scanning, hook parsing
  reporter.py          # text/json/github output formatting
  rules.py             # Rule model, YAML loading, pack loading
  stats.py             # Best-effort local stats persistence
  violation.py         # Violation model
  packs/
    light.yaml
    standard.yaml
    strict.yaml

tests/
  test_cli.py
  test_config.py
  test_engine.py
  test_new_rules.py
  test_pack_examples.py
  test_reporter.py
  test_rules.py
  test_stats.py
```

## Stack

- Python 3.10+
- Click
- PyYAML
- No ML dependencies
- No network dependency in the runtime path

## Public behavior

### CLI commands

```text
ai-watchdog check [--stdin] [--pack NAME] [--rules DIR] [--instructions PATH]
                  [--format text|json|github] [--no-stats] [FILE]
ai-watchdog stats [--format text|json]
ai-watchdog init
python -m ai_watchdog ...
```

### Config

The tool supports `.ai-watchdog.yaml`, discovered by walking upward from the current directory.

Supported config keys:

```yaml
rules:
  pack: standard
  custom: ./rules/

instructions:
  - CLAUDE.md
  - .cursorrules

output:
  format: text

stats:
  enabled: true
```

CLI flags override config values.

### Exit behavior

- `BLOCK` violation present: exit code `2`
- only `WARN` / `INFO`: exit code `0`
- clean result: exit code `0`

Hook-friendly behavior matters more than fancy output.

## Design principles

1. Speed over sophistication. This tool should stay simple and fast.
2. Rules are data. Detection logic should live in YAML packs where possible.
3. False positives are acceptable in stricter packs, but docs and examples must be honest.
4. Public docs must match the implementation exactly.
5. Tests are part of the product surface. Rule examples, CLI behavior, config loading, and reporter output should all be covered.

## Coding guidance

- Prefer extending packs and tests together.
- If a rule changes, update:
  - the YAML pack
  - direct rule tests
  - YAML example validation where relevant
- Keep CLI behavior predictable and minimal.
- Stats must remain best-effort and never block core rule results.
- Avoid introducing optional complexity unless it clearly improves usability.

## Release guidance

This project is currently best described as alpha-quality tooling. Be careful not to overstate maturity in docs or release messaging unless:
- tests pass from a clean environment
- README examples are verified
- packaged artifacts include the required rule data files

## When working in this repo

- Read the current implementation before assuming a feature exists.
- Do not reintroduce stale concepts like `watch`, `audit`, `context.py`, `instructions.py`, `Watchdog`, or `Rich` unless they are actually implemented.
- Keep README, CLI help, and `CLAUDE.md` aligned.
