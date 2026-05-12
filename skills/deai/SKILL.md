---
name: deai
version: 0.1.0
description: Find the AI fingerprints in code and remove them. The moat skill. Use when the user asks to "de-AI", "deai", "remove AI slop", "strip AI patterns", "make this less AI-y", "remove emojis from code", "remove NOTE comments", "this looks AI-generated, fix it", or "clean up the AI tells in this file". Catches the visible AI-style fingerprints (emphasis labels like NOTE/IMPORTANT, ASCII section dividers, hedge leakage, self-praise vocabulary, emojis in source) — not just correctness bugs.
triggers:
  - deai
  - de-AI this
  - remove AI fingerprints
  - remove AI slop
  - strip the AI tells
  - this looks AI-generated fix it
  - remove emojis from code
  - clean up AI patterns
benefits-from: [scan, simplify, audit, python-rules]
allowed-tools: Bash(aidoctor *), Bash(uvx aidoctor*), Bash(pipx run aidoctor*), Read, Edit, Write, Grep
---

# /aidoctor:deai

Find and remove the visible AI fingerprints from code. The headline moat skill.

## What this catches (and what it doesn't)

**Catches (visible AI tells):**
- `# NOTE:`, `# IMPORTANT:`, `# CAREFUL:`, `# CRITICAL:` emphasis labels
- ASCII section dividers (`# ==================== SECTION ====================`)
- Self-praise vocabulary in comments ("Pythonic", "idiomatic", "elegant", "clean code")
- Hedge leakage ("# Note: this assumes…", "# As an AI, I…")
- Emojis in source code (comments, identifiers) — NOT in string literals (those are intentional UX)

**Does NOT catch (use /aidoctor:scan for these):**
- Correctness bugs (bare except, range(len), hardcoded secrets, async/sync mismatch)
- Security issues (shell=True, pickle.loads, eval/exec) — see /aidoctor:scan + the owasp rule pack

The difference matters: `/scan` is "is this code broken?", `/deai` is "does this code LOOK AI-generated?"

## Iron Law

```
NO APPLY WITHOUT FRESH `aidoctor deai` OUTPUT IN THIS MESSAGE
NO APPLY WITHOUT USER GO-AHEAD PER FINDING
```

If you didn't run `aidoctor deai` in this turn, you cannot propose fixes. Output from a previous turn is stale — files may have changed. Every fix is presented to the user for explicit y/N/quit before it lands.

## Step 0 — Announce

Print one line: `aidoctor /deai — finding AI fingerprints in <paths>`. Then proceed.

## Step 1 — Resolve the target

If the user passed paths, use them. Otherwise default to `.` (current project root).

If the user is asking about a specific recent change (e.g., "deai what I just wrote"), use `git diff --name-only` to find the changed files and pass those.

## Step 2 — Run the deai pipeline

Try in order:
- `aidoctor deai <paths> --json`
- `uvx aidoctor deai <paths> --json`
- `pipx run aidoctor deai <paths> --json`

If none work, tell the user: *"aidoctor isn't installed. Fastest: `uv tool install aidoctor` (or `pip install aidoctor` if you don't have uv). Then re-run."* **STOP.**

If the command exits non-zero (it shouldn't — /deai is non-blocking discovery), quote the stderr verbatim and stop.

## Step 3 — Parse and summarize

The JSON has shape:
```
{
  "schema_version": 1,
  "ai_residue_score": <int 0-100>,
  "files_scanned": <int>,
  "findings": [
    {"rule_id": "ai-emoji-in-code", "file": "/abs/path", "line": 42, "column": 10,
     "message": "…", "help": "…", "proposed_fix": {"ok": true, "original_code": "…",
     "replacement_code": "…", "line_range": [42, 42], "reason_if_failed": null}}
  ]
}
```

Tell the user, in this exact shape:

```
aidoctor /deai found <N> AI fingerprint(s) across <M> file(s).
AI residue score: <X>/100  (100 = clean)

  • <K> emphasis labels (NOTE/IMPORTANT/…)
  • <K> ASCII section dividers
  • <K> hedge comments
  • <K> self-praise comments
  • <K> emojis in code
```

Only include category rows that have findings.

## Step 4 — Per-finding apply loop

For each finding with `proposed_fix.ok == true`:

1. Read the file (use `Read` tool) to confirm the line content matches `original_code`. If it doesn't (file was edited since scan), skip with: *"Skipping line N — file changed since scan, re-run /deai."*

2. Present a one-line diff to the user:
   ```
   <file>:<line>  <rule_id>
   - <original_code>
   + <replacement_code>
   Apply this fix? [y/N/q]
   ```

3. If `y`: use `Edit` to apply the replacement on that exact line. Track success.
4. If `N`: skip; record as "rejected by user."
5. If `q`: stop applying; preserve prior accepted fixes; print the partial-results summary and exit Step 4.

For findings with `proposed_fix.ok == false`: print the `reason_if_failed` to the user; do not apply.

## Step 5 — Re-scan and verify

Run `aidoctor deai <paths> --json` again. Compare to Step 2's output:

- If `ai_residue_score` improved and `findings` count dropped by the number of applied fixes: report success.
- If `findings` count is HIGHER (a fix introduced a new finding): tell the user which file changed unexpectedly. Per the rescue rule, do NOT silently revert; ask whether to roll back the offending fix.

Report:
```
aidoctor /deai — done.
  Applied: <K> fix(es).
  AI residue score: <before> → <after>  (delta: +<X>)
  Files modified: <list>
```

## Anti-rationalization rules

If you find yourself saying any of these, **STOP** — they're rationalizations that erode the moat:

| Thought | Reality |
|---|---|
| "The emoji is decorative, it's fine" | The user invoked /deai. They asked for the strip. Strip. |
| "NOTE: is useful context, I'll keep it" | The user invoked /deai. They asked for the strip. Strip. |
| "I'll skip this one because…" | Present the fix, let the user reject if they want. Don't pre-filter. |
| "Let me just apply all the obvious ones first" | Iron Law: per-finding user approval. No batching. |
| "I already manually checked, it's clean" | Run `aidoctor deai`. Output in this message. |

## When NOT to use /aidoctor:deai

- The user is asking about correctness, not style → use `/aidoctor:scan`
- The user wants to review a diff, not strip AI tells → use `/aidoctor:simplify`
- The user wants a whole-repo audit including security + perf → use `/aidoctor:audit`

## Multi-language note (v2.0 → v1.5 roadmap)

At v2.0, `/deai`'s scanner + fixes are Python-only (libcst). The 5 ai_style rules with `comment_regex` + `source_unicode_category` detect kinds are language-agnostic by design and will activate on Rust/Go/JS/TS once tree-sitter scanning ships in v1.5. The agent-applied fix step works in any language — only the detection layer is Python-bound at v2.0.

When scanning a non-Python file at v2.0, /deai will return zero findings and a 100 residue score. That's not "this is clean" — it's "/deai doesn't see this language yet."
