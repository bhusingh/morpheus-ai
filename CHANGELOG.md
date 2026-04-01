# Changelog

## 0.3.0 — 2026-04-01

### Added

- **Context-aware hook support**: SubagentStop, PostToolUse, and improved PreToolUse/Stop parsing
- **Structured hook payload parsing**: extracts hook_event_name, tool_name, tool_output from JSON
- **Smart rule filtering**: code-only rules (placeholder, delegation) skip Stop hooks; conversation-only rules (options, confirmation, planning) skip Bash/Read hooks — reduces false positives
- **False-completion rule**: catches "I've implemented all the changes" / "Everything is working" claims (WARN in strict, INFO in standard)
- Rule counts: light 6, standard 13, strict 19
- `HookPayload` and `parse_hook_payload()` added to public API
- `tool_name` and `speculation` fields in audit log entries
- Audit display shows tool name per entry
- **KAIROS/proactive mode**: `<tick>` messages auto-skipped (no false positives)
- **Auto-discovery of instruction files**: CLAUDE.md, .cursorrules, .cursor/rules, .github/copilot-instructions.md, .windsurfrules, .clinerules
- **`--suggest-fix` flag**: outputs JSON fix guidance on stdout when blocking (hook response mode)
- **Speculation tracking**: speculative tool calls detected and tagged in audit
- 262 tests

## 0.2.0 — 2026-03-31

### Added

- **Audit log**: local, append-only record of every check at `~/.morpheus-ai/audit.log`
- New CLI command: `morpheus-ai audit [--tail N] [--format text|json] [--clear]`
- New config key: `audit.enabled` (default: true)
- New CLI flag: `--no-audit` on the check command
- No input content is ever logged — only metadata (timestamp, pack, input size, violations, matched rules)
- Audit log capped at 5 MB with automatic trimming
- Security & Trust section in README with explicit no-network, no-telemetry guarantees
- CI/PyPI/Python/License badges in README
- "This is not a linter" positioning section in README

## 0.1.0 — 2026-03-31

Initial public release.

### Added

- CLI tool: `morpheus-ai check`, `morpheus-ai stats`, `morpheus-ai init`
- Python library API: `check_text()`, `load_rules()`, `check_hook_input()`
- Three built-in rule packs: `light` (6 rules), `standard` (12 rules), `strict` (18 rules)
- Detection for: scope reduction, option offering, deferral, test skipping, placeholder code, user delegation, simplified delivery, partial execution, false blockers, premature confirmation, excessive planning, unsolicited alternatives, error handling deferral, hardcoded shortcuts, cost scaring, scope creep warnings, hedging, ellipsis truncation
- Instruction compliance checking against CLAUDE.md / .cursorrules
- Custom YAML rules with regex patterns
- Hook mode: JSON parsing for Claude Code `PreToolUse` hooks
- Output formats: text (default), JSON, GitHub Actions annotations
- Config file `.morpheus-ai.yaml` with walk-up directory discovery
- Local stats persistence to `~/.morpheus-ai/stats.json`
- Exit code 2 on BLOCK violations for hook-friendly behavior
