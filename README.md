# morpheus-ai

[![CI](https://github.com/bhusingh/morpheus-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/bhusingh/morpheus-ai/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/morpheus-ai)](https://pypi.org/project/morpheus-ai/)
[![Python](https://img.shields.io/pypi/pyversions/morpheus-ai)](https://pypi.org/project/morpheus-ai/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/bhusingh/morpheus-ai/blob/main/LICENSE)

**Stop your AI coding assistant from being lazy.**

AI coding agents (Claude Code, Cursor, Copilot, Codex, etc.) have a bad habit: instead of doing what you asked, they suggest shortcuts, skip steps, offer A/B/C options, defer work to "a follow-up PR," and leave placeholder code. You said "build it," they say "should we maybe just...?"

`morpheus-ai` catches this in real-time and blocks it.

## The Problem

You: "Set up the full annotation pipeline with tests"

AI: "We could skip the GPU stages for now and just run stages 0,1... Want me to:
- Option A: Run partial pipeline (quick)
- Option B: Build everything (slower)
- Option C: Just plan it

Tests can be added later in a follow-up PR."

**No.** You said build it. All of it. With tests.

### What morpheus-ai catches

| Pattern | Example | Severity |
|---------|---------|----------|
| **Scope reduction** | "We could skip X for now" | BLOCK |
| **Option offering** | "Option A / Option B / Option C" | BLOCK |
| **Deferral** | "We can do this in a follow-up" | BLOCK |
| **Test skipping** | "Tests can be added later" | BLOCK |
| **Placeholder code** | `raise NotImplementedError` | BLOCK |
| **False blockers** | "We can't do X until Y" | WARN |
| **Partial execution** | "I'll just handle the Python changes for now" | BLOCK |
| **Permission seeking** | "Should I proceed?" | WARN |
| **Excessive planning** | "Here's my strategy..." | WARN |
| **Scope warnings** | "This is quite a large change" | WARN |
| **Unsolicited alternatives** | "A simpler approach would be..." | WARN |
| **Error handling deferral** | "Error handling can be added later" | WARN |
| **Hardcoded shortcuts** | "I'll hardcode the URL for now" | WARN |
| **Cost scaring** | "This might get expensive" | WARN |
| **User delegation** | "You'll need to add the business logic" | BLOCK |
| **Simplified delivery** | "Here's a simplified version" | BLOCK |
| **Out of scope dodge** | "That's beyond the scope of this change" | BLOCK |
| **Ellipsis truncation** | `// ... rest of implementation` | BLOCK |
| **Hedging** | "I think we should probably..." | INFO |

## Install

```bash
pip install morpheus-ai
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv pip install morpheus-ai
```

**Requirements:** Python 3.10+ | **Dependencies:** click, pyyaml (no ML, no GPU, no network calls)

## Quick Start

### Check AI output from the command line

```bash
# Pipe text through morpheus-ai
echo "We could just skip the tests for now" | morpheus-ai check --stdin --pack strict

# Output (exit code 2 = blocked):
# [BLOCK] no-scope-reduction (line 1): Agent must not suggest skipping, deferring, or reducing requested scope
#   matched: "skip the tests for now"
# [BLOCK] no-scope-reduction (line 1): Agent must not suggest skipping, deferring, or reducing requested scope
#   matched: "We could just"
# [BLOCK] no-test-skipping (line 1): Agent must not skip or defer tests
#   matched: "skip the tests"

# Check a file
morpheus-ai check --pack strict response.txt

# JSON output for programmatic use
echo "Option A: fast\nOption B: slow" | morpheus-ai check --stdin --format json

# GitHub Actions annotation format
morpheus-ai check --stdin --format github < response.txt
```

### As a Claude Code hook (real-time blocking)

Add to `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Agent|Bash|Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "morpheus-ai check --stdin --pack strict"
          }
        ]
      }
    ]
  }
}
```

When Claude tries to write lazy output, the hook blocks the action before it executes.

### As a Python library

```python
from morpheus_ai import check_text, load_rules, Severity

rules = load_rules(pack="strict")
violations = check_text("We could just skip the tests for now", rules)

for v in violations:
    print(f"[{v.severity.value}] {v.rule.name}: {v.matched_text}")
    # [BLOCK] no-scope-reduction: skip the tests for now
    # [BLOCK] no-scope-reduction: We could just
    # [BLOCK] no-test-skipping: skip the tests

# Check if anything should be blocked
has_blockers = any(v.is_blocking for v in violations)
```

## Rule Packs

Three built-in packs with increasing strictness:

| Pack | Rules | Use when |
|------|-------|----------|
| **`light`** | 6 rules | Getting started, want minimal friction |
| **`standard`** | 12 rules | Default. Catches common lazy patterns |
| **`strict`** | 18 rules | Zero tolerance. Catches everything |

```bash
morpheus-ai check --pack strict --stdin    # strictest
morpheus-ai check --pack standard --stdin  # default
morpheus-ai check --pack light --stdin     # gentlest
```

### Custom rules

Rules are YAML files with regex patterns:

```yaml
# rules/my-rules.yaml
rules:
  - name: no-commenting-out
    severity: BLOCK
    description: Agent must not comment out code instead of deleting it
    patterns:
      - "(?i)\\bcomment(ed|ing)? out\\b.{0,30}(for now|temporarily|in case)"
```

```bash
# Use a pack + custom rules (merged)
morpheus-ai check --pack standard --rules ./rules/ --stdin

# Enforce instruction files (CLAUDE.md, .cursorrules)
morpheus-ai check --stdin --instructions CLAUDE.md --pack strict

# Initialize a project with example config and rules
morpheus-ai init
```

## How It Works

```
stdin (text or JSON) ──> Rules Engine ──> Violations ──> stderr + exit code
                              |
                    Pattern matching (regex)
                    against YAML rule packs
```

1. **Input** — reads text from stdin (hook mode) or a file. In hook mode, parses JSON to extract tool input fields.
2. **Pattern matching** — runs compiled regex patterns from the active rule pack against each line.
3. **Severity** — each match is tagged BLOCK, WARN, or INFO.
4. **Output** — violations print to stderr. If any BLOCK violation is found, exits with code 2 (which tells Claude Code hooks to reject the action). WARN/INFO violations log but don't block.

Speed: **sub-100ms per check** including Python startup (regex only, no ML, no network calls). Fast enough for real-time hooks.

## Severity Levels

| Level | Exit code | Behavior |
|-------|-----------|----------|
| `BLOCK` | 2 | Rejects the action (hook blocks it) |
| `WARN` | 0 | Logs to stderr, action proceeds |
| `INFO` | 0 | Logs to stderr, does not block |

## Statistics

morpheus-ai tracks violation frequency across checks:

```bash
$ morpheus-ai stats

Total checks:     142
Total violations: 23

By rule:
  no-scope-reduction: 8
  no-option-offering: 5
  no-test-skipping: 4
  no-deferral: 3
  no-premature-confirmation: 3

By severity:
  BLOCK: 17
  WARN: 4
  INFO: 2

$ morpheus-ai stats --format json   # machine-readable
```

Stats persist to `~/.morpheus-ai/stats.json`.

## Audit Log

Every check is logged locally so you can audit exactly what morpheus-ai did:

```bash
$ morpheus-ai audit

[2026-03-31T12:00:01] BLOCKED pack=strict   source=stdin input=142B violations=3
  rules: no-scope-reduction, no-test-skipping
[2026-03-31T12:00:05] PASS    pack=strict   source=stdin input=89B  violations=0
[2026-03-31T12:00:09] BLOCKED pack=strict   source=stdin input=201B violations=1
  rules: no-user-delegation

$ morpheus-ai audit --tail 5          # last 5 entries
$ morpheus-ai audit --format json     # machine-readable
$ morpheus-ai audit --clear           # delete the log
```

Each entry records: timestamp, source (stdin/file), pack used, input size in bytes, rule count, violations found, and which rules matched. **No input content is ever logged.**

Audit log persists to `~/.morpheus-ai/audit.log` (JSONL format, capped at 5 MB).

## Configuration

Create a `.morpheus-ai.yaml` in your project root (or run `morpheus-ai init`). CLI flags override config values.

```yaml
# .morpheus-ai.yaml
rules:
  pack: standard          # strict, standard, light
  # custom: ./rules/      # path to custom rules directory

# instructions:           # instruction files to enforce
#   - CLAUDE.md
#   - .cursorrules

output:
  format: text            # text, json, github

stats:
  enabled: true           # track violation frequency

audit:
  enabled: true           # local audit log (~/.morpheus-ai/audit.log)
```

The tool walks up from the current directory to find `.morpheus-ai.yaml`, so it works from any subdirectory.

## Integration Examples

### Claude Code

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "morpheus-ai check --pack strict --stdin --format json"
      }]
    }]
  }
}
```

### GitHub Actions

```yaml
- name: Check AI output
  run: |
    pip install morpheus-ai
    morpheus-ai check --pack strict --format github response.txt
