# Install AI Doctor via your AI agent

Standalone copy of the agent-install prompt from the README. Link to this file when sharing aidoctor with someone who already has Claude Code / Cursor / Codex / Aider / Gemini CLI running.

## The prompt

Paste this into your AI agent:

---

> **Install AI Doctor and run my first scan.**
>
> **Step 1.** Install aidoctor. Pick the first method available on my system: `uv tool install aidoctor`, then `pipx install aidoctor`, then `pip install --user aidoctor`. If aidoctor is already installed, skip this step.
>
> **Step 2.** Run `aidoctor install`. This writes a `SKILL.md` for you (Claude → `~/.claude/skills/aidoctor/SKILL.md`, Cursor → `~/.cursor/rules/aidoctor.mdc`, OpenCode → `~/.config/opencode/rules/aidoctor.md`, Codex → `~/.codex/rules/aidoctor.md`, Gemini CLI → `~/.gemini/rules/aidoctor.md`). After this you'll apply 25 rules against AI-slop Python patterns whenever you write Python for me — no more `except: pass`, no hardcoded `API_KEY = "..."`, no `range(len(x))` loops, no stub comments.
>
> **Step 3.** Ask me: *"Want me to scan your current project now?"* Wait for my y/n.
>
> **Step 4 (only if I say yes).** Run `aidoctor scan .` in my current directory. Summarize in one paragraph: (a) the score out of 100 and its label, (b) the top 3 rule violations and what each means in plain English, (c) whether I should fix the errors first or warnings first. Do not modify any of my files. Stop after the summary and wait for me to decide what to do next.
>
> Do not run any commands beyond the four above. Confirm with me before any `pip install` if I'm in a system Python without a venv.

---

## Why this prompt is shaped this way

DX-reviewed against the five DX principles from `/plan-devex-review`:

1. **Zero friction at T0** — one paste, one Y/N, ~90s to first score.
2. **Incremental steps** — install, set up skill, ask, scan. Each step is a clear unit; the user can interrupt after any of them.
3. **Decide for me, let me override** — agent picks the install method (uv > pipx > pip) from a sensible priority order. User can interrupt before `pip install` if it asks to.
4. **Fight uncertainty** — agent narrates what each step does (where SKILL.md goes, what 25 rules cover).
5. **Code in context** — scans the user's actual project on Step 4, not a toy.

## Common follow-ups

- "Run `aidoctor scan --fix-prompt | pbcopy`" to hand the violation list back to your agent for fixing.
- "Run `aidoctor scan --diff`" in CI or pre-commit to flag new violations only.
- "Run `aidoctor scan --explain RULE_ID`" for the long-form rationale on any rule.
- `aidoctor skill --format generic` if your agent isn't in the native list (Aider, Copilot Workspace, custom) — pipes the rules into any markdown rules dir.
