# Iteration-3 — audit skill validation

Date: 2026-05-11. Built a 5-file test corpus with 22 deliberate issues across 3 tiers (`GROUND_TRUTH.md`). Two subagents audited it — one with no skill (baseline), one with the new `audit` skill loaded. Graded against the curated 22-item truth.

## Headline

> **Both auditors caught 80%+ of ground truth. The skill wins on STRUCTURE not raw catch rate — phases, dedup, tier calibration, decision brief. Baseline catches the same bugs but reports them ad-hoc.**

## Quant

| | Baseline | With audit skill |
|---|---|---|
| Findings caught from 22-item GT | 19 | **21** |
| Catch rate | 86% | **95%** |
| Output length | ~40 lines narrative | ~250 lines structured |
| All TIER-1 security bugs caught? | ✅ Yes (3/3) | ✅ Yes (3/3) |
| Dedup of overlapping findings | No | Explicit (SEC1↔scanner, C2↔scanner) |
| Format | Bullet list, ad-hoc tiering | Phases 1-5, 6 dimensions, STOP gate, D1 brief |
| Iron Law check | N/A | All 6 dimensions explicitly enumerated |
| Decision brief | One paragraph | Full A/B/C with ELI10 + ≥40-char pros-cons + Net |

## The qualitative difference

Both subagents identified the 3 TIER-1 security issues (2 SQL injections + hardcoded API key) and the bare except. **They don't disagree on the must-fix floor.**

Where they diverge:

### Baseline strengths
- More **domain-specific surface findings** beyond the GT: caught `delete_item(id)` shadowing builtin, hardcoded `"inventory.db"` path, missing schema migration, hardcoded `$` in `format_currency`. The model applied real Python intuition per-file.
- More readable as a narrative — one would happily skim it.

### Skill strengths
- **Process discipline.** Six dimensions, all explicitly enumerated even when sparse. No "I think the structure is fine" — every dimension produces explicit findings or an explicit "no issues" call.
- **Tier calibration.** Every finding has an explicit tier with one-line justification. Baseline elevated #7 (duplicate httpx) to TIER-1 — debatable. Skill's calibration is more defensible.
- **Dedup.** Skill explicitly noted: "SEC1 absorbs the scanner's `hardcoded-api-key`; C2 absorbs `time-sleep-in-test`." Baseline silently reports the same finding twice across categories.
- **Evidence grounding.** Dimension 5 (Standards) was run via `aidoctor scan --json` — the report cites the JSON output, not the model's recall.
- **Decision brief.** The skill emits a real D1 brief with three options, ELI10 ("ELI10: The audit found 32 unique issues..."), ≥40-char pros-cons, and a Net line. Baseline's recommendation is one paragraph.
- **Catch rate +2.** Skill found #8 (unpinned deps explicitly enumerated) and gave full tier-attribution to #6 (missing tests across multiple dimensions).

## What this means for shipping

The skill's value-add on a SMALL/OBVIOUS corpus is **process and calibration**, not raw bug detection. The baseline catches almost everything because the bugs are obvious and Python-idiomatic.

**The skill's value compounds on:**
1. **Larger codebases** (50+ files) where baseline would lose context coherence — the dimensional structure prevents the model from "drifting" into one or two files.
2. **Iterative fix loops** — the structured format makes it possible to track "what was T1 last run, fixed, now what's T2 promoted to T1?".
3. **Multi-agent dispatch** — the six dimensions are designed to be six parallel reviewer subagents, which baseline can't do.

## Critical context

Both reports correctly identified:
- 2 SQL injection vectors (the must-not-ship bugs)
- Hardcoded API key
- Bare except + silent failure
- Resource leak risk in DB code
- Test coverage gap for `db.py` (where the SQLi lives)

**The skill doesn't change the floor.** It changes the ceiling and the calibration.

## Limitations (honest)

- **Small corpus (5 files, 80 LOC, 22 issues).** Real-world repos are 100-1000+ files. Skill's structural advantage would compound at scale; this test undersells it.
- **Ground truth bias.** I both planted the issues AND graded the reports. A fairer test: someone else plants, someone else grades.
- **Single-shot per agent.** Didn't test the iterative loop (audit → Option A → fix → re-audit).
- **Sequential dimensions** in subagent (told it "don't spawn sub-subagents"). Real /aidoctor:audit would dispatch six parallel reviewers, which is faster + more diverse.

## Decision: ship audit in v0.1.x or hold for v0.2?

**Ship.** Reasons:
1. Catches all TIER-1 security bugs (the must-not-ship floor)
2. Process discipline + decision brief format is genuinely better DX than baseline
3. Iteration-2 already validated the same pattern in `simplify`
4. The "limitations" are LARGER-corpus tests, not blockers

What we'd want from iteration-4+:
- Real-world repo test (aidoctor itself, or sample OSS)
- Iterative loop test
- Real parallel dispatch (not sequential in-process)

## What we have shipped so far (v0.1.x, validated)

| Skill | Iteration | Validation |
|---|---|---|
| `python-rules` | iteration-1 | ✅ avg score 96→100, 3/5 evals improved |
| `simplify` | iteration-2 | ✅ 44 findings vs 7 hand-found, 0 false positives |
| `audit` | iteration-3 (this report) | ✅ 95% GT catch, structured output, tight calibration |
| `scan` (CLI) | (covered by all 3 above) | ✅ used as evidence layer for python-rules + audit |