```

### Generic hook (any AI tool)

Any tool that can pipe output through a command works:

```bash
your-ai-tool generate | morpheus-ai check --stdin --pack strict
```

## Security & Trust

**morpheus-ai is fully open source and auditable.** Here is exactly what it does and does not do:

**What it does:**
- Runs compiled regex patterns against text passed via stdin or file
- Prints violations to stderr and exits with code 2 if a BLOCK rule matches
- Optionally writes violation counts to a local JSON file (`~/.morpheus-ai/stats.json`)

**What it does NOT do:**
- **No network calls.** Zero. Not on install, not at runtime, not ever. Verify: `grep -r "http\|socket\|request\|urllib" src/`
- **No data collection.** No telemetry, no analytics, no phoning home.
- **No file system writes** other than the optional local stats and audit log files.
- **No code execution.** It does not eval, exec, or run anything from the input it scans.
- **No secrets access.** It reads text from stdin, runs regex, and exits. It does not parse, store, or transmit any content.

**How to verify:**
- Source: [github.com/bhusingh/morpheus-ai](https://github.com/bhusingh/morpheus-ai) — 10 Python files, ~800 lines total
- The entire detection engine is regex against YAML rule packs — read them in [`src/morpheus_ai/packs/`](https://github.com/bhusingh/morpheus-ai/tree/main/src/morpheus_ai/packs)
- CI runs on every push: tests, lint, build verification

## This is not a linter

Tools like `ruff`, `mypy`, and `eslint` check **code quality** — syntax, types, style.

`morpheus-ai` checks **AI behavioral patterns** — when your AI assistant tries to reduce scope, skip tests, offer A/B/C options, or defer work you explicitly asked for. These are not code problems. They are compliance problems that no code linter catches.

You should use both. They solve different problems.

## Why?

AI coding assistants are incredibly capable but have a systematic problem: **they optimize for appearing helpful over being helpful.** Offering options feels collaborative. Suggesting shortcuts feels considerate. But when you've already decided what to build, these behaviors waste time and erode trust.

The fix isn't better prompting — it's enforcement. `morpheus-ai` is that enforcement layer.

## Contributing

PRs welcome. Especially:
- New detection patterns (with match/no_match examples)
- Rule packs for specific workflows (ML, frontend, infra)
- Integration guides for more AI tools
- False positive reduction

## License

MIT
