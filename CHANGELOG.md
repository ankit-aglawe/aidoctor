# Changelog

All notable changes to aidoctor are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
