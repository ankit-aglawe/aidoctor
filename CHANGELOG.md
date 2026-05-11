# Changelog

All notable changes to aidoctor are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The project follows [Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-05-11

### Added — the harness shape

- Catalog expanded from 3 → 7 skills. New: `audit` (six-dimensional whole-project review), `rules` (browse the rule catalog), `using-aidoctor` (orientation, model-invoked when relevant), `help` (slash command for the catalog + decision tree)
- New CLI command: `aidoctor rules` lists all 25 rules grouped by category, with `--category`, `--severity`, and `--json` filters
- Rule URL surfaced in scan terminal output — each violation now shows its `aidoctor scan --explain <id>` docs link inline
- `scan` and `audit` skill frontmatter now allow `Edit, Write` tools so the fix flows actually work (they previously claimed to fix but couldn't edit files)
- Install flow detects non-Python project root and notes that skills install globally regardless

### Changed

- Plugin marketplace description rewritten to name the four time-points (writing / diff / project / CI) and explicit Python scope
- README: new "what to invoke when" decision tree at the top of the Claude Code install section
- Positioning: "Python coding harness for AI agents" (was "static analyzer"). Multi-language family architecture noted in roadmap
- Interactive `aidoctor install` UX (cyan gradient banner + ◇/◆/●/○ icons) — lifted patterns from vercel-labs/skills
- BANNER\_GRADIENT applies a 12-shade per-row cyan gradient to the AI/DOCTOR ANSI Shadow logo

### Roadmap (declared, not shipped)

- v0.3+: `js-rules` and `rust-rules` SKILL packs built via the same iteration-1..3 A/B testing methodology
- v0.5+: tree-sitter backbone in CLI for multi-language deterministic scan
- Listed on the official Anthropic plugin marketplace
- MCP server (`aidoctor mcp`)
- `aidoctor learn` — propose project-local rules from your git history
- PR-delta scoring on GitHub Action

## [0.1.0] — 2026-05-11

### Added

- 25 rules across 7 categories: hardcoded secrets (3), AI-slop imports (4), dead defenses (4), async/sync mismatch (3), fake type hints (3), stale loop patterns (3), N+1 / performance (3), comment-driven decay (2)
- CLI: `aidoctor scan PATH` with `--json`, `--diff`, `--staged`, `--explain RULE`, `--fail-on error|warning|none`, `--verbose`
- CLI: `aidoctor install` writes a markdown skill into Claude Code, Cursor, OpenCode, Codex, and Gemini CLI agent dirs; backs up existing files
- CLI: `aidoctor skill --format <claude|cursor|opencode|codex|gemini|generic|raw>` prints the rendered skill to stdout for any agent without a native installer (Aider, Copilot Workspace, custom)
- CLI: `aidoctor scan-pr <github-url>` fetches a GitHub PR's diff via httpx and scores only the changed Python files
- Claude Code plugin: `/plugin marketplace add ankit-aglawe/aidoctor` then `/plugin install aidoctor@ankit-aglawe` — ships three model-invoked skills: `scan`, `simplify`, `python-rules`
- Multiprocessing parallel scan via `multiprocessing.Pool(cpu_count())` for repos with >4 files
- Score formula: `100 - unique_error_rules × 4 - unique_warning_rules × 2`, labels at 75/50
- Schema-versioned JSON output (`schema_version: 1`)
- Inline suppression: `# aidoctor: disable=rule-id`, `disable-line=`, `disable-file=`
- GitHub Action composite at `action.yml`
- Pre-commit hook config at `.pre-commit-hooks.yaml`
- 33 tests passing; pytest + pytest-cov + pytest-mock

### Project metadata

- Python 3.10+ required
- License: MIT
- Inspired by [react-doctor](https://github.com/millionco/react-doctor) by [@aidenybai](https://twitter.com/aidenybai)
