# AI Doctor

> Your agent writes bad Python. This catches it.

Install command: `pip install aidoctor` · Run: `aidoctor scan .`

A static analyzer for AI-generated Python code. Catches the patterns that AI coding assistants (Claude Code, Cursor, Copilot, Codex) produce: bare `except`, hardcoded secrets, async/sync mismatches, dead defenses, fake type hints, and more. Then installs a skill into your AI agent so it stops writing them in the first place.

![demo](docs/demo.gif)

[Install](#install) · [Demo](#demo) · [Leaderboard](#leaderboard) · [Docs](#how-it-works)

## Quick start

```bash
pip install aidoctor
aidoctor scan .
```

That's it. No signup, no API key, no telemetry.

## Install via your AI agent (one paste)

Don't want to install yourself? Paste the block below into **Claude Code, Cursor, Codex, Aider, or Gemini CLI**. The agent installs aidoctor, sets up the skill in its own config dir, and asks before scanning.

> **Install AI Doctor and run my first scan.**
>
> **Step 1.** Install aidoctor. Pick the first method available on my system: `uv tool install aidoctor`, then `pipx install aidoctor`, then `pip install --user aidoctor`. If aidoctor is already installed, skip this step.
>
> **Step 2.** Run `aidoctor install`. This writes a `SKILL.md` for you (Claude → `~/.claude/skills/aidoctor/SKILL.md`, Cursor → `~/.cursor/rules/aidoctor.mdc`, etc.). After this you'll apply 25 rules against AI-slop Python patterns whenever you write Python for me — no more `except: pass`, no hardcoded `API_KEY = "..."`, no `range(len(x))` loops, no stub comments.
>
> **Step 3.** Ask me: *"Want me to scan your current project now?"* Wait for my y/n.
>
> **Step 4 (only if I say yes).** Run `aidoctor scan .` in my current directory. Summarize in one paragraph: (a) the score out of 100 and its label, (b) the top 3 rule violations and what each means in plain English, (c) whether I should fix the errors first or warnings first. Do not modify any of my files. Stop after the summary and wait for me to decide what to do next.
>
> Do not run any commands beyond the four above. Confirm with me before any `pip install` if I'm in a system Python without a venv.

After install, `aidoctor scan` works from any project directory. Re-run anytime.

## How it works

aidoctor runs 25 rules against your Python code via `libcst`. Each rule targets a pattern AI coding assistants regularly produce. Output is a 0-100 health score with a doctor-face ASCII emoticon, plus violations grouped by category. The score penalizes unique rules tripped, not violation count, so you fix categories of issues rather than chasing line counts.

## Stop AI slop in the first place

```bash
aidoctor install
```

Installs a markdown skill into your AI agent's config directory: **Claude Code, Cursor, OpenCode, Codex, Gemini CLI**. Your agent reads it before generating Python code and avoids the patterns aidoctor catches.

For any other agent (Aider, Copilot Workspace, custom): pipe the rules in.

```bash
aidoctor skill --format generic > my-agent/rules/aidoctor.md
```

### Use `/aidoctor` as a slash command

`aidoctor install` also drops a slash command for the platforms that support it: **Claude Code, OpenCode, Gemini CLI**. After install, just type `/aidoctor` (or `/aidoctor src/`) inside the agent — it runs the scan, summarizes the score in plain English, and asks if you want it to fix the violations. Cursor and Codex don't support custom slash commands, so the rules file is the main vector there.

## What aidoctor catches

| Category | Sample rules |
|----------|--------------|
| AI-Slop Imports | wildcard import abuse, conditional import outside try, duplicate import, import-without-use |
| Dead Defenses | bare `except: pass`, `except Exception` swallowing, unreachable raise after return |
| Async/Sync Mismatch | sync I/O in async fn, `asyncio.run` inside async fn, blocking call in event loop |
| Hardcoded Secrets | API_KEY / TOKEN literals, AWS credentials patterns, JWT-shaped strings |
| Fake Type Hints | `Any` everywhere, missing return type on public fn, Generic without TypeVar |
| Stale Loop Patterns | mutating list during iteration, `range(len(x))`, `time.sleep` in tests |
| N+1 / Performance | nested loop append, repeated dict lookup, `+=` str concat in loop |
| Comment-Driven Decay | TODO/FIXME without ticket, stub comments like `# implement this` |

Full rule docs: `aidoctor scan --explain <rule-id>`.

## Leaderboard

How major Python projects score:

| Repo | Score | Top issues |
|------|-------|------------|
| _coming at launch_ | — | — |

Want your project listed? [Open a PR](https://github.com/aidoctor/aidoctor/pulls) adding it to `leaderboard.yaml`.

## Fixing violations

Tell your AI agent: *"run aidoctor scan and fix what comes up."* The agent already has the SKILL.md installed (after `aidoctor install`), so it knows the rules. It runs the scan, reads the output, applies the fixes. No flag needed.

## Inline suppression

```python
# aidoctor: disable=hardcoded-api-key
API_KEY = "sk-test-not-real"
```

Other forms: `# aidoctor: disable-line=rule-name` (this line), `# aidoctor: disable-file=rule-name` (entire file), `# aidoctor: disable=rule-1,rule-2` (multiple).

## CI integration

GitHub Actions:

```yaml
- uses: aidoctor/aidoctor-action@v1
  with:
    fail-on: error
```

Pre-commit:

```yaml
repos:
  - repo: https://github.com/aidoctor/aidoctor
    rev: v0.1.0
    hooks:
      - id: aidoctor
```

## Why aidoctor

Python is AI's native language. AI assistants write more Python than any other language. They produce predictable failure patterns. This tool catches them.

Inspired by [react-doctor](https://github.com/millionco/react-doctor) by [@aidenybai](https://twitter.com/aidenybai). Built for the AI-coding era.

## License

MIT
