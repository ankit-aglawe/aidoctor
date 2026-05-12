<p align="center">
  <img src="https://raw.githubusercontent.com/ankit-aglawe/aidoctor/main/docs/banner.png" alt="aidoctor" width="660" />
</p>

> Your agent writes bad code. `/aidoctor:deai` finds the AI fingerprints and removes them.

**AIDoctor is the coding harness with a deterministic verifier under it.** New in v2.0:

1. **`/aidoctor:deai` — the moat skill.** Detects the *visible* AI tells in your code (`# NOTE:` / `# IMPORTANT:` emphasis labels, `# ====== SECTION ======` ASCII dividers, self-praise comments like `# Pythonic`/`# elegant`, hedge leakage like `# As an AI, I...`, emojis in source code), proposes a deterministic AST-driven fix for each, and applies them with per-finding user approval. Python at v2.0; multi-language in v2.1 (the rules are language-agnostic; the apply layer lands with the tree-sitter scanner).
2. **`/aidoctor:scan` — calibrated AI-slop linter.** 33 Python rules across 10 categories (bare `except`, hardcoded secrets, async/sync mismatch, the new 3 OWASP-3 security sinks, the 5 ai_style rules, and more). New in v2.0: score caps when `error`-severity rules fire (any error → 69; any critical → 39), `--fail-on=error` is the default so CI works out of the box, `--jsonl` streams findings for `jq`/`grep` pipelines.
3. **Skill packs for other languages.** React, Rust, JS/TS, Go — 78 rules across 4 packs steering Claude Code / Cursor / Codex / Gemini at generation time. v2.1 brings these into the deterministic scanner via tree-sitter.

Works across **Claude Code, Cursor, Codex, Gemini CLI, OpenCode.** Same skill catalog, every major agent.

