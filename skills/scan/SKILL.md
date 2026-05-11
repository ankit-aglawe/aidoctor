---
name: scan
description: Scan Python code with aidoctor for AI-slop patterns and report a 0-100 health score. Use whenever the user asks to scan, lint, audit, check, review, score, or grade Python code — or asks "is this AI slop?", "find bad code Claude wrote", or "what's wrong with this Python?". Catches bare except, hardcoded secrets, range(len) loops, stub comments, async/sync mismatch, and 21 other patterns AI coding assistants regularly produce.
allowed-tools: Bash(aidoctor *), Bash(uvx aidoctor*), Bash(pipx run aidoctor*), Read, Grep
---

# aidoctor scan

Run the aidoctor static analyzer on the user's Python code and report what it finds. Honest, concrete, no upsell.

## Steps

1. **Resolve the target.** If the user passed arguments (e.g. "scan src/"), use those paths. Otherwise use `.` (current project root).

2. **Run the scan.** Try in order until one works:
   - `aidoctor scan <paths>`
   - `uvx aidoctor scan <paths>` (if `aidoctor` not on PATH but `uv` is)
   - `pipx run aidoctor scan <paths>`

   If none of those work, tell the user: *"aidoctor isn't installed. The fastest install is `uv tool install aidoctor` (or `pip install aidoctor` if you don't have uv). Then re-run."* Stop.

3. **Summarize in one paragraph.** Read the scan output and write:
   - **Score and band:** `X/100 — Healthy / Needs work / Critical` (90+ Healthy, 70–89 Needs work, below 70 Critical).
   - **Top 3 rule IDs that fired** (e.g. `bare-except-pass`, `hardcoded-api-key`, `range-len-loop`), each with a one-line plain-English explanation of what it means and why AI agents write it.
   - **Where to start:** if any errors exist, fix errors before warnings. Otherwise warnings.

4. **Do not modify any files in this turn.** Stop after the summary.

5. **Ask:** *"Want me to fix these? I'll go rule-by-rule starting with the highest severity."*

## When the user says yes (next turn)

Fix one rule's violations at a time. After each rule's fixes, re-run `aidoctor scan` to confirm the score moved up. Never use `# aidoctor: disable=...` to silence a finding without the user's explicit permission — fix the underlying issue.

## Rule reference

Look up any rule by ID:

```bash
aidoctor scan --explain <rule-id>
```

Each rule has a stable identifier that appears identically in scan output, this skill, and the leaderboard — so an agent can cite a finding back to the user and vice versa.
