---
name: scan
version: 0.1.0
description: Scan Python code with aidoctor for AI-slop patterns and report a 0-100 health score. Use whenever the user asks to scan, lint, audit, check, review, score, or grade Python code — or asks "is this AI slop?", "find bad code Claude wrote", or "what's wrong with this Python?". Catches bare except, hardcoded secrets, range(len) loops, stub comments, async/sync mismatch, and 21 other patterns AI coding assistants regularly produce.
triggers:
  - scan this
  - lint my python
  - check this for ai slop
  - is this ai slop
  - score this code
  - grade this python
  - find bugs claude wrote
  - audit this repo
benefits-from: [simplify, python-rules]
allowed-tools: Bash(aidoctor *), Bash(uvx aidoctor*), Bash(pipx run aidoctor*), Read, Grep
---

# aidoctor scan

Run the aidoctor static analyzer on the user's Python code and report what it finds. Honest, concrete, no upsell.

## Iron Law

```
NO SCORE CLAIM WITHOUT FRESH `aidoctor scan` OUTPUT IN THIS MESSAGE
```

If you didn't run `aidoctor scan` in this turn, you cannot report a score. Output from a previous turn is stale — files may have changed. **Spirit over letter** — paraphrasing a remembered score, averaging old runs, or saying "looks healthy" without fresh output is the same violation.

## Step 0 — Announce

Print one line so the user has a visible handle: `aidoctor /scan — running on <paths> (<N> .py files)`. Then proceed.

## Step 1 — Resolve the target

If the user passed arguments (e.g. "scan src/"), use those paths. Otherwise use `.` (current project root).

## Step 2 — Run the scan

Try in order until one works:
- `aidoctor scan <paths>`
- `uvx aidoctor scan <paths>` (if `aidoctor` not on PATH but `uv` is)
- `pipx run aidoctor scan <paths>`

If none work, tell the user: *"aidoctor isn't installed. Fastest install is `uv tool install aidoctor` (or `pip install aidoctor` if you don't have uv). Then re-run."* **STOP.**

If aidoctor exits non-zero with anything other than "no violations" output, **STOP**. Do not fabricate a score. Quote the error verbatim and ask the user to share their Python version and platform.

## Step 3 — Summarize in one paragraph

Read the scan output and write:
- **Score and band:** `X/100 — Healthy / Needs work / Critical` (90+ Healthy, 70–89 Needs work, below 70 Critical).
- **Top 3 rule IDs that fired** (e.g. `bare-except-pass`, `hardcoded-api-key`, `range-len-loop`), each with a one-line plain-English explanation of what it means and why AI agents write it.
- **Where to start:** if any errors exist, fix errors before warnings. Otherwise warnings.

## Step 4 — STOP

Do not modify any files in this turn. Do not begin fixing. **STOP here and wait for the user's go-ahead** via the decision brief in Step 5.

## Step 5 — Ask using a decision brief

Use this exact format — it's the gstack convention the user is fluent in:

```
D1 — Fix the findings now?
ELI10: Your scan found N violations across M categories. Errors are the urgent ones — they fail CI gates. Warnings are sloppy patterns Claude/Copilot tend to write but don't block deploys.
Recommendation: A because errors block CI and warnings are negotiable

A) Fix errors only (recommended)
  ✅ Unblocks CI fast; tight scope; you can review each fix before merging
  ❌ Leaves the N warnings that may compound over time
B) Fix errors and warnings
  ✅ Cleanest result; ships zero-violation code; one pass, done
  ❌ Bigger diff to review; some warnings may be context-dependent skips
C) Skip fixing — show me only
  ✅ I review the list and decide later; no surprises
  ❌ Findings live in the code until the next scan

Net: A is the highest-ROI default. Pick C if you're auditing rather than fixing.
```

Adapt N and M to the real numbers. If only errors exist, drop option B. If only warnings exist, drop option A and re-label.

## Step 6 — Chain to simplify (when relevant)

If the score is below 70 **and** the user has uncommitted changes (`git diff` non-empty) **and** the findings are largely in those changes, recommend chaining to simplify:

*"The findings are mostly in code you just changed. `/aidoctor:simplify` does a three-angle review (reuse / quality / efficiency) and fixes issues in one pass. Want me to chain into it?"*

Otherwise skip — don't suggest simplify on a clean diff or an old repo audit.

## When the user picks A or B (next turn)

Fix one rule's violations at a time. After each rule's fixes, re-run `aidoctor scan` to confirm the score moved up. Never use `# aidoctor: disable=...` to silence a finding without the user's explicit permission — fix the underlying issue.

After the final fix pass, run `aidoctor scan` one more time. Report the new score in the format from Step 3. This is the verification gate.

## Red flags — STOP and re-run

| Thought | Reality |
|---|---|
| "I already ran scan last turn" | Run it again. Files changed. |
| "Score looks low, I'll average them" | Report the actual number. |
| "Some findings look wrong, I'll skip them" | Cite the `rule_id` and ask the user. |
| "I'm sure that file is clean" | Confidence ≠ evidence. Run the scan. |

## Rule reference

Look up any rule by ID:

```bash
aidoctor scan --explain <rule-id>
```

Each rule has a stable identifier that appears identically in scan output, this skill, and the leaderboard — so an agent can cite a finding back to the user and vice versa.
