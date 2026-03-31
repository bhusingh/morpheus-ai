# Changelog

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
