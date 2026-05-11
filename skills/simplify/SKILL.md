---
name: simplify
version: 0.1.0
description: Review just-changed code for reuse, quality, and efficiency — then fix the issues. Use whenever the user asks to simplify, clean up, refactor, dedupe, tighten, polish, or "review what I just changed" / "are there issues with this diff?" / "is this over-engineered?". Spawns three parallel reviewer subagents (reuse / quality / efficiency), aggregates findings, and applies fixes directly. Language-agnostic orchestration; Python rules deepest today.
triggers:
  - simplify this
  - simplify what I just changed
  - clean up this diff
  - review what I changed
  - is this over-engineered
  - dedupe this
  - tighten this
  - polish my changes
benefits-from: [scan, python-rules]
allowed-tools: Bash(git diff*), Bash(git status*), Bash(aidoctor *), Read, Edit, Write, Grep, Task
---

# aidoctor simplify

A three-angle review of recently-changed Python code, then a fix pass. Modeled after the gstack `autoplan` reviewer pipeline but parallel (three independent angles) instead of sequential (gstack chains CEO → Design → Eng → DX, but we have three independent lenses on the same diff).

## Language scope

`simplify` works on **any code**. The three-reviewer framework (reuse / quality / efficiency) is language-agnostic.

When the diff includes Python, additionally invoke `aidoctor scan` on the changed files for deterministic rule-grounded findings (current rule pack: Python). When the diff is in a language without an aidoctor rule pack (JS, Rust, Go, etc.), skip the scan step and rely on the three reviewers' qualitative review alone. Note this in your Phase 5 summary: *"LLM-only review (no rule pack for &lt;language&gt; yet)."*

This fallback is the design: rules-where-available, LLM-where-not.

## Iron Law

```
NO FIX WITHOUT ALL THREE REVIEWERS RETURNED + USER GO-AHEAD
```

A reviewer that returns last often catches the highest-severity issue. Starting to fix on partial output means you miss it. **Spirit over letter** — "I'll just start fixing the easy ones" violates this rule the same as "I'll skip waiting."

## Step 0 — Announce

Print one line: `aidoctor /simplify — diff against HEAD, dispatching 3 reviewers (reuse / quality / efficiency).` Then proceed.

## Phase 1 — Identify changes

Run `git diff` (or `git diff HEAD` if there are staged changes) to see what changed in this session. If there are no git changes, fall back to the files the user mentioned in the conversation or that you edited earlier.

If the diff is empty across both unstaged and staged: **STOP**. Tell the user: *"No changes detected. /simplify works on a diff. If you want a full-repo review, use /scan instead."*

## Phase 2 — Launch three reviewer subagents in parallel

Use the Task tool to spawn all three reviewers concurrently in a single message. Pass each one the full diff. Each reviewer is honest and surgical, NOT defensive.

### Reviewer 1 — Code Reuse

For each change:
1. Search for existing utilities, helpers, or constants that could replace newly written code. Look in adjacent files, shared modules, and `utils/` / `lib/` dirs.
2. Flag any new function that duplicates existing functionality. Name the existing function to use instead.
3. Flag any inline logic that could use an existing utility — hand-rolled string manipulation, manual path handling, custom env checks, ad-hoc type guards.

### Reviewer 2 — Code Quality

Review for hacky patterns and aidoctor-rule violations:
1. **Redundant state**: state that duplicates existing state, cached values that could be derived, observers that could be direct calls.
2. **Parameter sprawl**: new parameters added instead of restructuring.
3. **Copy-paste with slight variation**: near-duplicate blocks that should share a helper.
4. **Leaky abstractions**: exposing internals that should stay encapsulated.
5. **Stringly-typed code**: raw strings where enums or constants exist.
6. **Nested conditionals 3+ levels deep**: flatten with early returns, guard clauses, or a lookup table.
7. **Unnecessary comments**: explaining WHAT (well-named identifiers already do that) or narrating the change. Delete; keep only non-obvious WHY.
8. **Any aidoctor rule violations** — run `aidoctor scan` on the changed files and include findings with `rule_id`.

### Reviewer 3 — Efficiency

Review for efficiency issues:
1. **Unnecessary work**: redundant computations, repeated file reads, duplicate API calls, N+1 patterns.
2. **Missed concurrency**: independent operations run sequentially when they could be parallel.
3. **Hot-path bloat**: new blocking work added to startup or per-request paths.
4. **Recurring no-op updates**: unconditional state writes inside loops or event handlers — add a change-detection guard.
5. **Unnecessary existence checks**: `path.exists()` before opening (TOCTOU) — try/except is safer.
6. **Memory**: unbounded data structures, missing cleanup, leaked listeners.
7. **Overly broad operations**: reading entire files when only a portion is needed.

## STOP — Pre-Phase 3 checklist

Before you begin fixing anything, **STOP** and verify:

- [ ] All three reviewer subagents returned (no partial output)
- [ ] Findings deduplicated (same issue surfaced by two reviewers = one fix)
- [ ] Phase-transition summary emitted (see template below)
- [ ] User notified via decision brief and confirmed which findings to fix

If any box is unchecked: do not start editing. Wait.

### Phase 2 → Phase 3 transition summary

Emit this one-liner before continuing: *"Phase 2 complete. Reuse: N findings. Quality: N findings. Efficiency: N findings. Total unique: M. Beginning decision brief."*

## Phase 3 — Decision brief

Ask the user which findings to fix, using the gstack decision-brief format:

```
D1 — Which findings should I fix?
ELI10: The three reviewers flagged M unique issues across reuse / quality / efficiency. Some are clear wins (duplicate code → existing helper); some are taste calls (one of the reviewers thinks this nested ternary is fine).
Recommendation: A because the consensus findings are the highest-confidence wins

A) Fix only findings flagged by 2+ reviewers (recommended)
  ✅ Highest signal-to-noise; minimal taste-call risk; small focused diff
  ❌ May skip a real-but-single-source finding worth fixing
B) Fix all M unique findings
  ✅ Cleanest result; addresses everything raised
  ❌ Bigger diff to review; some single-source findings may be reviewer noise
C) Show me the list, I'll pick
  ✅ Full control; I choose each fix
  ❌ Slower; more back-and-forth

Net: A is the safe default; pick C when the diff is sensitive or commit-history matters.
```

Adapt M to the real total.

## Phase 4 — Fix

Apply fixes per the user's choice. One reviewer's finding at a time. Do not batch unrelated changes into a single edit — keep the diff reviewable.

When a finding is a borderline taste call (e.g., "this is YAGNI but the user just wrote it"), surface a mini-brief instead of silently skipping:

```
D<n> — Apply this fix or skip?
Finding: <reviewer> says <verbatim quote>
ELI10: <one-line plain-English>
Recommendation: <apply | skip> because <reason>
```

After fixing: run `aidoctor scan` on the changed files. If the score did not move up, surface what didn't fix.

## Phase 5 — Summarize

One paragraph: what was fixed, what was skipped (and why), what the new aidoctor score is. If the code was already clean, say so — don't manufacture findings.

## Red flags — STOP

| Thought | Reality |
|---|---|
| "Two reviewers returned, I can start" | NO. Wait for all three. |
| "This finding is obviously right, skip the brief" | Use the brief. Borderline-confidence findings need user input. |
| "I'll batch all fixes into one edit" | Keep each fix isolated. Reviewable diffs > clever batching. |
| "Scan didn't move up but the fixes look right" | Re-read the scan output. Either the fix missed or the rule didn't apply. |