[Install](#install) · [CLI](#cli) · [Rules](#what-it-catches) · [Leaderboard](#leaderboard) · [vs alternatives](#how-it-differs)

## Install

Install differs by harness. If you use more than one, install aidoctor separately for each.

### Claude Code

Register the marketplace and install the plugin:

```
/plugin marketplace add ankit-aglawe/aidoctor
/plugin install aidoctor@ankit-aglawe
```

After install, just talk to Claude in plain English. Thirteen skills load:

| You want to | Invoke | Or say |
|---|---|---|
| **Remove visible AI fingerprints** | **`/aidoctor:deai`** | "deai this file", "remove AI tells" |
| **Get oriented (first time)** | `/aidoctor:welcome` | "show me aidoctor", "demo it" |
| **Write** Python (no action needed) | `python-rules` auto-loads | n/a |
| **Write** React (no action needed) | `react-rules` auto-loads | n/a |
| **Write** Rust (no action needed) | `rust-rules` auto-loads | n/a |
| **Write** JS/TS (no action needed) | `js-rules` auto-loads | n/a |
| **Write** Go (no action needed) | `go-rules` auto-loads | n/a |
| **Lint** one file or path | `/aidoctor:scan` | "scan this", "lint my code" |
| **Review** your last diff | `/aidoctor:simplify` | "review what I just changed" |
| **Audit** the whole repo | `/aidoctor:audit` | "audit this repo", "is it prod-ready?" |
| **Browse** the rule catalog | `/aidoctor:rules` | "list AIDoctor rules" |
| **Get oriented (the catalog)** | `/aidoctor:help` | "how do I use AIDoctor?" |
| **Add the pre-commit hook** | `aidoctor install --pre-commit` | "set up the git hook" |

Lost? Type `/aidoctor:help` for the full decision tree.

For languages without a rule pack (Java, Kotlin, C#, Ruby, PHP, Swift, etc.), the orchestration skills (`scan`, `simplify`, `audit`) fall back to LLM-only review — still useful, just less language-specific.

### Cursor

In Cursor Agent chat:

```
/add-plugin aidoctor
```

Or run `uvx aidoctor install` once — it writes `~/.cursor/rules/aidoctor.mdc`.

### Codex CLI

Drop the rules file into Codex's config dir:

```bash
uvx aidoctor install
```

Writes `~/.codex/skills/aidoctor.md`. Codex reads it automatically when generating Python, React, Rust, JS/TS, or Go.

### Gemini CLI

```bash
uvx aidoctor install
```

Writes `~/.gemini/skills/aidoctor.md`.

### OpenCode

```bash
uvx aidoctor install
```

Writes `~/.config/opencode/rules/aidoctor.md`.

### Any other agent (Aider, Copilot, custom)

```bash
uvx aidoctor skill --format generic > my-agent/rules/aidoctor.md
```

Or paste this prompt into the agent:

> **Install aidoctor and run my first scan.**
>
> 1. Run `uvx aidoctor install` (or `pip install aidoctor && aidoctor install` if `uvx` is missing).
> 2. Run `uvx aidoctor scan .` in the current project.
> 3. Summarize in one paragraph: (a) the score out of 100 and its label, (b) the top 3 rule violations and what each means in plain English, (c) whether to fix errors or warnings first.
> 4. Do not modify any files. Stop after the summary.

## CLI

> The skill harness is the primary surface. The CLI on PyPI is `aidoctor 2.0.0` — Python-only deterministic scanner (33 rules: 25 legacy + 3 OWASP-3 + 5 ai_style) with full `aidoctor deai` / `aidoctor doctor` / `aidoctor install --pre-commit` subcommands. Multi-language deterministic scanning (Rust, Go, JS/TS) ships in v2.1 on a tree-sitter backbone — the rule packs for those languages currently steer agents at generation time via `*-rules` SKILL packs.

For humans and CI (Python projects only):

```bash
uvx aidoctor scan .             # zero-install
uv tool install aidoctor        # persistent (2026-native)
pipx install aidoctor           # isolated
pip install aidoctor            # classic / CI
```

Then:

```bash
aidoctor scan .                       # full repo
aidoctor scan src/ tests/             # specific paths
aidoctor scan --diff                  # only lines you've changed
aidoctor scan-pr https://github.com/owner/repo/pull/42
aidoctor scan --explain bare-except-pass    # docs for one rule
```

No signup. No API key. No telemetry. Runs entirely on your machine.

## What it catches

**107 rules across 5 languages.** Each rule has a stable ID (`bare-except-pass`, `rust-unwrap-in-prod`, `go-error-ignored`, `js-any-everywhere`, `react-key-as-index`) that appears identically in skill markdown, scan output, and slash commands — so an agent can cite a finding back to you and you can cite one back to the agent.

| Language | Pack | Highlights |
|---|---|---|
| **Python** (25 rules) | `python-rules` | bare `except: pass`, hardcoded API keys, sync I/O in async fn, `Any` everywhere, `range(len(x))`, nested-loop append, wildcard imports, stub comments shipped as code |
| **React** (19 rules) | `react-rules` | key-as-index, stale closures in effects, missing dependency arrays, `dangerouslySetInnerHTML` without sanitization, `useState` of derived value, prop-drilling beyond 3 levels |
| **Rust** (22 rules) | `rust-rules` | `.unwrap()` in production fn, `.clone()` everywhere, `Result<T, String>` instead of typed error, `.lock().unwrap()` panic cascade, lifetime overengineering, blocking I/O in async |
| **JS/TS** (21 rules) | `js-rules` | `any` everywhere, `as User` cast bypassing validation, callback hell, floating promises, empty catch, untyped function params, `@ts-ignore` without reason |
| **Go** (20 rules) | `go-rules` | `data, _ := ` discarding errors, goroutine leak (no context), `panic` in library, value-receiver mutex, `append(items, ...)` without assign, error not wrapped with `%w` |

Honesty: rules are graded HIGH/MEDIUM/LOW for AI-slop confidence in `evals/HONESTY_AUDIT.md`. The HIGH ones are the spine — proven across iter-1..7 A/B tests against trapped prompts. The LOW ones are defensive coverage.

For languages without a rule pack (Java, Kotlin, C#, Ruby, PHP, Swift, etc.), the orchestration skills (`scan`, `simplify`, `audit`) fall back to LLM-only review.

## Score

`aidoctor scan` outputs a 0–100 health score. The score penalizes the *number of unique rules tripped*, not raw violation count — so fixing one category moves the number, instead of chasing per-line totals.

| Band | Label |
|---|---|
| 90–100 | Healthy |
| 70–89 | Needs work |
| 0–69 | Critical |

Same formula on every machine. Same formula in CI.

## Slash commands

In Claude Code, the plugin installs `/aidoctor:scan` (run a scan + summary). In OpenCode and Gemini CLI, `aidoctor install` drops a global `/aidoctor` command. Cursor and Codex don't support custom slash commands; the rules file is the install vector there.

## GitHub Action

```yaml
- uses: ankit-aglawe/aidoctor-action@v1
  with:
    fail-on: error      # error | warning | none
```

Or call the CLI directly in any workflow:

```yaml
- run: uvx aidoctor scan . --fail-on error
```

Pre-commit (one-liner setup):

```bash
aidoctor install --pre-commit       # writes the block below, idempotent
pre-commit install                  # activates the hook in .git/hooks/
```

Or manually:

```yaml
repos:
  - repo: https://github.com/ankit-aglawe/aidoctor
    rev: v2.0.0
    hooks:
      - id: aidoctor              # diff mode (only scans changed files)
        args: [--fail-on, error]
```

## Configuration

aidoctor reads `[tool.aidoctor]` in `pyproject.toml` if present. The defaults are designed to be useful without any config.

```toml
[tool.aidoctor]
exclude = ["migrations/", "vendor/"]
fail-on = "error"
```

### Inline suppression

```python
# aidoctor: disable=hardcoded-api-key
API_KEY = "sk-test-not-real"
```

Variants:

```python
foo()  # aidoctor: disable-line=range-len-loop
```

```python
# aidoctor: disable-file=stub-comment,todo-without-ticket
```

Multiple rules: `# aidoctor: disable=rule-1,rule-2`.

## How it differs

|  | aidoctor | Ruff | Sloppylint | CodeRabbit |
|---|---|---|---|---|
| Catches AI-author patterns specifically | ✓ | partial | ✓ | ✓ |
| Stable rule IDs | ✓ | ✓ | — | per-customer |
| Installs a skill in your agent | ✓ | — | — | — |
| Runs locally, no cloud | ✓ | ✓ | ✓ | — |
| Free CLI | ✓ | ✓ | ✓ | $24/seat/mo |
| Per-PR scan | ✓ (`scan-pr`) | via Action | — | ✓ |

Ruff / Clippy / staticcheck / typescript-eslint are the right tools for correctness. AIDoctor is the right tool for the specific failure modes LLMs have across all five supported languages — patterns that pass those linters on default settings but break in production. Same harness, five languages.

## Leaderboard

How major open-source projects score across Python, React, Rust, JS/TS, and Go:

| Repo | Language | Score | Top issues |
|---|---|---|---|
| _coming at launch_ | — | — | — |

Want your project listed? [Open a PR](https://github.com/ankit-aglawe/aidoctor/pulls) adding it to `leaderboard.yaml`.

## Roadmap

- [x] Claude Code plugin via `/plugin marketplace add ankit-aglawe/aidoctor` (v0.1+)
- [x] 7-skill catalog: scan, simplify, audit, rules, help, using-aidoctor, python-rules (v0.2)
- [x] **`react-rules` SKILL pack** — patterns lifted from [react-doctor](https://github.com/millionco/react-doctor) (MIT) with attribution (v1.0)
- [x] **`rust-rules` SKILL pack** — 22 rules across error handling, memory, type system, performance, idioms, async (v1.1)
- [x] **`js-rules` SKILL pack** — 21 language-level JS/TS rules across types, async, error-handling, idioms, modules (v1.1)
- [x] **`go-rules` SKILL pack** — 20 rules across error-handling, concurrency, idioms, performance, ai-slop-specific (v1.1)
- [ ] **`vue-rules`, `next-rules`, `java-rules`, `swift-rules`, etc.** — family pattern. Each language/framework is its own rule SKILL; orchestration skills stay shared
- [ ] Tree-sitter backbone in CLI for multi-language deterministic scan
- [ ] Listed on the official Anthropic plugin marketplace
- [ ] MCP server (`aidoctor mcp`) so Cursor / Windsurf / Codex / Gemini reach the rules over a single transport
- [ ] `aidoctor learn` — propose project-local rules from your git history
- [ ] PR-delta scoring on GitHub Action

Want a language we haven't shipped yet? Upvote / open an issue. We build the next rule pack when there's signal.

## Credits

Inspired by [react-doctor](https://github.com/millionco/react-doctor) by [@aidenybai](https://twitter.com/aidenybai). Built for the era where most code isn't written by humans anymore.

## License

MIT
