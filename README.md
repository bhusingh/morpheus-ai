# ai-watchdog

**Stop your AI coding assistant from being lazy.**

AI coding agents (Claude Code, Cursor, Copilot, etc.) have a bad habit: instead of doing what you asked, they suggest shortcuts, skip steps, offer A/B/C options, and defer work. You said "build it", they say "should we maybe just...?"

`ai-watchdog` catches this in real-time and blocks it.

## The Problem

You: "Set up the full annotation pipeline"

AI: "We could skip GatorTron for now and just run stages 0,1... Want me to:
- Option A: Run partial pipeline (quick)
- Option B: Build everything (slower)
- Option C: Just plan it"

**No.** You said build it. Build it.

### What ai-watchdog detects

| Pattern | Example | Why it's bad |
|---------|---------|--------------|
| **Scope reduction** | "We could skip X for now" | You didn't ask to skip anything |
| **Option offering** | "Option A / Option B / Option C" | You gave a directive, not a question |
| **Deferral** | "We can do this later" | You said now |
| **Permission seeking** | "Should I proceed?" | You already said yes |
| **Partial execution** | "Let's start with just..." | You said the whole thing |
| **Instruction violation** | Ignoring rules in CLAUDE.md | The rules exist for a reason |

## Install

```bash
pip install ai-watchdog
```

## Quick Start

### As a Claude Code hook

```json
// .claude/settings.json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Agent|Bash|Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "ai-watchdog check --stdin"
          }
        ]
      }
    ]
  }
}
```

### As a CLI

```bash
# Check a single response
echo "Should we skip the tests for now?" | ai-watchdog check --stdin

# Watch a log file
ai-watchdog watch --file conversation.jsonl

# Validate against instruction files
ai-watchdog audit --rules ./rules/ --conversation conversation.jsonl
```

### As a Python library

```python
from ai_watchdog import Watchdog

dog = Watchdog.from_rules_dir("./rules/")

response = "We could skip GatorTron and just run the CPU stages..."
violations = dog.check(response)

for v in violations:
    print(f"[{v.severity}] {v.rule}: {v.match}")
    # [BLOCK] no-scope-reduction: "skip GatorTron and just run"
```

## Rules

Rules are YAML files that define what to catch:

```yaml
# rules/no-shortcuts.yaml
name: no-scope-reduction
severity: BLOCK
description: Agent must not suggest skipping or reducing requested scope
patterns:
  - "(?i)\\b(skip|defer|later|for now|instead of|we could just)\\b"
  - "(?i)\\bOption [A-C]\\b"
  - "(?i)\\b(should I|want me to|shall we|do you want)\\b.*\\?"
context:
  - The user gave a clear directive
  - The agent is suggesting doing less than asked
```

### Built-in rule packs

| Pack | Rules | What it catches |
|------|-------|-----------------|
| `strict` | 12 rules | All scope reduction, option offering, deferral, permission seeking |
| `standard` | 8 rules | Scope reduction, option offering, deferral (allows clarifying questions) |
| `light` | 4 rules | Only catches blatant shortcuts and instruction violations |

```bash
# Use a built-in pack
ai-watchdog check --pack strict --stdin

# Or bring your own rules
ai-watchdog check --rules ./my-rules/ --stdin
```

## How it works

1. **Pattern matching** - Fast regex-based detection of lazy patterns
2. **Context analysis** - Understands if the user gave a directive vs asked a question
3. **Instruction compliance** - Loads your CLAUDE.md / .cursorrules and checks if the agent follows them
4. **Severity levels** - BLOCK (stop the action), WARN (log it), INFO (count it)

### Architecture

```
User prompt ──> AI Agent ──> ai-watchdog ──> Allow / Block
                                 |
                            Rules Engine
                            (YAML rules)
                                 |
                         Instruction Files
                       (CLAUDE.md, .cursorrules)
```

## Configuration

```yaml
# .ai-watchdog.yaml (project root)
rules:
  pack: strict            # Built-in pack: strict, standard, light
  custom: ./rules/        # Additional custom rules (merged with pack)

instructions:             # Instruction files to enforce
  - CLAUDE.md
  - .cursorrules
  - .claude/commands/*.md

on_violation:
  BLOCK: reject           # reject = block the action, warn = log only
  WARN: log
  INFO: count

output:
  format: text            # text, json, github-annotation
  file: null              # Log file path (null = stderr)

stats:
  enabled: true           # Track violation frequency
  report_every: 50        # Print stats every N checks
```

## Integrations

### Claude Code (hooks)

```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": ".*",
      "hooks": [{
        "type": "command",
        "command": "ai-watchdog check --pack strict --stdin --format json"
      }]
    }]
  }
}
```

### Cursor (.cursorrules)

Add to your `.cursorrules`:
```
IMPORTANT: Do not suggest alternatives, options, or shortcuts.
Execute exactly what was requested. Do not ask for confirmation
unless there is a genuine technical blocker.
```

Then validate:
```bash
ai-watchdog audit --instructions .cursorrules --conversation output.log
```

### CI/CD (GitHub Actions)

```yaml
- name: AI Watchdog Audit
  run: |
    pip install ai-watchdog
    ai-watchdog audit \
      --rules ./rules/ \
      --instructions CLAUDE.md \
      --conversation .claude/conversations/*.jsonl \
      --format github-annotation
```

## Stats & Reporting

```bash
$ ai-watchdog stats

AI Watchdog Report (last 7 days)
================================
Total checks:     1,247
Violations:       89 (7.1%)
  BLOCK:          23
  WARN:           41
  INFO:           25

Top violations:
  1. no-scope-reduction    34 hits  "skip X for now"
  2. no-option-offering    22 hits  "Option A / B / C"
  3. no-deferral           18 hits  "we can do this later"
  4. no-permission-seeking 15 hits  "should I proceed?"

Trend: -12% vs last week (rules are working)
```

## Why?

AI coding assistants are incredibly capable but have a systematic problem: **they optimize for appearing helpful over being helpful.** Offering options feels collaborative. Suggesting shortcuts feels considerate. But when you've already decided what to build, these behaviors waste time and erode trust.

The fix isn't better prompting — it's enforcement. `ai-watchdog` is that enforcement layer.

## Contributing

PRs welcome. Especially:
- New rule packs for specific workflows
- Integration plugins for more AI tools
- False positive reduction in pattern matching
- Benchmarks on real conversation logs

## License

MIT
