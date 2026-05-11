---
name: simplify
description: Review just-changed Python code for reuse, quality, and efficiency — then fix the issues. Use whenever the user asks to simplify, clean up, refactor, dedupe, tighten, polish, or "review what I just changed" / "are there issues with this diff?" / "is this over-engineered?". Spawns three parallel reviewer subagents (reuse / quality / efficiency), aggregates findings, and applies fixes directly.
allowed-tools: Bash(git diff*), Bash(git status*), Bash(aidoctor *), Read, Edit, Write, Grep, Task
---

# aidoctor simplify

A three-angle review of recently-changed Python code, then a fix pass. Modeled after the original `/simplify` skill but specialized for Python and integrated with aidoctor's rule taxonomy.

## Phase 1 — Identify changes

Run `git diff` (or `git diff HEAD` if there are staged changes) to see what changed in this session. If there are no git changes, fall back to the files the user mentioned in the conversation or that you edited earlier.

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
8. **Any aidoctor rule violations** — run `aidoctor scan` on the changed files and include findings.

### Reviewer 3 — Efficiency

Review for efficiency issues:
1. **Unnecessary work**: redundant computations, repeated file reads, duplicate API calls, N+1 patterns.
2. **Missed concurrency**: independent operations run sequentially when they could be parallel.
3. **Hot-path bloat**: new blocking work added to startup or per-request paths.
4. **Recurring no-op updates**: unconditional state writes inside loops or event handlers — add a change-detection guard.
5. **Unnecessary existence checks**: `path.exists()` before opening (TOCTOU) — try/except is safer.
6. **Memory**: unbounded data structures, missing cleanup, leaked listeners.
7. **Overly broad operations**: reading entire files when only a portion is needed.

## Phase 3 — Aggregate and fix

Wait for all three reviewers. Combine findings, deduplicate, and fix each issue directly. If a finding is a false positive or not worth addressing, note it and skip — do not argue with the reviewer, just move on.

After fixing: re-run `aidoctor scan` on the changed files to confirm the score didn't regress.

## Phase 4 — Summarize

One paragraph: what was fixed, what was skipped (and why), and whether the diff is now ready. If the code was already clean, say so — don't manufacture findings.
