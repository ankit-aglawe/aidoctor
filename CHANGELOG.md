# Changelog

All notable changes to AIDoctor are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The project follows [Semantic Versioning](https://semver.org/).

## [2.0.0] — 2026-05-12

### The moat ships: `/aidoctor:deai` finds and removes AI fingerprints

v2.0 reframes aidoctor from "Python AI-slop linter" to **the coding harness with a deterministic verifier under it**. The new headline skill `/aidoctor:deai` detects the *visible* AI tells — NOTE/IMPORTANT emphasis labels, ASCII section dividers, hedge leakage, self-praise vocabulary, emojis in source code — and proposes deterministic fixes for each.

Three calibration bugs flagged by 8-persona evaluation are fixed: score caps, --fail-on default, and JSON streaming.

### Added

- **`/aidoctor:deai` skill + `aidoctor deai` CLI** — the moat. Scans code, filters to ai-style HIGH-confidence findings, proposes a fix per finding, computes an "AI residue score" (0–100, 100 = clean). The skill orchestrates interactive apply via the agent's file-edit tools; the CLI emits structured JSON the skill consumes.
- **5 ai_style rules** (Python; declarative via JSONL): `ai-emphasis-label` (NOTE/IMPORTANT/CAREFUL/CRITICAL/TIP/HACK/WARNING/REMEMBER), `ai-section-divider` (10+ char ASCII rules), `ai-hedge-comment` ("Note: this assumes...", "As an AI, I..."), `ai-self-praise-comment` ("Pythonic", "idiomatic", "elegant", "clean code"), `ai-emoji-in-code` (Unicode So/Sk in comments + identifiers; string literals exempt). Multi-language ports tracked in TODOS for v2.1.
- **3 OWASP-3 Python security rules** (severity=warning at v1; promotion to error gated on telemetry FP-rate in v2.1): `shell-true-with-variable`, `pickle-loads-on-non-constant`, `eval-or-exec-on-non-constant`. Constants explicitly allowed (no taint analysis at v1; documented in HONESTY_AUDIT).
- **Declarative JSONL rule engine** (`aidoctor.engine.declarative`) — 3 detect kinds (`comment_regex`, `source_unicode_category`, `ast_call_with_kwarg`) + a `python` escape hatch for flow-sensitive rules. Reduces the cost of a new rule from a Python file to a JSONL line.
- **4 fix kinds** (`aidoctor.engine.fixes`): `strip_label`, `delete_emoji`, `strip_comment`, `template_replacement`. Each returns a `RewriteResult(ok, original_code, replacement_code, line_range, reason_if_failed)` — the locked API contract.
- **Public Python API** at the top-level package: `aidoctor.scan_paths(paths) → ScanResult`, `ScanResult.score`, `ScanResult.to_dict()`, `ScanResult.to_json()`. SemVer applies; deprecations get one minor-version warning before removal.
- **Central error renderer** (`aidoctor.engine.error_renderer`) — every rescue site routes through one formatter so exception class, attempted operation, file:line, and remediation hint stay consistent across the codebase.
- **`aidoctor install --pre-commit`** — one-command idempotent `.pre-commit-config.yaml` generator. Marker-based replace ensures re-running updates the rev cleanly without duplicating the block.
- **`aidoctor doctor`** — diagnostics subcommand prints version + Python + platform + per-manifest rule counts. Paste-this-when-filing-a-bug helper.
- **`/aidoctor:welcome` onboarding skill** — 60-second live demo of `/deai` on a planted slop file. Marker-tracked first-run UX.
- **`--jsonl` streaming output** — one JSON object per line for `jq`/`grep`/log-aggregator pipelines. Summary record always last.
- **`Severity.CRITICAL`** — new severity tier above ERROR. Caps score at 39 ("Critical") when any critical-severity rule fires; reserved for the OWASP-class sinks once promoted from warning in v2.1.

### Changed (breaking)

- **`aidoctor scan --fail-on` default is now `error`** (was: `none`). Files with `error`-severity violations now fail CI by default — this closes the v1.1 "broken CI integration" bug Maya's persona flagged. Use `--fail-on=none` to preserve v1.x behavior.
- **Score caps:** any `error`-severity rule firing now caps the score at 69 ("Needs work"). Any `critical`-severity rule firing caps at 39 ("Critical"). Closes the v1.1 trust bug where files with hardcoded payment keys + RCE scored 88 "Great" (flagged by 3 of 8 personas independently).
- **`/aidoctor:help` rewritten** — now leads with `/aidoctor:deai` as the headline + lists 8 invocation paths including pre-commit hook setup.
- **Brand reframing** — the README/CHANGELOG/pyproject description now positions aidoctor as "the coding harness that removes AI fingerprints" rather than "Python AI-slop linter."

### Internal architecture

- **Skill-first declarative rule architecture** (locked mid-CEO-review): the SKILL.md is the product; rule logic lives in JSONL manifests + small Python core. ~8 Python modules cover all 33 rules (vs ~33 Python files if we'd stayed with one-file-per-rule).
- **`rules_complex/security.py`** — 3 OWASP detectors registered with the declarative engine via the python escape hatch. Auto-registers on import; multiprocess-safe (workers re-import).
- **`Category.AI_STYLE` + `Category.SECURITY`** — new categories alongside the v1.1 8.
- **Tests:** added 91 tests across `test_public_api`, `test_error_renderer`, `test_declarative_engine`, `test_fixes`, `test_security_rules`, `test_ai_style_rules`, `test_deai_cli`, `test_install_pre_commit`, `test_doctor_cli`. Full suite: 282 passing, 0 regressions.

### Validation evidence

| Pack | Rules | Method | Status |
|---|---|---|---|
| ai_style (declarative) | 5 | Single-line trigger (deterministic regex/unicode match) | Direct |
| owasp.jsonl (Python) | 3 | Manual fixture (constant-vs-non-constant) | Direct + Bandit overlap (B602/B301/B307) |
| Existing v1.1 25 Python | 25 | iteration-1/2/3 A/B (unchanged) | Retained from v1.1 |

### Not in v2.0 (tracked in TODOS for v2.1)

- ai_style rules ported to Rust/Go/JS/TS (detection works via declarative engine once tree-sitter scanners ship)
- Tree-sitter scanners for Rust/Go/JS/TS (detection layer; rule packs are detection-ready)
- OWASP-3 ported to Rust/Go/JS/TS
- Per-context AST rewriter for `/deai` apply (v2.0 ships agent-applied fixes via skill markdown)
- `aidoctor explain <rule-id>` LLM-coached fixes (BYO key)
- `aidoctor challenge` two-agent head-to-head
- ai-doctor.dev/leaderboard
- Workflow skills (`/plan`, `/tdd`, `/debug`, `/review`, `/refactor`, `/ship`)
- `/aidoctor:behaviors` + `install --rules`
- Hosted `explain` free tier (Cloudflare Worker proxy)
- 5 more Python ai_style rules via python escape hatch (inflated-print, useless-docstring, generic-vars-in-long-fn, obvious-type-annotation, explanation-comment)

These are scoped in `~/.gstack/projects/doctor/ceo-plans/2026-05-12-superpower-layer.md` — the CEO+eng review plan that drove this release.

## [1.1.0] — 2026-05-11

### Three new language rule packs — Rust, JS/TS, Go

AIDoctor v1.1 expands from 2 language rule packs (Python, React) to **5** (adds Rust, JS/TS, Go). 107 rules across 5 languages, all validated through A/B testing against trapped prompts.

### Added

- **`rust-rules` SKILL** — 22 Rust rules across error handling (unwrap-in-prod, panic-on-input, stringly-typed-error, mutex-poison-ignored, index-slice, option-result-bool-trap), memory safety (unsafe-without-safety-comment, transmute-misuse), type system (integer-cast-truncation, floating-point-eq, lifetime-overengineering), performance (unnecessary-clone, collect-then-iter, string-concat-in-loop), idioms (string-when-str-works, needless-return, match-single-arm, trait-object-when-generic-works, derive-omission), and async (block-in-async, block-on-in-async, allow-clippy-blanket). Validated by iteration-5 A/B test (5/5 baselines tripped traps, 5/5 with_skill avoided).
- **`js-rules` SKILL** — 21 JS/TS rules covering types (any-everywhere, as-cast-hiding-error, as-any-double-cast, ts-ignore-without-reason, non-null-assertion, untyped-function-param, enum-instead-of-union), async (floating-promise, promise-chain-instead-of-await, await-in-loop, unhandled-rejection-then), error handling (empty-catch, catch-any-implicit, throw-non-error), idioms (var-instead-of-const, loose-equality, callback-hell, console-log-shipped), and modules (unused-import, default-export-mixed, magic-string-import-path). React is excluded — covered by `react-rules`. Validated by iteration-6 (4/5 baselines tripped — one resisted, graded MEDIUM in honesty audit).
- **`go-rules` SKILL** — 20 Go rules: error-ignored, error-not-wrapped, error-string-comparison, panic-in-library, goroutine-leak, loop-var-capture, mutex-by-value, channel-unbuffered-send, context-not-propagated, interface-pointer-return, stuttering-name, getter-prefix, empty-interface-any, init-abuse, slice-append-aliasing, string-concat-loop, make-without-capacity, stub-comment, hardcoded-secret, time-now-in-test. Validated by iteration-7 (5/5 baselines tripped — strongest evidence of the three iterations).
- **`evals/HONESTY_AUDIT.md`** — per-rule HIGH/MEDIUM/LOW confidence grading with baseline evidence quoted. 35 HIGH rules across the three new packs, the spine of the catalog. LOW rules retained as defensive coverage but flagged so we don't oversell.
- **`evals/iteration-5-rust/`, `iteration-6-js/`, `iteration-7-go/`** — full A/B test artifacts: 30 subagent outputs (5 prompts × 3 languages × 2 conditions), benchmark.json, REPORT.md per language.

### Changed

- Brand prose now uses **AIDoctor** (capitalized) consistently in README, CHANGELOG, plugin descriptions, and marketplace listing. CLI binary, Python package name, and slash-command prefix stay lowercase (`aidoctor scan`, `pip install aidoctor`, `/aidoctor:scan`).
- README hero updated to name all 5 rule packs explicitly with rule counts (Python 25, React 19, Rust 22, JS/TS 21, Go 20 — 107 total).
- README install table expanded to include Rust/JS/Go auto-load entries.
- Plugin marketplace description and tags updated for the multi-language scope.

### Validation evidence

| Language | Iteration | Baselines tripped | With-skill avoided | False positives |
|---|---|---|---|---|
| Rust | 5 | 5/5 | 5/5 | 0 |
| JS/TS | 6 | 4/5 | 5/5 | 0 |
| Go | 7 | 5/5 | 5/5 | 0 |

The eval-2 JS baseline correctly resisted `js-floating-promise` — documented in the honesty audit as a MEDIUM-confidence rule rather than HIGH. We did not strengthen the trap to force compliance; that would have invalidated the signal.

## [1.0.0] — 2026-05-11

### Pivot — aidoctor is now a multi-language skill pack

aidoctor v1.0 is a coding harness for AI agents, distributed as a Claude Code plugin and per-agent skill files for Cursor, Codex, Gemini CLI, OpenCode. **The CLI is deprecated as the primary surface; the v0.2.0 wheel is unpublished and shelved.** Skills are the product. v2.0+ may revive a CLI for deterministic verification.

### Added

- `react-rules` SKILL — 19 React/JSX rules covering state & effects, performance, architecture, security, accessibility, dead code. Rule semantics lifted from [react-doctor](https://github.com/millionco/react-doctor) (MIT, attribution in `THIRD_PARTY_LICENSES`).
- Iteration-4 validation evidence: 5/5 React prompts improved with skill, 0 regressions, 0 false positives. Report in `evals/iteration-4-react/REPORT.md`.
- LLM-only fallback documented in `simplify` and `audit` SKILL.md: for languages without a rule pack, the orchestration skills fall back to general code review patterns.
- `THIRD_PARTY_LICENSES` file with react-doctor MIT attribution.
- `docs/specs/2026-05-11-skill-pack-pivot-design.md` — design doc explaining the pivot.

### Changed

- Brand position: "Multi-language coding harness for AI agents" (was "Python coding harness").
- Plugin marketplace description names the multi-language scope: deep packs for Python + React, LLM-only for everything else, JS/Rust/Go on the roadmap.
- README hero rewritten to articulate the moat: "AI-slop removal in any code + opinionated robust, production-grade, non-overengineered patterns."

### Deferred to v2.0+

- `aidoctor scan` CLI as deterministic verifier
- PyPI publication of v0.2.0+ (v0.1.0 stays live for the few CLI users)
- tree-sitter / libcst parsers
- GitHub Action surface
- Score formula / leaderboard
- VS Code extension

## [0.2.0] — 2026-05-11 (UNRELEASED — skill-pack pivot superseded this)

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
