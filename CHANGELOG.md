# Changelog

## 0.3.0 — 2026-04-01

### Added

- **Context-aware hook support**: PreToolUse, PostToolUse, Stop, SubagentStop — all four Claude Code hook types now parsed with structured payloads
- **Smart rule filtering**: code-only rules (placeholder, delegation) only fire on code tools; conversation-only rules (options, confirmation, planning, false-completion) only fire on Stop/SubagentStop — significantly reduces false positives
- **False-completion rule**: catches vague claims like "I've implemented all the changes" or "Everything is working" without evidence (WARN in strict, INFO in standard)
- **Auto-discovery of instruction files**: automatically finds and enforces CLAUDE.md, .cursorrules, .cursor/rules, .github/copilot-instructions.md, .windsurfrules, .clinerules — no config needed
- **`--suggest-fix` flag**: outputs JSON fix guidance on stdout when blocking, enabling hook response integration
- **KAIROS/proactive mode awareness**: `<tick>` messages from autonomous mode auto-skipped
- **Speculation tracking**: speculative tool calls detected and tagged in audit log
- `HookPayload` and `parse_hook_payload()` added to public API
- `tool_name` and `speculation` fields in audit log entries
- New config key: `instructions_config.auto_discover` (default: true)
- 500 KB cap on auto-discovered instruction files to prevent slow checks
- Rule counts: light 6, standard 13, strict 19
- Development status upgraded from Alpha to Beta
- 262 tests

### Fixed

- Conversation-only rules no longer fire on PreToolUse hooks for Write/Edit tools (was causing false positives on code containing strings like "Option A")
- PostToolUse false-completion scanning now skips read-only tools (Read, Glob, Grep, ToolSearch, LSP) that return file contents
- Auto-discovery resolves instruction files from config directory, not cwd — works correctly from subdirectories and hook processes

## 0.2.1 — 2026-03-31

### Fixed

- Engine now parses Stop hook `last_assistant_message` field — catches lazy patterns in Claude's conversational text, not just tool inputs
- README hook config updated to use both PreToolUse and Stop hooks

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
