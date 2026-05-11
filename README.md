<p align="center">
  <img src="https://raw.githubusercontent.com/ankit-aglawe/aidoctor/main/docs/banner.png" alt="aidoctor" width="660" />
</p>

> Your agent writes bad code. This catches it.

**AIDoctor is the multi-language coding harness for AI agents.** Two things in one:

1. **AI-slop removal across any code.** Orchestration skills (`scan`, `simplify`, `audit`, `rules`) catch the patterns LLMs reflexively produce — bare `except`, missing cleanup, stale closures, hardcoded secrets, `.unwrap()` in production Rust, `data, _ := ` in Go, `as User` casts in TypeScript, and dozens more. Five language rule packs (**Python, React, Rust, JS/TS, Go — 107 rules**) ground the review in real syntax; the harness reviews qualitatively wherever specifics aren't loaded.
2. **Opinionated robust, production-grade, non-overengineered patterns.** `simplify` spawns three parallel reviewers (reuse / quality / efficiency) to fight over-engineering at the diff level. `audit` applies a six-dimensional review (structure / deps / security / exceptions / standards / coverage) at the project level. Same decision-brief format gstack users already trust.

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

After install, just talk to Claude in plain English. Eleven skills load:

| You want to | Invoke | Or say |
|---|---|---|
| **Write** Python (no action needed) | `python-rules` auto-loads | n/a |
| **Write** React (no action needed) | `react-rules` auto-loads | n/a |
| **Write** Rust (no action needed) | `rust-rules` auto-loads | n/a |
| **Write** JS/TS (no action needed) | `js-rules` auto-loads | n/a |
| **Write** Go (no action needed) | `go-rules` auto-loads | n/a |
| **Lint** one file or path | `/aidoctor:scan` | "scan this", "lint my code" |
| **Review** your last diff | `/aidoctor:simplify` | "review what I just changed" |
| **Audit** the whole repo | `/aidoctor:audit` | "audit this repo", "is it prod-ready?" |
| **Browse** the rule catalog | `/aidoctor:rules` | "list AIDoctor rules" |
| **Get oriented** | `/aidoctor:help` | "how do I use AIDoctor?" |

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

Writes `~/.codex/skills/aidoctor.md`. Codex reads it automatically when generating Python.

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

For humans and CI:

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

25 rules across 8 categories. Each rule has a stable ID (`bare-except-pass`, `hardcoded-api-key`, `range-len-loop`) that appears identically in scan output, the skill markdown, and the slash command — so an agent can cite a finding back to you and you can cite a finding back to the agent.

| Category | Rules |
|---|---|
| **Dead defenses** | bare `except: pass`, `except Exception` swallowing, unreachable raise after return, redundant null-check after `isinstance` |
| **Hardcoded secrets** | API key / token literals, AWS credentials, JWT-shaped strings |
| **Async/sync mismatch** | sync I/O in async fn, `asyncio.run` inside async fn, blocking call in event loop |
| **Fake type hints** | `Any` everywhere, missing return type on public fn, generic without `TypeVar` |
| **Stale loop patterns** | mutate list during iteration, `range(len(x))`, `time.sleep` in tests |
| **Performance** | nested-loop `append`, `+=` string concat in loop, repeated dict lookup |
| **AI-slop imports** | wildcard import, duplicate import, conditional import outside try, import without use |
| **Comment-driven decay** | TODO/FIXME without ticket, stub comments (`# implement this`) shipped as code |

Full rule reference: `aidoctor scan --explain <rule-id>`.

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

Pre-commit:

```yaml
repos:
  - repo: https://github.com/ankit-aglawe/aidoctor
    rev: v0.1.0
    hooks:
      - id: aidoctor
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

Ruff is the right tool for correctness. aidoctor is the right tool for the specific failure modes LLMs have when they write Python — patterns that pass Ruff and mypy on default settings but break in production.

## Leaderboard

How major Python projects score:

| Repo | Score | Top issues |
|---|---|---|
| _coming at launch_ | — | — |

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

Inspired by [react-doctor](https://github.com/millionco/react-doctor) by [@aidenybai](https://twitter.com/aidenybai). Built for the era where most Python isn't written by humans anymore.

## License

MIT
